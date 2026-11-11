//! Where the bot keeps its state: small JSON documents by key ("bridge_queue.json", "members/<digest>.json").
//!
//! Two backends behind one interface:
//!   - [`FileStore`]: files in the data folder (one server, the way the bot always ran; same file names as before);
//!   - the AWS one (aws.rs, feature "aws"): DynamoDB items, for the bot on Lambda where many copies run at once.
//!
//! Every read-modify-write goes through [`update`]: it reads the document with its version and writes it back only if
//! nobody wrote it in between (else it reads again and retries), so two copies of the bot can't lose each other's
//! changes. Keys with a "/" are collections: [`list`] reads every document under a prefix.

use crate::core::{Error, Result};
use serde::de::DeserializeOwned;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};

/// A document and the version it was read at (0: it does not exist).
#[derive(Debug, Clone, PartialEq)]
pub struct Doc {
    pub bytes: Vec<u8>,
    pub ver: u64,
}

pub trait Backend: Send + Sync {
    /// The document, or None.
    fn get(&self, key: &str) -> Result<Option<Doc>>;
    /// Write `bytes` if the document is still at version `expect` (0: it must not exist yet). Ok(false): someone
    /// else wrote it first (read it again).
    fn put_if(&self, key: &str, bytes: &[u8], expect: u64) -> Result<bool>;
    /// Remove a document (no error when it is not there).
    fn delete(&self, key: &str) -> Result<()>;
    /// Every document whose key starts with `prefix` (a collection: "members/"), as (key, bytes).
    fn list(&self, prefix: &str) -> Result<Vec<(String, Vec<u8>)>>;
    /// Atomically take the next number of a counter that starts at `start` and stops before `limit`: the number
    /// taken, or None when it reached `limit`. No number is ever handed out twice, whatever runs at the same time.
    fn take(&self, key: &str, start: u64, limit: u64) -> Result<Option<u64>>;
    /// The number a counter would hand out next (None: never used).
    fn peek(&self, key: &str) -> Result<Option<u64>>;
}

static STORE: RwLock<Option<Arc<dyn Backend>>> = RwLock::new(None);

/// Use this backend from now on (main / the Lambda start / tests).
pub fn set(b: Arc<dyn Backend>) {
    *STORE.write().unwrap() = Some(b);
}

/// The backend in use: the one set, else files in the data folder.
pub fn backend() -> Arc<dyn Backend> {
    if let Some(b) = STORE.read().unwrap().clone() {
        return b;
    }
    Arc::new(FileStore::new(crate::data_dir()))
}

// ------------------------------------------------------------------------------------------------------------------
// JSON helpers (what the bot's modules use)
// ------------------------------------------------------------------------------------------------------------------

/// The document as T, or T::default() when it is missing or unreadable (as the bot always read its files).
pub fn load<T: DeserializeOwned + Default>(key: &str) -> T {
    match backend().get(key) {
        Ok(Some(d)) => serde_json::from_slice(&d.bytes).unwrap_or_default(),
        Ok(None) => T::default(),
        Err(e) => {
            eprintln!("store: read {key}: {e}");
            T::default()
        }
    }
}

/// The document as T, or None when it is missing or unreadable.
pub fn load_opt<T: DeserializeOwned>(key: &str) -> Option<T> {
    match backend().get(key) {
        Ok(Some(d)) => serde_json::from_slice(&d.bytes).ok(),
        Ok(None) => None,
        Err(e) => {
            eprintln!("store: read {key}: {e}");
            None
        }
    }
}

fn to_bytes<T: Serialize + ?Sized>(v: &T) -> Vec<u8> {
    serde_json::to_vec_pretty(v).unwrap_or_default()
}

/// How often [`update`] reads again after a conflict before it gives up.
const TRIES: usize = 20;

