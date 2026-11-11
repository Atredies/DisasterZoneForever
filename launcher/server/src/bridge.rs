//! The bot's state about Discord changes for the game, and the signed queue of them (in the store, store.rs):
//!
//!   bridge_queue.json     records the game has not taken yet (each signed when it is made: dz_proto::Record)
//!   bridge_profiles.json  the characters each Discord user made in Discord
//!   bridge_channels.json  the server's text channels (for the addon's Settings > Discord dropdowns)
//!   bridge_links.json     the hash and revision of the badge list last sent
//!   bridge_key.json(+.leaves)  the signing key (dz-server keygen); on AWS its secret is a parameter and the used
//!                         leaves are a counter in the store (signer_next), see [`set_counted_signer`]
//!
//! A record leaves the queue once any member's game marked it applied (DisasterZoneBridgeDB.applied, uploaded by
//! their launcher after the save).

use crate::core::error::Result;
use crate::store;
use dz_proto::wots::Signer;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

pub use dz_proto::{Channel, Record};

/// How the bot signs: with the key file it saves after each signature (one server), or with a key whose leaves are
/// handed out by the store's atomic counter (many copies at once, on AWS).
enum Signing {
    File(Signer),
    Counted(Signer),
}

static SIGNER: Mutex<Option<Signing>> = Mutex::new(None);

/// The store's counter of used leaves (a Counted key).
pub const SIGNER_COUNTER: &str = "signer_next";

/// Sign with this key file (saved as used before each signature).
pub fn set_signer(s: Signer) {
    *SIGNER.lock().unwrap() = Some(Signing::File(s));
}

/// Sign with this key, taking each leaf from the store's counter (it starts at the key file's `next`).
pub fn set_counted_signer(s: Signer) {
    // (what a copy without the key needs to say how many are left: /api/health on the api function)
    let info = SignerInfo { capacity: s.capacity(), first: s.first_unused() as u64 };
    if let Err(e) = store::save(SIGNER_INFO, &info) {
        eprintln!("bridge: signer info: {e}");
    }
    *SIGNER.lock().unwrap() = Some(Signing::Counted(s));
}

const SIGNER_INFO: &str = "signer_info.json";

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct SignerInfo {
    capacity: u64,
    first: u64,
}

/// Signatures the key has left (None: no key known).
pub fn signatures_left() -> Option<u64> {
    let g = SIGNER.lock().unwrap();
    let Some(signing) = g.as_ref() else {
        // no key here (the api function): the worker's counted key, if it said what it is
        let info: SignerInfo = store::load_opt(SIGNER_INFO)?;
        let next = store::backend().peek(SIGNER_COUNTER).ok().flatten().unwrap_or(info.first).max(info.first);
        return Some(info.capacity.saturating_sub(next));
    };
    match signing {
        Signing::File(s) => Some(s.left()),
        Signing::Counted(s) => {
            let next = store::backend().peek(SIGNER_COUNTER).ok().flatten().unwrap_or(s.first_unused() as u64);
            Some(s.capacity().saturating_sub(next.max(s.first_unused() as u64)))
        }
    }
}

/// The public half of the key in use (tests, /api/health).
pub fn public_key() -> Option<dz_proto::wots::PublicKey> {
    SIGNER.lock().unwrap().as_ref().map(|s| match s {
        Signing::File(s) | Signing::Counted(s) => s.public(),
    })
}

fn sign(message: &[u8]) -> Result<Vec<u8>> {
    let err = |e: &dyn std::fmt::Display| crate::core::Error::Msg(e.to_string());
    let mut g = SIGNER.lock().unwrap();
    match g.as_mut().ok_or_else(|| crate::core::Error::Msg("the bot has no signing key (dz-server keygen)".into()))? {
        Signing::File(s) => s.sign(message).map_err(|e| err(&e)),
        Signing::Counted(s) => {
            // (the leaf is ours alone once the counter handed it out: nothing else can sign with it)
            let leaf = store::backend()
                .take(SIGNER_COUNTER, s.first_unused() as u64, s.capacity())?
                .ok_or_else(|| err(&dz_proto::wots::KeyError::Spent))?;
            s.sign_leaf(leaf as u32, message).map_err(|e| err(&e))
        }
    }
}

/// A file in the data folder (the files that are not the bot's state: the key, BridgeKey.lua, the art).
pub fn path(name: &str) -> PathBuf {
    crate::data_dir().join(name)
}

