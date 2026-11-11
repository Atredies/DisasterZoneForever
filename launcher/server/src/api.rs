//! The web side members' launchers talk to (dz_proto documents the bodies):
//!   GET  /api/health           is the bot up, how old is its guild data, signatures left
//!   POST /api/link  { code }   a /launcher code -> the launcher's member key
//!   POST /api/sync             (Bearer key) the game's last save in, the signed records + channels + links out
//!   GET  /api/presence         (Bearer key) who of the guild is in game, when the others last were (presence.rs)
//!   POST /api/interactions     Discord itself (the Developer Portal's Interactions Endpoint URL): every slash
//!                              command, button and form, signed by Discord (Ed25519, the app's public key)
//! Behind a TLS proxy (Caddy) on the server; plain HTTP on 127.0.0.1 when testing at home.

use crate::bridge;
use axum::body::Bytes;
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use dz_proto::{LinkDown, LinkUp, PresenceDown, SyncDown, SyncUp};
use serde_json::{json, Value};
use std::io::Read;

/// The biggest upload taken (a guild's snapshot is a few hundred KB; gzip'd far less).
const MAX_BODY: usize = 16 * 1024 * 1024;

type Fail = (StatusCode, String);

fn fail(code: StatusCode, text: &str) -> Fail {
    (code, text.to_string())
}

pub fn router() -> Router {
    Router::new()
        .route("/api/health", get(health))
        .route("/api/link", post(link))
        .route("/api/sync", post(sync))
        .route("/api/presence", get(presence))
        .route("/api/interactions", post(interactions))
        .layer(axum::extract::DefaultBodyLimit::max(MAX_BODY))
}

async fn health() -> Json<Value> {
    let now = crate::bot::unix_now();
    let age = crate::signup::current_snap().and_then(|s| s.get("at").and_then(|a| a.as_u64())).map(|a| now.saturating_sub(a));
    Json(json!({ "ok": true, "version": env!("CARGO_PKG_VERSION"), "dataAge": age, "signaturesLeft": bridge::signatures_left() }))
}

async fn link(Json(up): Json<LinkUp>) -> Result<Json<LinkDown>, Fail> {
    match crate::members::redeem(&up.code, crate::bot::unix_now()) {
        Some((key, user)) => Ok(Json(LinkDown { key, user })),
        None => Err(fail(StatusCode::NOT_FOUND, "That code is unknown or older than 15 minutes: type /launcher in Discord for a new one.")),
    }
}

fn body_json(headers: &HeaderMap, body: &[u8]) -> Result<SyncUp, Fail> {
    let gz = headers.get("content-encoding").and_then(|v| v.to_str().ok()).is_some_and(|v| v.eq_ignore_ascii_case("gzip"));
    let raw = if gz {
        let mut out = Vec::new();
        flate2::read::GzDecoder::new(body)
            .take(MAX_BODY as u64 * 4)
            .read_to_end(&mut out)
            .map_err(|_| fail(StatusCode::BAD_REQUEST, "the upload is not gzip"))?;
        out
    } else {
        body.to_vec()
    };
    serde_json::from_slice(&raw).map_err(|e| fail(StatusCode::BAD_REQUEST, &format!("bad upload: {e}")))
}

/// (one upload merged at a time)
static MERGING: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// The member key of a request (Authorization: Bearer <key>), checked.
fn member_of(headers: &HeaderMap, now: u64) -> Result<crate::members::Member, Fail> {
    let key = headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .ok_or_else(|| fail(StatusCode::UNAUTHORIZED, "no member key"))?;
    crate::members::check(key, now)
        .ok_or_else(|| fail(StatusCode::UNAUTHORIZED, "This launcher's key was removed: link it again with /launcher in Discord."))
}

/// Who is in game (a launcher asks once a minute while its window is open).
async fn presence(headers: HeaderMap) -> Result<Json<PresenceDown>, Fail> {
    let now = crate::bot::unix_now();
    member_of(&headers, now)?;
    Ok(Json(crate::presence::list(now)))
}