/// Read the document, change it with `f`, write it back if nobody wrote it meanwhile (else run `f` again on the newer
/// one). Nothing is written when `f` left it as it was. Returns what `f` returned the time it was saved.
pub fn update<T, R>(key: &str, mut f: impl FnMut(&mut T) -> R) -> Result<R>
where
    T: Serialize + DeserializeOwned + Default,
{
    let b = backend();
    for _ in 0..TRIES {
        let cur = b.get(key)?;
        let (mut v, ver, before) = match &cur {
            Some(d) => (serde_json::from_slice(&d.bytes).unwrap_or_default(), d.ver, d.bytes.clone()),
            None => (T::default(), 0, Vec::new()),
        };
        let r = f(&mut v);
        let after = to_bytes(&v);
        if cur.is_some() && after == before {
            return Ok(r);
        }
        if cur.is_none() && after == to_bytes(&T::default()) {
            return Ok(r); // (still empty: no document needed)
        }
        if b.put_if(key, &after, ver)? {
            return Ok(r);
        }
        // (someone else wrote it: a short pause, then again with theirs)
        std::thread::sleep(std::time::Duration::from_millis(5 + (rand_u64() % 20)));
    }
    Err(Error::Msg(format!("store: {key} kept changing under us ({TRIES} tries)")))
}

/// Write the document whatever is there now (for a value one writer owns, e.g. the guild picture after its merge).
pub fn save<T: Serialize + ?Sized>(key: &str, v: &T) -> Result<()> {
    let b = backend();
    let bytes = to_bytes(v);
    for _ in 0..TRIES {
        let ver = b.get(key)?.map_or(0, |d| d.ver);
        if b.put_if(key, &bytes, ver)? {
            return Ok(());
        }
    }
    Err(Error::Msg(format!("store: could not write {key}")))
}

pub fn delete(key: &str) -> Result<()> {
    backend().delete(key)
}

/// Every document under `prefix` as T (unreadable ones skipped), with its key.
pub fn list<T: DeserializeOwned>(prefix: &str) -> Vec<(String, T)> {
    match backend().list(prefix) {
        Ok(all) => all.into_iter().filter_map(|(k, b)| Some((k, serde_json::from_slice(&b).ok()?))).collect(),
        Err(e) => {
            eprintln!("store: list {prefix}: {e}");
            Vec::new()
        }
    }
}

/// A key-safe form of an id (Discord ids and hex digests already are; anything else is hashed).
pub fn safe(id: &str) -> String {
    if !id.is_empty() && id.len() <= 80 && id.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-') {
        id.to_string()
    } else {
        hex::encode(&Sha256::digest(id.as_bytes())[..16])
    }
}

pub fn rand_u64() -> u64 {
    let mut b = [0u8; 8];
    getrandom::fill(&mut b).expect("the OS has no random numbers");
    u64::from_le_bytes(b)
}

// ------------------------------------------------------------------------------------------------------------------
// Files in the data folder
// ------------------------------------------------------------------------------------------------------------------

/// One process owns the folder (the bot on one server), so a lock in this process is enough for [`Backend::put_if`].
/// A document's version is a hash of its bytes.
pub struct FileStore {
    root: PathBuf,
}

/// (one lock for every FileStore: tests make several over the same folder)
static FILE_LOCK: Mutex<()> = Mutex::new(());

impl FileStore {
    pub fn new(root: PathBuf) -> FileStore {
        FileStore { root }
    }

    fn path(&self, key: &str) -> Result<PathBuf> {
        if key.is_empty() || key.split('/').any(|p| p.is_empty() || p == "." || p == "..") || key.contains('\\') {
            return Err(Error::Msg(format!("store: bad key {key:?}")));
        }
        Ok(self.root.join(key))
    }

    fn ver_of(bytes: &[u8]) -> u64 {
        // (never 0: 0 means "missing")
        u64::from_le_bytes(Sha256::digest(bytes)[..8].try_into().unwrap()) | 1
    }
}

fn write_atomic(p: &Path, data: &[u8]) -> std::io::Result<()> {
    if let Some(d) = p.parent() {
        std::fs::create_dir_all(d)?;
    }
    let tmp = p.with_extension("tmp");
    std::fs::write(&tmp, data)?;
    std::fs::rename(&tmp, p)
}

