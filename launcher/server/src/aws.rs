//! The bot on AWS Lambda (feature "aws"). Two functions run this binary, chosen by DZ_LAMBDA:
//!
//!   api     the web side (api.rs) behind a Function URL: the launchers' /api/* and Discord's /api/interactions.
//!           It never signs and never calls Discord: slow work goes to the queue as jobs (jobs.rs).
//!   worker  reads the SQS FIFO queue: deferred answers, raid posts, DMs, the reminder tick, setup. It holds the
//!           Discord token and the signing key. Invoked directly with { "admin": "keygen" } it makes the bridge key
//!           once (refused when one exists).
//!
//! State is a DynamoDB table (one item per document: pk = this bot's profile, sk = the document's key; the value
//! gzip'd; bigger than an item holds -> an S3 object it points to). The bucket also holds the art and Items.lua
//! (<profile>/assets/, copied to DZ_DATA at a cold start) and the key's public leaves (<profile>/bridge_key.json.leaves).
//!
//! Environment: DZ_LAMBDA, DZ_PROFILE, DZ_TABLE, DZ_BUCKET, DZ_QUEUE_URL, DZ_TOKEN_PARAM, DZ_KEY_PARAM, DZ_DATA
//! (a folder under /tmp), plus the Config ones (DZ_APP_ID, DZ_GUILD_ID, DZ_GUILD, DZ_PUBLIC_KEY) and TZ.

use crate::core::{Error, Result};
use crate::store::{Backend, Doc};
use aws_sdk_dynamodb::primitives::Blob;
use aws_sdk_dynamodb::types::{AttributeValue, ReturnValue};
use std::collections::HashMap;
use std::future::Future;
use std::io::{Read, Write};
use std::sync::Arc;

/// A gzip'd value bigger than this goes to S3 (a DynamoDB item holds 400 KB).
const ITEM_MAX: usize = 350 * 1024;

fn e<E: std::error::Error>(what: &str, err: E) -> Error {
    // (the whole chain: an SDK error alone says only "service error")
    Error::Net(format!("{what}: {}", aws_smithy_types::error::display::DisplayErrorContext(&err)))
}

/// Run an AWS call from the bot's synchronous code (the store is called from everywhere). The functions run on
/// tokio's multi-thread runtime, where this is allowed.
fn block<F: Future>(rt: &tokio::runtime::Handle, f: F) -> F::Output {
    tokio::task::block_in_place(|| rt.block_on(f))
}

fn gz(b: &[u8]) -> Vec<u8> {
    let mut w = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
    let _ = w.write_all(b);
    w.finish().unwrap_or_default()
}

fn gunzip(b: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    flate2::read::GzDecoder::new(b).read_to_end(&mut out)?;
    Ok(out)
}

// ------------------------------------------------------------------------------------------------------------------
// The store
// ------------------------------------------------------------------------------------------------------------------

pub struct Dynamo {
    pub db: aws_sdk_dynamodb::Client,
    pub s3: Option<aws_sdk_s3::Client>,
    pub table: String,
    pub bucket: String,
    /// this bot's partition: one table serves every guild's bot
    pub pk: String,
    pub rt: tokio::runtime::Handle,
}

impl Dynamo {
    fn key(&self, k: &str) -> HashMap<String, AttributeValue> {
        HashMap::from([("pk".to_string(), AttributeValue::S(self.pk.clone())), ("sk".to_string(), AttributeValue::S(k.to_string()))])
    }

    async fn value_of(&self, item: &HashMap<String, AttributeValue>) -> Result<Doc> {
        let ver = item.get("ver").and_then(|v| v.as_n().ok()).and_then(|n| n.parse().ok()).unwrap_or(1);
        let raw = match (item.get("v"), item.get("s3").and_then(|v| v.as_s().ok())) {
            (Some(AttributeValue::B(b)), _) => b.as_ref().to_vec(),
            (_, Some(obj)) => {
                let s3 = self.s3.as_ref().ok_or_else(|| Error::Msg("a document is in S3 but no bucket is set".into()))?;
                // (the exact S3 version this item points to: a newer write never changes what it reads)
                let v = item.get("s3v").and_then(|v| v.as_s().ok()).cloned();
                let o = s3.get_object().bucket(&self.bucket).key(obj).set_version_id(v).send().await.map_err(|x| e("s3 get", x))?;
                o.body.collect().await.map_err(|x| e("s3 read", x))?.into_bytes().to_vec()
            }
            _ => return Err(Error::Msg("a document without a value".into())),
        };
        Ok(Doc { bytes: gunzip(&raw)?, ver })
    }
}