async fn sync(headers: HeaderMap, body: Bytes) -> Result<Json<SyncDown>, Fail> {
    let now = crate::bot::unix_now();
    let member = member_of(&headers, now)?;
    let up = body_json(&headers, &body)?;
    if let Some(g) = up.game.as_ref() {
        crate::presence::report(&member.user, &member.name, g, now);
    }
    if let Some(db) = up.bridge.as_ref() {
        // what the game took leaves the queue; refusals go to whoever made them
        match bridge::take_applied(db.get("applied")) {
            Ok(failed) if !failed.is_empty() => crate::jobs::submit(crate::jobs::Job::Tell { failed }),
            Ok(_) => {}
            Err(e) => eprintln!("sync: queue: {e}"),
        }
        if let Some(snap) = db.get("snap").filter(|s| s.is_object() && s.get("error").is_none()) {
            take_snapshot(snap, &member.name).await;
        }
    }
    let mut down = SyncDown {
        now,
        records: bridge::load_queue(),
        channels: bridge::load_channels(),
        links: bridge::links(&bridge::load_profiles()),
        user: member.name,
        hash: String::new(),
        same: false,
    };
    down.hash = answer_hash(&down);
    // (the free server's traffic is capped: an unchanged answer is one line)
    if !up.have.is_empty() && up.have == down.hash {
        down.records.clear();
        down.channels.clear();
        down.links.clear();
        down.same = true;
    }
    Ok(Json(down))
}

fn answer_hash(d: &SyncDown) -> String {
    let text = serde_json::to_vec(&(&d.records, &d.channels, &d.links, &d.user)).unwrap_or_default();
    hex::encode(&<sha2::Sha256 as sha2::Digest>::digest(text)[..12])
}

/// Fold a member's snapshot into the guild's; when it changed, the raid posts follow.
pub async fn take_snapshot(snap: &Value, who: &str) {
    let _g = MERGING.lock().await;
    let guild = crate::config().guild.clone().filter(|g| !g.is_empty());
    // (read, merge, write back only if no other copy of the bot merged meanwhile: else merge again into theirs)
    let res = crate::store::update(crate::signup::SNAP_KEY, |cur: &mut Option<Value>| {
        match crate::merge::merge(cur.as_ref(), snap, guild.as_deref()) {
            crate::merge::Outcome::Merged(v) => {
                let changed = cur.as_ref() != Some(&v);
                *cur = Some(v);
                Ok(changed)
            }
            crate::merge::Outcome::OtherGuild(g) => Err(g),
        }
    });
    let merged = match res {
        Ok(Ok(true)) => match crate::store::load_opt::<Value>(crate::signup::SNAP_KEY) {
            Some(v) => v,
            None => return,
        },
        Ok(Ok(false)) => return,
        Ok(Err(g)) => {
            eprintln!("sync: {who}'s snapshot is for another guild ({g}): ignored");
            return;
        }
        Err(e) => {
            eprintln!("sync: could not save merged.json: {e}");
            return;
        }
    };
    crate::signup::set_snap(merged);
    crate::posts::request_refresh();
}

// ------------------------------------------------------------------------------------------------------------------
// Discord over HTTP
// ------------------------------------------------------------------------------------------------------------------