// ------------------------------------------------------------------------------------------------------------------
// Profiles: the characters each Discord user made in Discord (name, class, spec). No proof is asked; one name
// belongs to one Discord user.
// ------------------------------------------------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Char {
    /// as the game writes it: "Lee" or "Lee-Thunderstrike"
    pub name: String,
    /// class file: "WARRIOR"
    pub class: String,
    /// 1-based index into the class's specs (addon ns.SPECS)
    pub spec: u32,
    /// the Discord name of whoever made it (the addon shows a badge after the character's name)
    #[serde(default)]
    pub by: String,
}

/// Discord user id -> their characters (the first is their main)
pub type Profiles = std::collections::BTreeMap<String, Vec<Char>>;

const PROFILES: &str = "bridge_profiles.json";
const QUEUE: &str = "bridge_queue.json";
const CHANNELS: &str = "bridge_channels.json";
const LINKS: &str = "bridge_links.json";

pub fn load_profiles() -> Profiles {
    store::load(PROFILES)
}

/// Save the characters made in Discord; the game's badges follow (a new signed "links" record).
pub fn save_profiles(p: &Profiles) -> Result<()> {
    store::save(PROFILES, p)?;
    push_links(p)
}

/// Change the characters made in Discord in one step (nobody else's change in between is lost); the badges follow.
pub fn update_profiles<R>(f: impl FnMut(&mut Profiles) -> R) -> Result<R> {
    let r = store::update(PROFILES, f)?;
    push_links(&load_profiles())?;
    Ok(r)
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct LinksState {
    #[serde(default)]
    hash: String,
    #[serde(default)]
    rev: u64,
}

/// The badges as a signed record { rev, l = { [character] = Discord name } } (addon Core/Bridge.lua "links"); an
/// older one still waiting is dropped. Nothing when they are the ones last sent (bridge_links.json keeps their hash).
pub fn push_links(p: &Profiles) -> Result<()> {
    let l: serde_json::Map<String, Value> = links(p).into_iter().map(|k| (k.name, Value::String(k.discord))).collect();
    let hash = hex::encode(<sha2::Sha256 as sha2::Digest>::digest(serde_json::to_vec(&l).unwrap_or_default()));
    let now = crate::bot::unix_now();
    // (claim the new revision first: two copies of the bot sending the same list at once send it once)
    let claimed = store::update(LINKS, |st: &mut LinksState| {
        if st.hash == hash {
            return None;
        }
        // (a rev above the last one even if the clock stepped back: the game keeps the higher)
        st.rev = now.max(st.rev + 1);
        st.hash = hash.clone();
        Some(st.rev)
    })?;
    let Some(rev) = claimed else { return Ok(()) };
    let mut r = Record {
        id: format!("ln_{rev}"),
        kind: "links".into(),
        at: now,
        by: "DisasterZone".into(),
        body: serde_json::json!({ "rev": rev, "l": l }),
        discord: String::new(),
        sig: String::new(),
    };
    r.sig = hex::encode(sign(&r.message().map_err(|e| crate::core::Error::Msg(e.to_string()))?)?);
    store::update(QUEUE, |q: &mut Vec<Record>| {
        // (an older list still waiting is replaced; a newer one, sent meanwhile, wins)
        if q.iter().any(|x| x.kind == "links" && x.body.get("rev").and_then(|v| v.as_u64()).unwrap_or(0) > rev) {
            return;
        }
        q.retain(|x| x.kind != "links");
        q.push(r.clone());
    })?;
    Ok(())
}

/// The characters made in Discord, for the addon's badges.
pub fn links(p: &Profiles) -> Vec<dz_proto::Link> {
    p.values()
        .flatten()
        .map(|c| dz_proto::Link { name: c.name.clone(), discord: if c.by.is_empty() { "Discord".into() } else { c.by.clone() } })
        .collect()
}

fn short_lower(name: &str) -> String {
    name.split('-').next().unwrap_or(name).to_lowercase()
}

/// Who has this character already (another user's claim on "Lee" is refused).
pub fn owner_of(p: &Profiles, name: &str) -> Option<String> {
    let want = short_lower(name);
    p.iter().find(|(_, chars)| chars.iter().any(|c| short_lower(&c.name) == want)).map(|(u, _)| u.clone())
}

/// "aRAKIS" -> "Arakis": the first letter upper case, the rest lower.
fn word_case(w: &str) -> String {
    let mut out: String = w.chars().take(1).flat_map(|c| c.to_uppercase()).collect();
    out.extend(w.chars().skip(1).flat_map(|c| c.to_lowercase()));
    out
}

/// A name as WoW writes it: each word's first letter upper, the rest lower ("lEE" -> "Lee", Forever's
/// "arakis  war" -> "Arakis War"); a realm after '-' is kept as typed.
pub fn tidy_name(name: &str) -> String {
    let name = name.trim();
    let (n, realm) = match name.split_once('-') {
        Some((n, r)) => (n, Some(r)),
        None => (name, None),
    };
    // each word capitalised: TBC names are one word, Forever's are "Name Surname" (one space between)
    let mut out = n.split_whitespace().map(word_case).collect::<Vec<_>>().join(" ");
    if let Some(r) = realm.filter(|r| !r.is_empty()) {
        out.push('-');
        out.push_str(r);
    }
    out
}

// ------------------------------------------------------------------------------------------------------------------
// Files
// ------------------------------------------------------------------------------------------------------------------

/// A file in the data folder written whole (not the bot's state: that is in the store).
pub fn save_json<T: Serialize + ?Sized>(p: &Path, v: &T) -> Result<()> {
    std::fs::create_dir_all(p.parent().unwrap())?;
    let tmp = p.with_extension("tmp");
    std::fs::write(&tmp, serde_json::to_vec_pretty(v).unwrap())?;
    std::fs::rename(&tmp, p)?;
    Ok(())
}

pub fn load_channels() -> Vec<Channel> {
    store::load(CHANNELS)
}

pub fn save_channels(c: &[Channel]) -> Result<()> {
    store::save(CHANNELS, c)
}

/// A Lua array as the launcher uploads it (an object with keys "1", "2", ...) in order; any other value: empty.
pub fn lua_list(v: Option<&Value>) -> Vec<&Value> {
    let Some(Value::Object(m)) = v else { return Vec::new() };
    let mut out: Vec<(usize, &Value)> = m.iter().filter_map(|(k, x)| Some((k.parse().ok()?, x))).collect();
    out.sort_by_key(|(i, _)| *i);
    out.into_iter().map(|(_, x)| x).collect()
}

// ------------------------------------------------------------------------------------------------------------------
// The queue
// ------------------------------------------------------------------------------------------------------------------

pub fn load_queue() -> Vec<Record> {
    store::load(QUEUE)
}

/// Sign a record and queue it for the game. Returns the records now waiting.
pub fn push(mut r: Record) -> Result<Vec<Record>> {
    let message = r.message().map_err(|e| crate::core::Error::Msg(e.to_string()))?;
    r.sig = hex::encode(sign(&message)?);
    // (a record nobody could take in two weeks - a guest when no raid leader syncs - is dropped)
    let cut = r.at.saturating_sub(MAX_AGE);
    store::update(QUEUE, |q: &mut Vec<Record>| {
        q.retain(|x| x.at >= cut && x.id != r.id);
        q.push(r.clone());
        q.clone()
    })
}

/// How long a record waits for a game to take it.
const MAX_AGE: u64 = 14 * 86400;

/// A member's game took these records (DisasterZoneBridgeDB.applied: { [id] = { ok, why } }): they leave the queue.
/// Returns the ones it refused, with why (told to whoever made them).
pub fn take_applied(applied: Option<&Value>) -> Result<Vec<(Record, String)>> {
    let Some(Value::Object(applied)) = applied else { return Ok(Vec::new()) };
    store::update(QUEUE, |all: &mut Vec<Record>| {
        let (mut keep, mut failed) = (Vec::new(), Vec::new());
        for r in all.drain(..) {
            match applied.get(&r.id) {
                None => keep.push(r),
                Some(m) => {
                    if m.get("ok").and_then(|x| x.as_bool()) != Some(true) {
                        let why = m.get("why").and_then(|x| x.as_str()).unwrap_or("refused").to_string();
                        failed.push((r, why));
                    }
                }
            }
        }
        *all = keep;
        failed
    })
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use serde_json::json;

    /// A data folder of its own and a small signing key, for tests that touch the bot's files (one at a time: the
    /// data folder is global).
    pub fn scratch() -> (tempfile::TempDir, std::sync::MutexGuard<'static, ()>) {
        static ONE: Mutex<()> = Mutex::new(());
        let g = ONE.lock().unwrap_or_else(|e| e.into_inner());
        let dir = tempfile::tempdir().unwrap();
        crate::set_data_dir(dir.path().to_path_buf());
        store::set(std::sync::Arc::new(store::FileStore::new(dir.path().to_path_buf())));
        set_signer(Signer::create(&dir.path().join("bridge_key.json"), 3, &[5u8; 48]).unwrap());
        (dir, g)
    }

    fn rec(id: &str) -> Record {
        Record { id: id.into(), kind: "test".into(), at: 1, by: "Tsumi".into(), body: json!({ "text": "x" }), discord: "42".into(), sig: String::new() }
    }

    #[test]
    fn records_are_signed_and_leave_when_taken() {
        let (_d, _g) = scratch();
        push(rec("dc_1")).unwrap();
        let q = push(rec("dc_2")).unwrap();
        assert_eq!(q.len(), 2);
        let pk = public_key().unwrap();
        for r in &q {
            assert!(dz_proto::wots::verify(&pk, &r.message().unwrap(), &hex::decode(&r.sig).unwrap()));
        }
        let failed = take_applied(Some(&json!({ "dc_1": { "ok": true }, "dc_2": { "ok": false, "why": "over" }, "old": { "ok": true } }))).unwrap();
        assert!(load_queue().is_empty());
        assert_eq!(failed.len(), 1);
        assert_eq!(failed[0].1, "over");
        assert_eq!(failed[0].0.discord, "42");
    }

    #[test]
    fn a_counted_key_uses_each_leaf_once_and_stops_when_spent() {
        let (d, _g) = scratch();
        // a key whose file says leaf 2 is next (two were used before it moved to the store's counter)
        let p = d.path().join("k.json");
        let mut s = Signer::create(&p, 3, &[9u8; 48]).unwrap();
        s.sign(b"a").unwrap();
        s.sign(b"b").unwrap();
        let leaves = std::fs::read(d.path().join("k.json.leaves")).unwrap();
        let counted = Signer::from_parts(&std::fs::read(&p).unwrap(), &leaves).unwrap();
        let pk = counted.public();
        set_counted_signer(counted);
        assert_eq!(signatures_left(), Some(6));
        let mut used = Vec::new();
        for n in 0..6 {
            let q = push(rec(&format!("c{n}"))).unwrap();
            let r = q.last().unwrap();
            let sig = hex::decode(&r.sig).unwrap();
            assert!(dz_proto::wots::verify(&pk, &r.message().unwrap(), &sig));
            used.push(u32::from_be_bytes(sig[..4].try_into().unwrap()));
        }
        assert_eq!(used, vec![2, 3, 4, 5, 6, 7]);
        assert_eq!(signatures_left(), Some(0));
        assert!(push(rec("one-too-many")).is_err(), "a spent key refuses");
        assert_eq!(load_queue().len(), 6);
    }

    #[test]
    fn badges_go_out_signed_once_per_change() {
        let (_d, _g) = scratch();
        let mut p = Profiles::new();
        p.insert("1".into(), vec![Char { name: "Lee".into(), class: "WARRIOR".into(), spec: 3, by: "LeeD".into() }]);
        save_profiles(&p).unwrap();
        save_profiles(&p).unwrap(); // (unchanged: no second record)
        let q = load_queue();
        assert_eq!(q.len(), 1);
        assert_eq!(q[0].kind, "links");
        assert_eq!(q[0].body["l"]["Lee"], json!("LeeD"));
        p.get_mut("1").unwrap().push(Char { name: "Ann".into(), class: "MAGE".into(), spec: 1, by: "LeeD".into() });
        save_profiles(&p).unwrap();
        let q = load_queue();
        assert_eq!(q.len(), 1); // (the older list is replaced)
        assert!(q[0].body["l"].get("Ann").is_some());
        assert!(q[0].body["rev"].as_u64().unwrap() > 0);
    }

    #[test]
    fn old_records_expire() {
        let (_d, _g) = scratch();
        push(Record { at: 1000, ..rec("old") }).unwrap();
        let q = push(Record { at: 1000 + MAX_AGE + 1, ..rec("new") }).unwrap();
        assert_eq!(q.iter().map(|r| r.id.as_str()).collect::<Vec<_>>(), vec!["new"]);
    }

    #[test]
    fn one_name_one_owner() {
        let mut p = Profiles::new();
        p.insert("1".into(), vec![Char { name: "Lee".into(), class: "WARRIOR".into(), spec: 3, by: String::new() }]);
        assert_eq!(owner_of(&p, "lee").as_deref(), Some("1"));
        assert_eq!(owner_of(&p, "LEE-Thunderstrike").as_deref(), Some("1"));
        assert_eq!(owner_of(&p, "Rita"), None);
        assert_eq!(links(&p)[0].discord, "Discord");
    }

    #[test]
    fn names_are_tidied_as_the_game_writes_them() {
        assert_eq!(tidy_name(" lEE "), "Lee");
        assert_eq!(tidy_name("élise-Thunderstrike"), "Élise-Thunderstrike");
        assert_eq!(tidy_name("bob-"), "Bob");
        assert_eq!(tidy_name("arakis  WAR"), "Arakis War");
        assert_eq!(tidy_name(" aurel namahs-CAMWOWEU4Realm4PvP"), "Aurel Namahs-CAMWOWEU4Realm4PvP");
    }
}