impl Backend for FileStore {
    fn get(&self, key: &str) -> Result<Option<Doc>> {
        match std::fs::read(self.path(key)?) {
            Ok(bytes) => Ok(Some(Doc { ver: Self::ver_of(&bytes), bytes })),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    fn put_if(&self, key: &str, bytes: &[u8], expect: u64) -> Result<bool> {
        let p = self.path(key)?;
        let _g = FILE_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let now = match std::fs::read(&p) {
            Ok(b) => Self::ver_of(&b),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => 0,
            Err(e) => return Err(e.into()),
        };
        if now != expect {
            return Ok(false);
        }
        write_atomic(&p, bytes)?;
        Ok(true)
    }

    fn delete(&self, key: &str) -> Result<()> {
        let _g = FILE_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        match std::fs::remove_file(self.path(key)?) {
            Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(e.into()),
            _ => Ok(()),
        }
    }

    fn list(&self, prefix: &str) -> Result<Vec<(String, Vec<u8>)>> {
        // (a prefix is a folder plus the start of a file name: "members/" or "members/ab")
        let (dir, start) = match prefix.rsplit_once('/') {
            Some((d, s)) => (self.path(d)?, s),
            None => (self.root.clone(), prefix),
        };
        let folder = prefix.rsplit_once('/').map(|(d, _)| format!("{d}/")).unwrap_or_default();
        let mut out = Vec::new();
        let rd = match std::fs::read_dir(&dir) {
            Ok(rd) => rd,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(out),
            Err(e) => return Err(e.into()),
        };
        for e in rd.flatten() {
            let name = e.file_name().to_string_lossy().to_string();
            if !name.starts_with(start) || name.ends_with(".tmp") || !e.path().is_file() {
                continue;
            }
            if let Ok(b) = std::fs::read(e.path()) {
                out.push((format!("{folder}{name}"), b));
            }
        }
        out.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(out)
    }

    fn take(&self, key: &str, start: u64, limit: u64) -> Result<Option<u64>> {
        let p = self.path(key)?;
        let _g = FILE_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let next: u64 = std::fs::read_to_string(&p).ok().and_then(|t| t.trim().parse().ok()).unwrap_or(start).max(start);
        if next >= limit {
            return Ok(None);
        }
        // (saved as taken before anyone uses it)
        write_atomic(&p, (next + 1).to_string().as_bytes())?;
        Ok(Some(next))
    }

    fn peek(&self, key: &str) -> Result<Option<u64>> {
        Ok(std::fs::read_to_string(self.path(key)?).ok().and_then(|t| t.trim().parse().ok()))
    }
}

// ------------------------------------------------------------------------------------------------------------------
// A document read again only after a while (the guild picture, the presence list: read on every answer)
// ------------------------------------------------------------------------------------------------------------------

pub struct Cached<T> {
    key: &'static str,
    ttl: std::time::Duration,
    slot: Mutex<Option<(std::time::Instant, Option<Arc<T>>)>>,
}

impl<T: DeserializeOwned> Cached<T> {
    pub const fn new(key: &'static str, ttl_ms: u64) -> Cached<T> {
        Cached { key, ttl: std::time::Duration::from_millis(ttl_ms), slot: Mutex::new(None) }
    }

    /// The document, read again when the copy here is older than the ttl.
    pub fn get(&self) -> Option<Arc<T>> {
        let mut g = self.slot.lock().unwrap();
        if let Some((at, v)) = g.as_ref() {
            if at.elapsed() < self.ttl {
                return v.clone();
            }
        }
        let v = load_opt::<T>(self.key).map(Arc::new);
        *g = Some((std::time::Instant::now(), v.clone()));
        v
    }

    /// This process just wrote it: use the new value at once.
    pub fn put(&self, v: T) {
        *self.slot.lock().unwrap() = Some((std::time::Instant::now(), Some(Arc::new(v))));
    }

    pub fn forget(&self) {
        *self.slot.lock().unwrap() = None;
    }
}

// ------------------------------------------------------------------------------------------------------------------
// The interface's promises, checked against any backend (aws.rs runs the same against DynamoDB Local)
// ------------------------------------------------------------------------------------------------------------------

#[cfg(any(test, feature = "aws"))]
pub mod contract {
    use super::*;
    use std::collections::BTreeMap;

    /// Every promise of [`Backend`], on an empty backend.
    pub fn check(b: Arc<dyn Backend>) {
        // get / put_if
        assert_eq!(b.get("a.json").unwrap(), None);
        assert!(!b.put_if("a.json", b"1", 7).unwrap(), "a missing document is at version 0");
        assert!(b.put_if("a.json", b"1", 0).unwrap());
        let d = b.get("a.json").unwrap().unwrap();
        assert_eq!(d.bytes, b"1");
        assert_ne!(d.ver, 0);
        assert!(!b.put_if("a.json", b"2", 0).unwrap(), "it exists now");
        assert!(b.put_if("a.json", b"2", d.ver).unwrap());
        assert!(!b.put_if("a.json", b"3", d.ver).unwrap(), "an old version loses");
        assert_eq!(b.get("a.json").unwrap().unwrap().bytes, b"2");
        // list
        b.put_if("m/x1.json", b"x1", 0).unwrap();
        b.put_if("m/x2.json", b"x2", 0).unwrap();
        b.put_if("m/y1.json", b"y1", 0).unwrap();
        b.put_if("mm.json", b"no", 0).unwrap();
        let keys: Vec<String> = b.list("m/").unwrap().into_iter().map(|(k, _)| k).collect();
        assert_eq!(keys, vec!["m/x1.json", "m/x2.json", "m/y1.json"]);
        assert_eq!(b.list("m/x").unwrap().len(), 2);
        assert!(b.list("none/").unwrap().is_empty());
        // delete
        b.delete("m/x1.json").unwrap();
        b.delete("m/x1.json").unwrap();
        assert_eq!(b.list("m/").unwrap().len(), 2);
        // take / peek
        assert_eq!(b.peek("c").unwrap(), None);
        assert_eq!(b.take("c", 5, 8).unwrap(), Some(5));
        assert_eq!(b.peek("c").unwrap(), Some(6));
        assert_eq!(b.take("c", 0, 8).unwrap(), Some(6), "the start only counts the first time");
        assert_eq!(b.take("c", 0, 8).unwrap(), Some(7));
        assert_eq!(b.take("c", 0, 8).unwrap(), None, "the limit is never handed out");
        assert_eq!(b.take("c", 0, 8).unwrap(), None);
    }

    /// Many threads at once: every counter number once, and no update lost.
    pub fn check_concurrency(b: Arc<dyn Backend>) {
        super::set(b.clone());
        let threads = 8;
        let each = 25;
        let taken = Arc::new(Mutex::new(Vec::new()));
        std::thread::scope(|s| {
            for t in 0..threads {
                let b = b.clone();
                let taken = taken.clone();
                s.spawn(move || {
                    for i in 0..each {
                        let n = b.take("leaf", 0, 1 << 20).unwrap().unwrap();
                        taken.lock().unwrap().push(n);
                        update("tally.json", |m: &mut BTreeMap<String, u32>| {
                            m.insert(format!("{t}-{i}"), 1);
                        })
                        .unwrap();
                    }
                });
            }
        });
        let mut all = taken.lock().unwrap().clone();
        all.sort();
        let n = all.len();
        all.dedup();
        assert_eq!(all.len(), n, "a counter number was handed out twice");
        assert_eq!(n, threads * each);
        let tally: BTreeMap<String, u32> = load("tally.json");
        assert_eq!(tally.len(), threads * each, "an update was lost");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn file_store_keeps_every_promise() {
        let dir = tempfile::tempdir().unwrap();
        contract::check(Arc::new(FileStore::new(dir.path().to_path_buf())));
    }

    #[test]
    fn file_store_under_many_threads() {
        let (_d, _g) = crate::bridge::tests::scratch();
        contract::check_concurrency(backend());
    }

    #[test]
    fn keys_cannot_leave_the_folder() {
        let dir = tempfile::tempdir().unwrap();
        let f = FileStore::new(dir.path().to_path_buf());
        for k in ["../x", "a//b", "", "a/../b", "/abs", "a\\b"] {
            assert!(f.get(k).is_err(), "{k}");
        }
        assert_eq!(safe("123456"), "123456");
        assert_eq!(safe("a/b").len(), 32);
    }

    #[test]
    fn update_writes_only_changes_and_retries_on_conflict() {
        let (_d, _g) = crate::bridge::tests::scratch();
        // nothing to write: no document appears
        update("u.json", |_: &mut Vec<u32>| ()).unwrap();
        assert!(backend().get("u.json").unwrap().is_none());
        // a writer that slips in between the read and the write: the closure runs again on its value
        let mut runs = 0;
        update("u.json", |v: &mut Vec<u32>| {
            runs += 1;
            if runs == 1 {
                save("u.json", &vec![9u32]).unwrap();
            }
            v.push(1);
        })
        .unwrap();
        assert_eq!(runs, 2);
        assert_eq!(load::<Vec<u32>>("u.json"), vec![9, 1]);
    }
}