impl Backend for Dynamo {
    fn get(&self, key: &str) -> Result<Option<Doc>> {
        block(&self.rt, async {
            let out = self.db.get_item().table_name(&self.table).set_key(Some(self.key(key))).consistent_read(true).send().await;
            match out.map_err(|x| e("dynamodb get", x))?.item {
                Some(item) if item.contains_key("v") || item.contains_key("s3") => Ok(Some(self.value_of(&item).await?)),
                _ => Ok(None),
            }
        })
    }

    fn put_if(&self, key: &str, bytes: &[u8], expect: u64) -> Result<bool> {
        block(&self.rt, async {
            let ver = expect + 1;
            let z = gz(bytes);
            let mut item = self.key(key);
            item.insert("ver".into(), AttributeValue::N(ver.to_string()));
            if z.len() > ITEM_MAX {
                let s3 = self.s3.as_ref().ok_or_else(|| Error::Msg(format!("{key} is too big for an item and no bucket is set")))?;
                // (the bucket keeps versions: the item names the one it wrote, so a reader of the item before it still
                // gets its own; old versions expire by the bucket's lifecycle)
                let obj = format!("{}/docs/{key}", self.pk);
                let put = s3.put_object().bucket(&self.bucket).key(&obj).body(z.into()).send().await.map_err(|x| e("s3 put", x))?;
                item.insert("s3".into(), AttributeValue::S(obj));
                if let Some(v) = put.version_id() {
                    item.insert("s3v".into(), AttributeValue::S(v.to_string()));
                }
            } else {
                item.insert("v".into(), AttributeValue::B(Blob::new(z)));
            }
            // (marks of answered interactions: DynamoDB deletes them after two days, its TTL on "expires")
            if key.starts_with("answered/") {
                item.insert("expires".into(), AttributeValue::N((crate::bot::unix_now() + 2 * 86400).to_string()));
            }
            let mut req = self.db.put_item().table_name(&self.table).set_item(Some(item));
            req = if expect == 0 {
                req.condition_expression("attribute_not_exists(sk) OR (attribute_not_exists(v) AND attribute_not_exists(s3))")
            } else {
                req.condition_expression("ver = :v").expression_attribute_values(":v", AttributeValue::N(expect.to_string()))
            };
            match req.send().await {
                Ok(_) => Ok(true),
                Err(x) if x.as_service_error().is_some_and(|s| s.is_conditional_check_failed_exception()) => Ok(false),
                Err(x) => Err(e("dynamodb put", x)),
            }
        })
    }

    fn delete(&self, key: &str) -> Result<()> {
        block(&self.rt, async {
            self.db.delete_item().table_name(&self.table).set_key(Some(self.key(key))).send().await.map_err(|x| e("dynamodb delete", x))?;
            Ok(())
        })
    }

    fn list(&self, prefix: &str) -> Result<Vec<(String, Vec<u8>)>> {
        block(&self.rt, async {
            let mut out = Vec::new();
            let mut start = None;
            loop {
                let mut q = self
                    .db
                    .query()
                    .table_name(&self.table)
                    .expression_attribute_values(":pk", AttributeValue::S(self.pk.clone()))
                    .consistent_read(true);
                // (DynamoDB refuses an empty begins_with: no prefix is the whole partition)
                q = if prefix.is_empty() {
                    q.key_condition_expression("pk = :pk")
                } else {
                    q.key_condition_expression("pk = :pk AND begins_with(sk, :p)").expression_attribute_values(":p", AttributeValue::S(prefix.to_string()))
                };
                let page = q
                    .set_exclusive_start_key(start)
                    .send()
                    .await
                    .map_err(|x| e("dynamodb query", x))?;
                for item in page.items() {
                    let Some(k) = item.get("sk").and_then(|v| v.as_s().ok()) else { continue };
                    if item.contains_key("v") || item.contains_key("s3") {
                        out.push((k.clone(), self.value_of(item).await?.bytes));
                    }
                }
                match page.last_evaluated_key() {
                    Some(k) if !k.is_empty() => start = Some(k.clone()),
                    _ => break,
                }
            }
            out.sort_by(|a, b| a.0.cmp(&b.0));
            Ok(out)
        })
    }