/// Is this request from Discord: the app's Ed25519 signature over timestamp + body (Discord sends a bad one now and
/// then on purpose and turns the endpoint off if it is accepted). A timestamp far from our clock is refused too.
pub fn from_discord(public_key_hex: &str, headers: &HeaderMap, body: &[u8], now: u64) -> bool {
    use ed25519_dalek::{Signature, Verifier, VerifyingKey};
    let h = |n: &str| headers.get(n).and_then(|v| v.to_str().ok());
    let (Some(sig), Some(ts)) = (h("x-signature-ed25519"), h("x-signature-timestamp")) else { return false };
    let Some(key) = hex::decode(public_key_hex.trim()).ok().and_then(|k| <[u8; 32]>::try_from(k).ok()) else { return false };
    let Ok(key) = VerifyingKey::from_bytes(&key) else { return false };
    let Some(sig) = hex::decode(sig).ok().and_then(|s| <[u8; 64]>::try_from(s).ok()) else { return false };
    if ts.parse::<u64>().map_or(true, |t| t.abs_diff(now) > 600) {
        return false;
    }
    let mut msg = ts.as_bytes().to_vec();
    msg.extend_from_slice(body);
    key.verify(&msg, &Signature::from_bytes(&sig)).is_ok()
}

async fn interactions(headers: HeaderMap, body: Bytes) -> Result<Json<Value>, Fail> {
    let key = crate::config().public_key.clone();
    if key.is_empty() || !from_discord(&key, &headers, &body, crate::bot::unix_now()) {
        return Err(fail(StatusCode::UNAUTHORIZED, "bad signature"));
    }
    let v: Value = serde_json::from_slice(&body).map_err(|_| fail(StatusCode::BAD_REQUEST, "not JSON"))?;
    // PING: Discord checking the endpoint
    if v.get("type").and_then(|t| t.as_u64()) == Some(1) {
        return Ok(Json(json!({ "type": 1 })));
    }
    let i: twilight_model::application::interaction::Interaction =
        serde_json::from_value(v).map_err(|e| fail(StatusCode::BAD_REQUEST, &format!("not an interaction: {e}")))?;
    if let Some(resp) = crate::bot::immediate(&i) {
        return Ok(Json(serde_json::to_value(resp).unwrap_or_default()));
    }
    crate::jobs::submit(crate::jobs::Job::Interaction { raw: String::from_utf8_lossy(&body).into_owned() });
    Ok(Json(serde_json::to_value(crate::bot::deferral(&i)).unwrap_or_default()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn only_discord_signed_requests_get_in() {
        use ed25519_dalek::{Signer, SigningKey};
        let sk = SigningKey::from_bytes(&[7u8; 32]);
        let pk = hex::encode(sk.verifying_key().to_bytes());
        let body = br#"{"type":1}"#;
        let signed = |ts: &str, body: &[u8]| {
            let mut m = ts.as_bytes().to_vec();
            m.extend_from_slice(body);
            let mut h = HeaderMap::new();
            h.insert("x-signature-ed25519", hex::encode(sk.sign(&m).to_bytes()).parse().unwrap());
            h.insert("x-signature-timestamp", ts.parse().unwrap());
            h
        };
        assert!(from_discord(&pk, &signed("1000", body), body, 1000));
        assert!(!from_discord(&pk, &signed("1000", body), br#"{"type":2}"#, 1000), "another body");
        assert!(!from_discord(&pk, &signed("1000", body), body, 5000), "an old timestamp");
        assert!(!from_discord(&hex::encode([9u8; 32]), &signed("1000", body), body, 1000), "another key");
        assert!(!from_discord(&pk, &HeaderMap::new(), body, 1000), "no signature");
        assert!(!from_discord("", &signed("1000", body), body, 1000), "no key set");
    }

    #[test]
    fn uploads_may_be_gzipped() {
        let up = json!({ "launcher": "0.3.0", "bridge": { "applied": {} } });
        let mut gz = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
        gz.write_all(up.to_string().as_bytes()).unwrap();
        let mut h = HeaderMap::new();
        h.insert("content-encoding", "gzip".parse().unwrap());
        assert_eq!(body_json(&h, &gz.finish().unwrap()).unwrap().launcher, "0.3.0");
        assert_eq!(body_json(&HeaderMap::new(), up.to_string().as_bytes()).unwrap().launcher, "0.3.0");
        assert!(body_json(&h, b"plain").is_err());
    }
}
