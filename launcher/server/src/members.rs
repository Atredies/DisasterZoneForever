//! Member keys: what a launcher shows to sync. /launcher in Discord gives a one-time code (15 minutes); the launcher
//! trades it for a key (POST /api/link). The server keeps only each key's SHA-256 (one document per key in the store:
//! members/<digest>.json), with the Discord user it belongs to; a user has at most MAX_KEYS (one per PC), the oldest
//! goes when a new one is made. The codes waiting to be redeemed are in launcher_codes.json (the answer to /launcher
//! and the launcher's POST may reach different copies of the bot).

use crate::store;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const CODE_LIFE: u64 = 15 * 60;
const MAX_KEYS: usize = 3;
/// (no 0/O, 1/I: read off a screen and typed)
const CODE_ALPHABET: &[u8] = b"ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const CODES: &str = "launcher_codes.json";
const LEGACY: &str = "members.json";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Member {
    /// Discord user id
    pub user: String,
    /// their Discord name when the key was made
    pub name: String,
    pub made: u64,
    #[serde(default)]
    pub seen: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct Code {
    code: String,
    user: String,
    name: String,
    until: u64,
}

fn random(n: usize) -> Vec<u8> {
    let mut b = vec![0u8; n];
    getrandom::fill(&mut b).expect("the OS has no random numbers");
    b
}

fn digest(key: &str) -> String {
    hex::encode(Sha256::digest(key.trim().as_bytes()))
}

fn doc(digest: &str) -> String {
    format!("members/{digest}.json")
}

/// Every key: (digest, member).
fn all() -> Vec<(String, Member)> {
    store::list::<Member>("members/")
        .into_iter()
        .filter_map(|(k, m)| Some((k.strip_prefix("members/")?.strip_suffix(".json")?.to_string(), m)))
        .collect()
}

/// A data folder from before keys had a document each: its members.json is split up (once, at start).
pub fn import_legacy() {
    let Some(old) = store::load_opt::<std::collections::BTreeMap<String, Member>>(LEGACY) else { return };
    for (d, m) in old {
        if let Err(e) = store::update(&doc(&d), |cur: &mut Option<Member>| {
            if cur.is_none() {
                *cur = Some(m.clone());
            }
        }) {
            eprintln!("members: import: {e}");
            return;
        }
    }
    let _ = store::delete(LEGACY);
    eprintln!("members: members.json split into members/");
}

/// A new one-time code for this Discord user (their older codes stop working).
pub fn new_code(user: &str, name: &str, now: u64) -> String {
    let code: String = random(8).iter().map(|b| CODE_ALPHABET[(*b as usize) % CODE_ALPHABET.len()] as char).collect();
    let made = Code { code: code.clone(), user: user.to_string(), name: name.to_string(), until: now + CODE_LIFE };
    if let Err(e) = store::update(CODES, |codes: &mut Vec<Code>| {
        codes.retain(|c| c.user != user && c.until > now);
        codes.push(made.clone());
    }) {
        eprintln!("members: code: {e}");
    }
    code
}

/// Trade a code for a key: (key, Discord name), or None when the code is unknown or too old.
pub fn redeem(code: &str, now: u64) -> Option<(String, String)> {
    let want: String = code.trim().to_uppercase().chars().filter(|c| c.is_ascii_alphanumeric()).collect();
    // (taken out in one step: a code works once, even when two launchers send it at the same moment)
    let c = store::update(CODES, |codes: &mut Vec<Code>| {
        let i = codes.iter().position(|c| c.code == want && c.until > now)?;
        Some(codes.remove(i))
    })
    .ok()??;
    let key = hex::encode(random(32));
    let mut theirs: Vec<(String, u64)> = all().into_iter().filter(|(_, m)| m.user == c.user).map(|(d, m)| (d, m.made)).collect();
    theirs.sort_by_key(|(_, made)| *made);
    while theirs.len() >= MAX_KEYS {
        let _ = store::delete(&doc(&theirs.remove(0).0));
    }
    store::save(&doc(&digest(&key)), &Member { user: c.user, name: c.name.clone(), made: now, seen: now }).ok()?;
    Some((key, c.name))
}

/// Whose key this is (and note when it was last used).
pub fn check(key: &str, now: u64) -> Option<Member> {
    let d = digest(key);
    let m: Member = store::load_opt(&doc(&d))?;
    // (seen is written at most every 10 minutes: one sync a minute per member is not a write each)
    if now >= m.seen + 600 {
        let _ = store::update(&doc(&d), |cur: &mut Option<Member>| {
            if let Some(c) = cur.as_mut() {
                c.seen = c.seen.max(now);
            }
        });
    }
    Some(m)
}

/// Forget every key of a Discord user (their launchers stop syncing until they link again).
pub fn forget(user: &str) -> usize {
    let mine: Vec<String> = all().into_iter().filter(|(_, m)| m.user == user).map(|(d, _)| d).collect();
    for d in &mine {
        let _ = store::delete(&doc(d));
    }
    mine.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn codes_become_keys_once() {
        let (_d, _g) = crate::bridge::tests::scratch();
        let code = new_code("42", "Tsumi", 100);
        assert_eq!(code.len(), 8);
        assert!(redeem("nope", 101).is_none());
        let (key, name) = redeem(&code.to_lowercase(), 101).unwrap();
        assert_eq!(name, "Tsumi");
        assert!(redeem(&code, 102).is_none()); // (once)
        assert_eq!(check(&key, 103).unwrap().user, "42");
        assert!(check("not-a-key", 103).is_none());
        assert_eq!(forget("42"), 1);
        assert!(check(&key, 104).is_none());
    }

    #[test]
    fn codes_run_out_and_old_keys_go() {
        let (_d, _g) = crate::bridge::tests::scratch();
        let code = new_code("42", "Tsumi", 100);
        assert!(redeem(&code, 100 + CODE_LIFE + 1).is_none());
        let keys: Vec<String> = (0..4).map(|i| redeem(&new_code("42", "Tsumi", 200 + i), 201 + i).unwrap().0).collect();
        assert!(check(&keys[0], 300).is_none()); // (the fourth PC pushed the first out)
        assert!(keys[1..].iter().all(|k| check(k, 300).is_some()));
    }

    #[test]
    fn an_old_members_file_is_split_up() {
        let (_d, _g) = crate::bridge::tests::scratch();
        let key = "k1";
        let mut old = std::collections::BTreeMap::new();
        old.insert(digest(key), Member { user: "42".into(), name: "Tsumi".into(), made: 5, seen: 5 });
        store::save(LEGACY, &old).unwrap();
        import_legacy();
        assert_eq!(check(key, 6).unwrap().name, "Tsumi");
        assert!(store::load_opt::<serde_json::Value>(LEGACY).is_none());
        import_legacy(); // (nothing left to do)
        assert_eq!(all().len(), 1);
    }

    #[test]
    fn a_code_works_once_even_from_two_launchers_at_once() {
        let (_d, _g) = crate::bridge::tests::scratch();
        let code = new_code("42", "Tsumi", 100);
        let wins = std::sync::Mutex::new(0);
        std::thread::scope(|s| {
            for _ in 0..6 {
                s.spawn(|| {
                    if redeem(&code, 101).is_some() {
                        *wins.lock().unwrap() += 1;
                    }
                });
            }
        });
        assert_eq!(*wins.lock().unwrap(), 1);
    }
}