    fn take(&self, key: &str, start: u64, limit: u64) -> Result<Option<u64>> {
        block(&self.rt, async {
            // (one atomic step: the number handed out is the one this call moved past; nobody else gets it)
            let r = self
                .db
                .update_item()
                .table_name(&self.table)
                .set_key(Some(self.key(key)))
                .update_expression("SET n = if_not_exists(n, :start) + :one")
                .condition_expression("attribute_not_exists(n) OR n < :limit")
                .expression_attribute_values(":start", AttributeValue::N(start.to_string()))
                .expression_attribute_values(":one", AttributeValue::N("1".into()))
                .expression_attribute_values(":limit", AttributeValue::N(limit.to_string()))
                .return_values(ReturnValue::UpdatedNew)
                .send()
                .await;
            match r {
                Ok(o) => {
                    let n: u64 = o
                        .attributes()
                        .and_then(|a| a.get("n"))
                        .and_then(|v| v.as_n().ok())
                        .and_then(|n| n.parse().ok())
                        .ok_or_else(|| Error::Msg("the counter has no number".into()))?;
                    let taken = n - 1;
                    Ok((taken < limit).then_some(taken))
                }
                Err(x) if x.as_service_error().is_some_and(|s| s.is_conditional_check_failed_exception()) => Ok(None),
                Err(x) => Err(e("dynamodb counter", x)),
            }
        })
    }

    fn peek(&self, key: &str) -> Result<Option<u64>> {
        block(&self.rt, async {
            let out = self.db.get_item().table_name(&self.table).set_key(Some(self.key(key))).consistent_read(true).send().await;
            Ok(out.map_err(|x| e("dynamodb get", x))?.item.and_then(|i| i.get("n").and_then(|v| v.as_n().ok()).and_then(|n| n.parse().ok())))
        })
    }
}

// ------------------------------------------------------------------------------------------------------------------
// The job queue
// ------------------------------------------------------------------------------------------------------------------

pub struct Sqs {
    pub client: aws_sdk_sqs::Client,
    pub url: String,
    pub rt: tokio::runtime::Handle,
}

impl crate::jobs::Queue for Sqs {
    fn send(&self, job: &crate::jobs::Job) -> Result<()> {
        let body = serde_json::to_string(job).map_err(|x| Error::Msg(x.to_string()))?;
        block(&self.rt, async {
            self.client
                .send_message()
                .queue_url(&self.url)
                .message_body(body)
                .message_group_id(job.group())
                .message_deduplication_id(job.dedup(crate::bot::unix_now()))
                .send()
                .await
                .map_err(|x| e("sqs send", x))?;
            Ok(())
        })
    }
}

// ------------------------------------------------------------------------------------------------------------------
// Starting a function
// ------------------------------------------------------------------------------------------------------------------

struct Env {
    profile: String,
    table: String,
    bucket: String,
    queue_url: String,
}

fn need(k: &str) -> std::result::Result<String, String> {
    std::env::var(k).ok().filter(|v| !v.is_empty()).ok_or_else(|| format!("{k} is not set"))
}

/// The SDK's HTTP client: rustls with ring, as the bot's Discord side.
fn https() -> aws_sdk_dynamodb::config::SharedHttpClient {
    aws_smithy_http_client::Builder::new()
        .tls_provider(aws_smithy_http_client::tls::Provider::Rustls(aws_smithy_http_client::tls::rustls_provider::CryptoMode::Ring))
        .build_https()
}

async fn sdk() -> aws_config::SdkConfig {
    aws_config::defaults(aws_config::BehaviorVersion::latest()).http_client(https()).load().await
}

async fn param(ssm: &aws_sdk_ssm::Client, name: &str) -> Result<String> {
    let o = ssm.get_parameter().name(name).with_decryption(true).send().await.map_err(|x| e(&format!("ssm {name}"), x))?;
    o.parameter().and_then(|p| p.value()).map(str::to_string).ok_or_else(|| Error::Msg(format!("ssm {name} is empty")))
}

