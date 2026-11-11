//! The bot's slow work, as jobs: the answer to a deferred interaction, the raid posts, the refusal DMs, the reminder
//! tick, the setup. Where they run:
//!   - one server (no queue set): a task in this process, as the bot always did;
//!   - AWS (aws.rs sets a queue): an SQS FIFO queue, read by the worker Lambda. Everything that edits the raid posts
//!     or sends DMs from the bot's side runs in one message group, one at a time ([`Job::group`]), so two copies never
//!     post the same raid twice or race Discord's rate limits; each interaction has a group of its own.
//!
//! A job may run twice (a queue retries after a failure): each one is safe to repeat (posts compare hashes, reminders
//! are claimed before they are sent, an interaction is answered once: [`claim_interaction`]).

use crate::core::Result;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, RwLock};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "job", rename_all = "snake_case")]
pub enum Job {
    /// a Discord interaction already acknowledged (bot::deferral): its JSON as Discord sent it
    Interaction { raw: String },
    /// post new raids and edit changed ones (posts::update)
    Posts,
    /// tell people their Discord changes were refused by the game
    Tell { failed: Vec<(crate::bridge::Record, String)> },
    /// the reminder DMs (every minute)
    Tick,
    /// commands, channels, emoji, badges (at deploy and every hour)
    Setup,
}

impl Job {
    /// The queue's message group: jobs of one group run one at a time, in order.
    pub fn group(&self) -> String {
        match self {
            Job::Interaction { raw } => {
                let id = serde_json::from_str::<serde_json::Value>(raw)
                    .ok()
                    .and_then(|v| v.get("id").and_then(|x| x.as_str()).map(str::to_string))
                    .unwrap_or_default();
                format!("i-{}", crate::store::safe(&id))
            }
            _ => "discord".into(),
        }
    }

    /// What makes two sends of the same job the same message (the queue drops the second within 5 minutes).
    #[cfg_attr(not(feature = "aws"), allow(dead_code))]
    pub fn dedup(&self, now: u64) -> String {
        match self {
            Job::Interaction { .. } => self.group(),
            // (one tick a minute, setup once a minute, each refusal once; every posts request is its own: one that
            // came after an update already ran must run again, and an update with nothing new is cheap)
            Job::Tick => format!("tick-{}", now / 60),
            Job::Posts => format!("posts-{now}-{:016x}", crate::store::rand_u64()),
            Job::Setup => format!("setup-{}", now / 60),
            Job::Tell { failed } => {
                let ids: Vec<&str> = failed.iter().map(|(r, _)| r.id.as_str()).collect();
                format!("tell-{}", hex::encode(&<sha2::Sha256 as sha2::Digest>::digest(ids.join(",").as_bytes())[..16]))
            }
        }
    }
}

/// Where jobs go when they don't run here.
pub trait Queue: Send + Sync {
    fn send(&self, job: &Job) -> Result<()>;
}

static QUEUE: RwLock<Option<Arc<dyn Queue>>> = RwLock::new(None);

#[cfg_attr(not(feature = "aws"), allow(dead_code))]
pub fn set_queue(q: Arc<dyn Queue>) {
    *QUEUE.write().unwrap() = Some(q);
}

/// Run this job: on the queue when there is one, else in a task here.
pub fn submit(job: Job) {
    let q = QUEUE.read().unwrap().clone();
    match q {
        Some(q) => {
            if let Err(e) = q.send(&job) {
                eprintln!("jobs: could not queue {:?}: {e}", job.group());
            }
        }
        None => {
            tokio::spawn(async move {
                if let Err(e) = run(job).await {
                    eprintln!("jobs: {e}");
                }
            });
        }
    }
}

/// An interaction is answered once: the first worker to claim its id does it (a queue's retry finds it taken).
pub fn claim_interaction(id: &str, now: u64) -> bool {
    let key = format!("answered/{}.json", crate::store::safe(id));
    crate::store::update(&key, |at: &mut u64| {
        if *at != 0 {
            return false;
        }
        *at = now;
        true
    })
    .unwrap_or(false)
}

/// Do the job (here: the worker, or a task of the one server).
pub async fn run(job: Job) -> Result<()> {
    let Some(http) = crate::bot::http() else {
        // (no Discord client: the bot isn't connected yet; nothing of this can be done without it)
        return Ok(());
    };
    match job {
        Job::Interaction { raw } => {
            let i: twilight_model::application::interaction::Interaction =
                serde_json::from_str(&raw).map_err(|e| crate::core::Error::Msg(format!("interaction: {e}")))?;
            if !claim_interaction(&i.id.get().to_string(), crate::bot::unix_now()) {
                return Ok(());
            }
            let (app_id, _) = crate::bot::ids().map_err(crate::core::Error::Msg)?;
            crate::bot::answer(&http, app_id, &i, crate::bot::Mode::Deferred).await
        }
        Job::Posts => {
            if let Some(snap) = crate::signup::current_snap() {
                // (icons the exported art lacks: fetched once, before the pictures are drawn)
                crate::render::fetch::ensure_items(crate::render::fetch::snapshot_items(&snap)).await;
                crate::posts::update(&http, &snap).await;
            }
            Ok(())
        }
        Job::Tell { failed } => {
            crate::bot::tell(&http, &failed).await;
            Ok(())
        }
        Job::Tick => {
            if let Some(snap) = crate::signup::current_snap() {
                crate::remind::tick(&http, &snap, crate::bot::unix_now() as i64).await;
            }
            Ok(())
        }
        Job::Setup => {
            let (app_id, guild_id) = crate::bot::ids().map_err(crate::core::Error::Msg)?;
            crate::bot::setup(&http, app_id, guild_id, true).await;
            prune_answered(crate::bot::unix_now());
            Ok(())
        }
    }
}

/// Forget the answered marks older than a day (a retry comes within minutes).
pub fn prune_answered(now: u64) {
    for (k, at) in crate::store::list::<u64>("answered/") {
        if at + 86400 < now {
            let _ = crate::store::delete(&k);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jobs_travel_as_json() {
        for j in [Job::Posts, Job::Tick, Job::Setup, Job::Interaction { raw: r#"{"id":"123"}"#.into() }] {
            let t = serde_json::to_string(&j).unwrap();
            assert_eq!(serde_json::from_str::<Job>(&t).unwrap(), j);
        }
        assert_eq!(serde_json::to_value(Job::Tick).unwrap(), serde_json::json!({ "job": "tick" }));
    }

    #[test]
    fn discord_writers_share_one_group_and_interactions_have_their_own() {
        assert_eq!(Job::Posts.group(), Job::Tick.group());
        assert_eq!(Job::Setup.group(), "discord");
        let a = Job::Interaction { raw: r#"{"id":"111"}"#.into() };
        let b = Job::Interaction { raw: r#"{"id":"222"}"#.into() };
        assert_ne!(a.group(), b.group());
        assert_eq!(a.dedup(5), a.group());
        assert_eq!(Job::Tick.dedup(60), Job::Tick.dedup(119));
        assert_ne!(Job::Tick.dedup(60), Job::Tick.dedup(120));
        assert_ne!(Job::Posts.dedup(60), Job::Posts.dedup(60), "a later posts request is never swallowed");
    }

    #[test]
    fn an_interaction_is_answered_once() {
        let (_d, _g) = crate::bridge::tests::scratch();
        assert!(claim_interaction("999", 5));
        assert!(!claim_interaction("999", 6));
        assert!(claim_interaction("1000", 6));
        prune_answered(5 + 86400 + 1);
        assert!(claim_interaction("999", 90_000));
    }
}