/// The art and Items.lua from <profile>/assets/ into the data folder (the worker draws the pictures).
async fn fetch_assets(s3: &aws_sdk_s3::Client, bucket: &str, profile: &str) -> Result<usize> {
    use futures::stream::{self, StreamExt, TryStreamExt};
    let prefix = format!("{profile}/assets/");
    let dir = crate::data_dir();
    // the keys first (1000 a page), then the files 32 at a time: a bot's art is about a thousand small icons, and
    // one by one that is half a minute of every cold start
    let mut todo = Vec::new();
    let mut token = None;
    loop {
        let page = s3
            .list_objects_v2()
            .bucket(bucket)
            .prefix(&prefix)
            .set_continuation_token(token)
            .send()
            .await
            .map_err(|x| e("s3 list", x))?;
        for o in page.contents() {
            let Some(k) = o.key() else { continue };
            let Some(rel) = k.strip_prefix(&prefix).filter(|r| !r.is_empty() && !r.ends_with('/') && !r.contains("..")) else { continue };
            let dest = dir.join(rel);
            if !dest.exists() {
                todo.push((k.to_string(), dest));
            }
        }
        match page.next_continuation_token() {
            Some(t) => token = Some(t.to_string()),
            None => break,
        }
    }
    let n = todo.len();
    stream::iter(todo)
        .map(|(k, dest)| async move {
            let body = s3.get_object().bucket(bucket).key(&k).send().await.map_err(|x| e("s3 get", x))?;
            let bytes = body.body.collect().await.map_err(|x| e("s3 read", x))?.into_bytes();
            if let Some(p) = dest.parent() {
                std::fs::create_dir_all(p)?;
            }
            std::fs::write(&dest, &bytes)?;
            Ok::<(), crate::core::Error>(())
        })
        .buffer_unordered(32)
        .try_collect::<Vec<()>>()
        .await?;
    Ok(n)
}

/// One object into the data folder.
async fn fetch_file(s3: &aws_sdk_s3::Client, bucket: &str, key: &str, rel: &str) -> Result<()> {
    let o = s3.get_object().bucket(bucket).key(key).send().await.map_err(|x| e("s3 get", x))?;
    let bytes = o.body.collect().await.map_err(|x| e("s3 read", x))?.into_bytes();
    let dest = crate::data_dir().join(rel);
    if let Some(p) = dest.parent() {
        std::fs::create_dir_all(p)?;
    }
    std::fs::write(dest, &bytes)?;
    Ok(())
}

static ASSETS: std::sync::OnceLock<(aws_sdk_s3::Client, String, String)> = std::sync::OnceLock::new();

/// A file the worker made for the art folder (an item icon from Wowhead): kept in S3 for the next cold start.
pub async fn publish_asset(rel: &str, bytes: &[u8]) {
    let Some((s3, bucket, profile)) = ASSETS.get() else { return };
    let r = s3.put_object().bucket(bucket).key(format!("{profile}/assets/{rel}")).body(bytes.to_vec().into()).send().await;
    if let Err(x) = r {
        eprintln!("aws: keep {rel}: {x}");
    }
}

/// The Lambda's start: DZ_LAMBDA says which function this is.
pub async fn lambda_main(role: &str) -> std::result::Result<(), lambda_runtime::Error> {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let env = Env { profile: need("DZ_PROFILE")?, table: need("DZ_TABLE")?, bucket: need("DZ_BUCKET")?, queue_url: need("DZ_QUEUE_URL")? };
    let cfg = sdk().await;
    let rt = tokio::runtime::Handle::current();
    let s3 = aws_sdk_s3::Client::new(&cfg);
    crate::store::set(Arc::new(Dynamo {
        db: aws_sdk_dynamodb::Client::new(&cfg),
        s3: Some(s3.clone()),
        table: env.table.clone(),
        bucket: env.bucket.clone(),
        pk: env.profile.clone(),
        rt: rt.clone(),
    }));
    crate::jobs::set_queue(Arc::new(Sqs { client: aws_sdk_sqs::Client::new(&cfg), url: env.queue_url.clone(), rt }));
    match role {
        "api" => {
            // (the item list: /bis set's autocomplete is answered here, at once)
            if let Err(x) = fetch_file(&s3, &env.bucket, &format!("{}/assets/Items.lua", env.profile), "Items.lua").await {
                eprintln!("aws: no Items.lua ({x}): /bis set finds no items");
            }
            lambda_http::run(crate::api::router()).await
        }
        "worker" => {
            let ssm = aws_sdk_ssm::Client::new(&cfg);
            let _ = ASSETS.set((s3.clone(), env.bucket.clone(), env.profile.clone()));
            match fetch_assets(&s3, &env.bucket, &env.profile).await {
                Ok(n) => eprintln!("aws: {n} art files fetched"),
                Err(x) => eprintln!("aws: no art ({x}): the bot posts text"),
            }
            let token = param(&ssm, &need("DZ_TOKEN_PARAM")?).await?;
            crate::bot::init_http(token.trim());
            let key_param = need("DZ_KEY_PARAM")?;
            let leaves_obj = format!("{}/bridge_key.json.leaves", env.profile);
            match load_signer(&ssm, &s3, &env.bucket, &key_param, &leaves_obj).await {
                Ok(s) => {
                    eprintln!("aws: signing key loaded");
                    crate::bridge::set_counted_signer(s);
                }
                Err(x) => eprintln!("aws: no signing key ({x}): Discord changes can't reach the game (run the keygen)"),
            }
            let keygen = (ssm, s3, env.bucket.clone(), key_param, leaves_obj);
            lambda_runtime::run(lambda_runtime::service_fn(move |ev: lambda_runtime::LambdaEvent<serde_json::Value>| {
                let keygen = keygen.clone();
                async move { worker(ev.payload, &keygen).await }
            }))
            .await
        }
        other => Err(format!("DZ_LAMBDA={other}: api or worker").into()),
    }
}

async fn load_signer(ssm: &aws_sdk_ssm::Client, s3: &aws_sdk_s3::Client, bucket: &str, param_name: &str, leaves_obj: &str) -> Result<dz_proto::wots::Signer> {
    let key_json = param(ssm, param_name).await?;
    let leaves = s3.get_object().bucket(bucket).key(leaves_obj).send().await.map_err(|x| e("s3 leaves", x))?;
    let leaves = leaves.body.collect().await.map_err(|x| e("s3 leaves", x))?.into_bytes();
    dz_proto::wots::Signer::from_parts(key_json.as_bytes(), &leaves).map_err(|x| Error::Msg(x.to_string()))
}

type KeygenCtx = (aws_sdk_ssm::Client, aws_sdk_s3::Client, String, String, String);

/// One event: an SQS batch (jobs), or a direct call ({ "job": ... } or { "admin": "keygen" }).
async fn worker(ev: serde_json::Value, keygen: &KeygenCtx) -> std::result::Result<serde_json::Value, lambda_runtime::Error> {
    if let Some(records) = ev.get("Records").and_then(|r| r.as_array()) {
        // (FIFO: after a failure the rest of the batch is handed back too, so a group's order holds)
        let mut failed: Vec<serde_json::Value> = Vec::new();
        for r in records {
            let id = r.get("messageId").cloned().unwrap_or_default();
            if !failed.is_empty() {
                failed.push(serde_json::json!({ "itemIdentifier": id }));
                continue;
            }
            let job = r.get("body").and_then(|b| b.as_str()).and_then(|b| serde_json::from_str::<crate::jobs::Job>(b).ok());
            let ok = match job {
                Some(job) => match crate::jobs::run(job).await {
                    Ok(()) => true,
                    Err(x) => {
                        eprintln!("worker: {x}");
                        false
                    }
                },
                None => {
                    eprintln!("worker: a message that is no job (dropped)");
                    true
                }
            };
            if !ok {
                failed.push(serde_json::json!({ "itemIdentifier": id }));
            }
        }
        return Ok(serde_json::json!({ "batchItemFailures": failed }));
    }
    if ev.get("admin").and_then(|a| a.as_str()) == Some("keygen") {
        let height = ev.get("height").and_then(|h| h.as_u64()).unwrap_or(16).clamp(4, 20) as u8;
        return Ok(make_key(keygen, height).await.map_err(|x| x.to_string())?);
    }
    let job: crate::jobs::Job = serde_json::from_value(ev).map_err(|x| format!("not a job: {x}"))?;
    crate::jobs::run(job).await.map_err(|x| x.to_string())?;
    Ok(serde_json::json!({ "ok": true }))
}

/// Make the bridge key here, so its secret never exists anywhere but this parameter: refused when it exists.
/// Returns the addon's Core/BridgeKey.lua (the public half) and also keeps it in S3 (<profile>/BridgeKey.lua).
async fn make_key(k: &KeygenCtx, height: u8) -> Result<serde_json::Value> {
    let (ssm, s3, bucket, param_name, leaves_obj) = k;
    if ssm.get_parameter().name(param_name).send().await.is_ok() {
        return Err(Error::Msg(format!("{param_name} exists: a key is made once (a new one needs an addon release; delete the old one by hand first)")));
    }
    let dir = std::env::temp_dir().join(format!("dz-keygen-{}", crate::store::rand_u64()));
    std::fs::create_dir_all(&dir)?;
    let p = dir.join("bridge_key.json");
    let mut entropy = [0u8; 48];
    getrandom::fill(&mut entropy).map_err(|x| Error::Msg(x.to_string()))?;
    let signer = dz_proto::wots::Signer::create(&p, height, &entropy).map_err(|x| Error::Msg(x.to_string()))?;
    let key_json = std::fs::read_to_string(&p)?;
    let leaves = std::fs::read(dir.join("bridge_key.json.leaves"))?;
    let _ = std::fs::remove_dir_all(&dir);
    // leaves first (public); then the secret, which may only be written if nobody made one meanwhile
    s3.put_object().bucket(bucket.as_str()).key(leaves_obj.as_str()).body(leaves.into()).send().await.map_err(|x| e("s3 leaves", x))?;
    ssm.put_parameter()
        .name(param_name.as_str())
        .value(key_json)
        .r#type(aws_sdk_ssm::types::ParameterType::SecureString)
        .overwrite(false)
        .send()
        .await
        .map_err(|x| e("ssm put (the key)", x))?;
    let lua = crate::bridge_key_lua(&signer.public());
    let profile = leaves_obj.split('/').next().unwrap_or("");
    let _ = s3.put_object().bucket(bucket.as_str()).key(format!("{profile}/BridgeKey.lua")).body(lua.clone().into_bytes().into()).send().await;
    crate::bridge::set_counted_signer(signer);
    Ok(serde_json::json!({ "ok": true, "signatures": 1u64 << height, "BridgeKey.lua": lua }))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The store's promises against DynamoDB Local (docker run -p 8000:8000 amazon/dynamodb-local), when
    /// DZ_TEST_DYNAMO=http://localhost:8000 is set; skipped otherwise.
    #[test]
    fn dynamo_keeps_every_promise() {
        let Ok(endpoint) = std::env::var("DZ_TEST_DYNAMO") else {
            eprintln!("DZ_TEST_DYNAMO not set: skipped");
            return;
        };
        let rt = tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap();
        let (db, table) = rt.block_on(async {
            let cfg = aws_sdk_dynamodb::config::Builder::new()
                .behavior_version(aws_sdk_dynamodb::config::BehaviorVersion::latest())
                .region(aws_sdk_dynamodb::config::Region::new("local"))
                .endpoint_url(endpoint)
                .credentials_provider(aws_sdk_dynamodb::config::Credentials::new("x", "x", None, None, "test"))
                .http_client(https())
                .build();
            let db = aws_sdk_dynamodb::Client::from_conf(cfg);
            let table = format!("dz-test-{}", crate::store::rand_u64() % 1_000_000);
            use aws_sdk_dynamodb::types::*;
            db.create_table()
                .table_name(&table)
                .attribute_definitions(AttributeDefinition::builder().attribute_name("pk").attribute_type(ScalarAttributeType::S).build().unwrap())
                .attribute_definitions(AttributeDefinition::builder().attribute_name("sk").attribute_type(ScalarAttributeType::S).build().unwrap())
                .key_schema(KeySchemaElement::builder().attribute_name("pk").key_type(KeyType::Hash).build().unwrap())
                .key_schema(KeySchemaElement::builder().attribute_name("sk").key_type(KeyType::Range).build().unwrap())
                .billing_mode(BillingMode::PayPerRequest)
                .send()
                .await
                .unwrap();
            (db, table)
        });
        let mk = |pk: &str| -> Arc<dyn Backend> {
            Arc::new(Dynamo { db: db.clone(), s3: None, table: table.clone(), bucket: String::new(), pk: pk.into(), rt: rt.handle().clone() })
        };
        // (the store is global: hold the tests' lock while it points at DynamoDB)
        let (_d, _g) = crate::bridge::tests::scratch();
        let a = mk("guild-a");
        let b = mk("guild-b");
        let a2 = a.clone();
        rt.block_on(async move { tokio::spawn(async move { crate::store::contract::check(a2) }).await.unwrap() });
        // another guild's partition sees none of it
        let b2 = b.clone();
        rt.block_on(async move { tokio::spawn(async move { assert!(b2.list("").unwrap().is_empty()) }).await.unwrap() });
        let c = mk("guild-c");
        rt.block_on(async move { tokio::spawn(async move { crate::store::contract::check_concurrency(c) }).await.unwrap() });
    }
}
