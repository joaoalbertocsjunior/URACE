//! Bounded compressed hybrid-signed local blocks with flock serialization.
//!
//! Ported from `signed_ledger.py`. Blocks are immutable; the head is a cache.
//! Recovery adopts a fully verified next block after an interrupted head update.
//! An independently retained checkpoint is required to detect whole-history rollback.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha384};
use std::io::Write;
use std::path::{Path, PathBuf};
use thiserror::Error;
use urace_crypto::ed25519::Keypair;

pub const LEDGER_SCHEMA_VERSION: &str = "urace-signed-block-v1";
const KNOWN_SCHEMA_VERSIONS: &[&str] = &[LEDGER_SCHEMA_VERSION];

/// Maximum uncompressed block size (matches Python's `ledger_crypto.MAX_BYTES`).
const MAX_BYTES: usize = 1 << 20; // 1 MiB

const ZERO_HASH: &str =
    "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum SignedLedgerError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("symlink in ledger path is prohibited")]
    SymlinkProhibited,
    #[error("block integrity violation: {0}")]
    IntegrityViolation(String),
    #[error("block size bound exceeded")]
    SizeBound,
    #[error("unknown block encoding")]
    UnknownEncoding,
    #[error("crypto error: {0}")]
    Crypto(String),
}

// ── Block encoding (pack / unpack) ────────────────────────────────────────────

/// Pack `data`: compress with zlib if it saves ≥10 %; otherwise store raw.
/// Prefix: `Z` = compressed, `J` = raw JSON.
pub fn pack(data: &[u8]) -> Result<Vec<u8>, SignedLedgerError> {
    if data.len() > MAX_BYTES {
        return Err(SignedLedgerError::SizeBound);
    }
    use std::io::Write as _;
    let mut encoder = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::new(6));
    encoder.write_all(data).map_err(SignedLedgerError::Io)?;
    let compressed = encoder.finish().map_err(SignedLedgerError::Io)?;
    if compressed.len() + 1 < (data.len() as f64 * 0.9) as usize {
        let mut out = Vec::with_capacity(1 + compressed.len());
        out.push(b'Z');
        out.extend_from_slice(&compressed);
        Ok(out)
    } else {
        let mut out = Vec::with_capacity(1 + data.len());
        out.push(b'J');
        out.extend_from_slice(data);
        Ok(out)
    }
}

/// Unpack a block previously packed with `pack`.
pub fn unpack(data: &[u8]) -> Result<Vec<u8>, SignedLedgerError> {
    if data.is_empty() || data.len() > MAX_BYTES + 1 {
        return Err(SignedLedgerError::SizeBound);
    }
    match data[0] {
        b'J' => {
            let raw = &data[1..];
            if raw.len() > MAX_BYTES {
                return Err(SignedLedgerError::SizeBound);
            }
            Ok(raw.to_vec())
        }
        b'Z' => {
            use std::io::Read as _;
            let mut decoder = flate2::read::ZlibDecoder::new(&data[1..]);
            let mut out = Vec::new();
            decoder
                .read_to_end(&mut out)
                .map_err(SignedLedgerError::Io)?;
            if out.len() > MAX_BYTES {
                return Err(SignedLedgerError::SizeBound);
            }
            Ok(out)
        }
        _ => Err(SignedLedgerError::UnknownEncoding),
    }
}

// ── Canonical JSON ────────────────────────────────────────────────────────────

/// Canonical (sorted-keys, compact) JSON bytes for a JSON value.
fn canonical(value: &Value) -> Vec<u8> {
    // serde_json::to_vec produces compact JSON but does NOT sort keys.
    // We sort by converting to a BTreeMap representation.
    canonical_sorted(value)
}

fn canonical_sorted(v: &Value) -> Vec<u8> {
    match v {
        Value::Object(map) => {
            let sorted: std::collections::BTreeMap<_, _> = map.iter().collect();
            let mut out = vec![b'{'];
            for (i, (k, val)) in sorted.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                out.extend_from_slice(&serde_json::to_vec(k).unwrap_or_default());
                out.push(b':');
                out.extend_from_slice(&canonical_sorted(val));
            }
            out.push(b'}');
            out
        }
        Value::Array(arr) => {
            let mut out = vec![b'['];
            for (i, item) in arr.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                out.extend_from_slice(&canonical_sorted(item));
            }
            out.push(b']');
            out
        }
        other => serde_json::to_vec(other).unwrap_or_default(),
    }
}

fn sha384_hex(data: &[u8]) -> String {
    hex::encode(Sha384::digest(data))
}

// ── Block types ───────────────────────────────────────────────────────────────

/// Payload section of a signed block.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockPayload {
    pub schema: String,
    pub author: String,
    pub sequence: u64,
    pub previous: String,
    pub at_unix: f64,
    pub kind: String,
    pub details: Value,
}

/// A fully signed immutable block (payload + Ed25519 signature).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedBlock {
    pub payload: BlockPayload,
    pub signature: String,
}

/// Head cache record (persisted to `head.json`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeadRecord {
    pub sequence: u64,
    pub hash: String,
    pub author: String,
}

/// Result returned from `Ledger::append`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppendResult {
    pub sequence: u64,
    pub hash: String,
    pub author: String,
    pub stored_bytes: usize,
    pub logical_bytes: usize,
}

/// Verification report from `Ledger::verify`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyReport {
    pub status: String,
    pub blocks: u64,
    pub stored_bytes: u64,
    pub logical_bytes: u64,
    pub global_consensus: bool,
    pub external_checkpoint_checked: bool,
}

// ── Identity helpers ──────────────────────────────────────────────────────────

/// A persistent Ed25519 identity backed by a JSON key file.
pub struct LedgerIdentity {
    keypair: Keypair,
    public_id: String,
}

impl LedgerIdentity {
    /// Load from `path` or generate and save if absent.
    pub fn load_or_generate(path: &Path) -> Result<Self, SignedLedgerError> {
        if path.is_symlink() {
            return Err(SignedLedgerError::SymlinkProhibited);
        }
        if path.exists() {
            let raw = std::fs::read_to_string(path)?;
            let v: Value = serde_json::from_str(&raw)?;
            let seed_hex = v
                .get("seed_hex")
                .and_then(Value::as_str)
                .ok_or_else(|| SignedLedgerError::IntegrityViolation("missing seed_hex".into()))?;
            let seed_bytes = hex::decode(seed_hex)
                .map_err(|e| SignedLedgerError::IntegrityViolation(e.to_string()))?;
            if seed_bytes.len() != 32 {
                return Err(SignedLedgerError::IntegrityViolation(
                    "seed must be 32 bytes".into(),
                ));
            }
            let seed: [u8; 32] = seed_bytes.try_into().unwrap();
            let keypair = Keypair::from_seed(&seed);
            let public_id = hex::encode(keypair.public_key_bytes());
            Ok(Self { keypair, public_id })
        } else {
            let mut rng = rand::thread_rng();
            let keypair = Keypair::generate(&mut rng);
            let seed = keypair.to_seed();
            let public_id = hex::encode(keypair.public_key_bytes());
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let v = serde_json::json!({ "seed_hex": hex::encode(*seed) });
            let tmp = path.with_extension("tmp");
            {
                let mut f = std::fs::OpenOptions::new()
                    .write(true)
                    .create(true)
                    .truncate(true)
                    .open(&tmp)?;
                f.write_all(serde_json::to_string(&v)?.as_bytes())?;
                f.flush()?;
                f.sync_all()?;
            }
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(&tmp, std::fs::Permissions::from_mode(0o600))?;
            }
            std::fs::rename(&tmp, path)?;
            Ok(Self { keypair, public_id })
        }
    }

    pub fn public_id(&self) -> &str {
        &self.public_id
    }

    fn sign_payload(&self, payload: &BlockPayload) -> Result<String, SignedLedgerError> {
        let canonical_bytes = canonical(&serde_json::to_value(payload)?);
        let sig_bytes = self.keypair.sign(&canonical_bytes);
        Ok(hex::encode(sig_bytes))
    }

    fn verify_payload(
        &self,
        payload: &BlockPayload,
        signature_hex: &str,
    ) -> Result<(), SignedLedgerError> {
        let canonical_bytes = canonical(&serde_json::to_value(payload)?);
        let sig_bytes =
            hex::decode(signature_hex).map_err(|e| SignedLedgerError::Crypto(e.to_string()))?;
        if sig_bytes.len() != 64 {
            return Err(SignedLedgerError::Crypto("invalid signature length".into()));
        }
        let sig: [u8; 64] = sig_bytes.try_into().unwrap();
        let pub_key_bytes =
            hex::decode(&self.public_id).map_err(|e| SignedLedgerError::Crypto(e.to_string()))?;
        if pub_key_bytes.len() != 32 {
            return Err(SignedLedgerError::Crypto(
                "invalid public key length".into(),
            ));
        }
        let pub_key: [u8; 32] = pub_key_bytes.try_into().unwrap();
        urace_crypto::ed25519::verify(&pub_key, &canonical_bytes, &sig)
            .map_err(|e| SignedLedgerError::Crypto(e.to_string()))
    }
}

// ── Ledger ────────────────────────────────────────────────────────────────────

/// Bounded compressed hybrid-signed ledger.
///
/// All writers serialize with an exclusive file lock. Blocks are immutable.
pub struct Ledger {
    root: PathBuf,
}

impl Ledger {
    /// Open (or create) a ledger at `root`.
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self {
            root: root.as_ref().to_path_buf(),
        }
    }

    fn block_path(&self, n: u64) -> PathBuf {
        self.root.join(format!("{n:020}.block"))
    }

    fn head_path(&self) -> PathBuf {
        self.root.join("head.json")
    }

    fn identity_path(&self) -> PathBuf {
        self.root.join("identity.json")
    }

    fn lock_path(&self) -> PathBuf {
        self.root.join("writer.lock")
    }

    fn load_head(&self) -> Result<Option<HeadRecord>, SignedLedgerError> {
        let p = self.head_path();
        if !p.exists() {
            return Ok(None);
        }
        let raw = std::fs::read_to_string(&p)?;
        let h: HeadRecord = serde_json::from_str(&raw)?;
        Ok(Some(h))
    }

    fn save_head(&self, head: &HeadRecord) -> Result<(), SignedLedgerError> {
        let p = self.head_path();
        let tmp = p.with_extension("tmp");
        {
            let mut f = std::fs::OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .open(&tmp)?;
            f.write_all(serde_json::to_string(head)?.as_bytes())?;
            f.flush()?;
            f.sync_all()?;
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&tmp, std::fs::Permissions::from_mode(0o600));
        }
        std::fs::rename(&tmp, &p)?;
        Ok(())
    }

    /// Returns `(block, sha384_digest, raw_logical_bytes)`.
    fn read_block(
        &self,
        n: u64,
        previous_hash: &str,
        author: &str,
        identity: &LedgerIdentity,
    ) -> Result<(SignedBlock, String, Vec<u8>), SignedLedgerError> {
        let p = self.block_path(n);
        if p.is_symlink() {
            return Err(SignedLedgerError::SymlinkProhibited);
        }
        let stored = std::fs::read(&p)?;
        if stored.len() > MAX_BYTES + 1 {
            return Err(SignedLedgerError::SizeBound);
        }
        let raw = unpack(&stored)?;
        let block: SignedBlock = serde_json::from_slice(&raw)?;

        let bp = &block.payload;
        if !KNOWN_SCHEMA_VERSIONS.contains(&bp.schema.as_str()) {
            return Err(SignedLedgerError::IntegrityViolation(format!(
                "block {n}: unknown schema '{}'",
                bp.schema
            )));
        }
        if bp.sequence != n {
            return Err(SignedLedgerError::IntegrityViolation(format!(
                "block {n}: sequence mismatch (got {})",
                bp.sequence
            )));
        }
        if bp.previous != previous_hash {
            return Err(SignedLedgerError::IntegrityViolation(format!(
                "block {n}: previous hash mismatch"
            )));
        }
        if bp.author != author {
            return Err(SignedLedgerError::IntegrityViolation(format!(
                "block {n}: author mismatch"
            )));
        }

        identity.verify_payload(bp, &block.signature)?;

        let digest = sha384_hex(&raw);
        Ok((block, digest, raw))
    }

    fn previous_hash(&self, n: u64) -> Result<String, SignedLedgerError> {
        if n == 1 {
            return Ok(ZERO_HASH.to_owned());
        }
        let p = self.block_path(n - 1);
        if p.is_symlink() {
            return Err(SignedLedgerError::SymlinkProhibited);
        }
        let stored = std::fs::read(&p)?;
        if stored.len() > MAX_BYTES + 1 {
            return Err(SignedLedgerError::SizeBound);
        }
        let raw = unpack(&stored)?;
        Ok(sha384_hex(&raw))
    }

    fn recover(&self, identity: &LedgerIdentity) -> Result<HeadRecord, SignedLedgerError> {
        std::fs::create_dir_all(&self.root)?;

        let head = self.load_head()?.unwrap_or_else(|| HeadRecord {
            sequence: 0,
            hash: ZERO_HASH.to_owned(),
            author: identity.public_id().to_owned(),
        });

        if head.author != identity.public_id() {
            return Err(SignedLedgerError::IntegrityViolation(
                "ledger author changed".into(),
            ));
        }

        // Verify the current head block is consistent
        if head.sequence > 0 {
            let prev = self.previous_hash(head.sequence)?;
            let (_, digest, _) = self.read_block(head.sequence, &prev, &head.author, identity)?;
            if digest != head.hash {
                return Err(SignedLedgerError::IntegrityViolation(
                    "ledger head hash mismatch".into(),
                ));
            }
        }

        // Adopt any fully written but un-published next blocks
        let mut current = head;
        loop {
            let next_path = self.block_path(current.sequence + 1);
            if !next_path.exists() {
                break;
            }
            let prev_hash = if current.sequence == 0 {
                ZERO_HASH.to_owned()
            } else {
                current.hash.clone()
            };
            let (_, digest, _) =
                self.read_block(current.sequence + 1, &prev_hash, &current.author, identity)?;
            current = HeadRecord {
                sequence: current.sequence + 1,
                hash: digest,
                author: current.author.clone(),
            };
            self.save_head(&current)?;
        }

        Ok(current)
    }

    /// Append a typed event to the ledger. Returns `AppendResult`.
    pub fn append(&self, kind: &str, details: Value) -> Result<AppendResult, SignedLedgerError> {
        // Validate kind (matches Python regex: [A-Z][A-Z0-9_]{0,63})
        {
            let bytes = kind.as_bytes();
            if bytes.is_empty()
                || bytes.len() > 64
                || !bytes[0].is_ascii_uppercase()
                || !bytes[1..]
                    .iter()
                    .all(|&b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
            {
                return Err(SignedLedgerError::IntegrityViolation(format!(
                    "invalid event kind: {kind}"
                )));
            }
        }

        // Exclusive write lock via lock file
        std::fs::create_dir_all(&self.root)?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&self.root, std::fs::Permissions::from_mode(0o700));
        }

        let lock_file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(self.lock_path())?;

        #[cfg(unix)]
        {
            use std::os::unix::io::AsRawFd;
            let ret = unsafe { libc::flock(lock_file.as_raw_fd(), libc::LOCK_EX) };
            if ret != 0 {
                return Err(SignedLedgerError::Io(std::io::Error::last_os_error()));
            }
        }

        let identity = LedgerIdentity::load_or_generate(&self.identity_path())?;
        let head = self.recover(&identity)?;

        let previous_hash = if head.sequence == 0 {
            ZERO_HASH.to_owned()
        } else {
            head.hash.clone()
        };

        let at_unix = {
            use std::time::{SystemTime, UNIX_EPOCH};
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0)
        };

        let payload = BlockPayload {
            schema: LEDGER_SCHEMA_VERSION.to_owned(),
            author: head.author.clone(),
            sequence: head.sequence + 1,
            previous: previous_hash,
            at_unix,
            kind: kind.to_owned(),
            details,
        };

        let signature = identity.sign_payload(&payload)?;
        let block = SignedBlock { payload, signature };
        let raw = canonical(&serde_json::to_value(&block)?);
        let stored = pack(&raw)?;

        let target = self.block_path(block.payload.sequence);

        // Write via pending file — a killed writer leaves a pending file, never a
        // partly published block.
        let pending = {
            let pending_path = self
                .root
                .join(format!("pending-{}", block.payload.sequence));
            {
                let mut f = std::fs::OpenOptions::new()
                    .write(true)
                    .create(true)
                    .truncate(true)
                    .open(&pending_path)?;
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ = f.set_permissions(std::fs::Permissions::from_mode(0o600));
                }
                f.write_all(&stored)?;
                f.flush()?;
                f.sync_all()?;
            }
            pending_path
        };

        // Hard-link pending → target, then unlink pending
        std::fs::hard_link(&pending, &target)?;
        let _ = std::fs::remove_file(&pending);

        // fsync directory
        #[cfg(unix)]
        {
            use std::os::unix::io::IntoRawFd;
            let dir_fd = std::fs::File::open(&self.root)?.into_raw_fd();
            unsafe { libc::fsync(dir_fd) };
        }

        let digest = sha384_hex(&raw);
        let new_head = HeadRecord {
            sequence: block.payload.sequence,
            hash: digest.clone(),
            author: head.author,
        };
        self.save_head(&new_head)?;

        Ok(AppendResult {
            sequence: new_head.sequence,
            hash: digest,
            author: new_head.author,
            stored_bytes: stored.len(),
            logical_bytes: raw.len(),
        })
    }

    /// Verify the full chain. Returns a `VerifyReport`.
    pub fn verify(
        &self,
        checkpoint: Option<&HeadRecord>,
    ) -> Result<VerifyReport, SignedLedgerError> {
        if !self.root.exists() {
            return Ok(VerifyReport {
                status: "NOT_INITIALIZED".to_owned(),
                blocks: 0,
                stored_bytes: 0,
                logical_bytes: 0,
                global_consensus: false,
                external_checkpoint_checked: false,
            });
        }

        // Shared read lock
        let lock_file = std::fs::OpenOptions::new()
            .read(true)
            .open(self.lock_path())?;
        #[cfg(unix)]
        {
            use std::os::unix::io::AsRawFd;
            unsafe { libc::flock(lock_file.as_raw_fd(), libc::LOCK_SH) };
        }

        let head = self.load_head()?.unwrap_or(HeadRecord {
            sequence: 0,
            hash: ZERO_HASH.to_owned(),
            author: String::new(),
        });

        let identity = LedgerIdentity::load_or_generate(&self.identity_path())?;
        let mut previous = ZERO_HASH.to_owned();
        let mut stored_bytes = 0u64;
        let mut logical_bytes = 0u64;

        for n in 1..=head.sequence {
            let (_block, digest, raw) = self.read_block(n, &previous, &head.author, &identity)?;
            stored_bytes += self.block_path(n).metadata()?.len();
            logical_bytes += raw.len() as u64;

            if let Some(cp) = checkpoint {
                if n == cp.sequence && (digest != cp.hash || head.author != cp.author) {
                    return Err(SignedLedgerError::IntegrityViolation(
                        "external checkpoint conflict".into(),
                    ));
                }
            }
            previous = digest;
        }

        if previous != head.hash {
            return Err(SignedLedgerError::IntegrityViolation(
                "ledger terminal hash mismatch".into(),
            ));
        }

        if let Some(cp) = checkpoint {
            if cp.author != head.author || cp.sequence > head.sequence {
                return Err(SignedLedgerError::IntegrityViolation(
                    "checkpoint indicates missing history".into(),
                ));
            }
        }

        Ok(VerifyReport {
            status: "VERIFIED_LOCAL_CHAIN".to_owned(),
            blocks: head.sequence,
            stored_bytes,
            logical_bytes,
            global_consensus: false,
            external_checkpoint_checked: checkpoint.is_some(),
        })
    }

    /// Read a page of blocks (bounded pagination).
    pub fn page(&self, offset: usize, limit: usize) -> Result<Vec<SignedBlock>, SignedLedgerError> {
        if limit == 0 || limit > 100 {
            return Err(SignedLedgerError::IntegrityViolation(
                "limit must be 1..=100".into(),
            ));
        }

        let lock_file = std::fs::OpenOptions::new()
            .read(true)
            .open(self.lock_path())?;
        #[cfg(unix)]
        {
            use std::os::unix::io::AsRawFd;
            unsafe { libc::flock(lock_file.as_raw_fd(), libc::LOCK_SH) };
        }

        let head = self.load_head()?.unwrap_or(HeadRecord {
            sequence: 0,
            hash: ZERO_HASH.to_owned(),
            author: String::new(),
        });

        let identity = LedgerIdentity::load_or_generate(&self.identity_path())?;
        let mut blocks = Vec::new();

        for n in (offset as u64 + 1)..=(head.sequence.min((offset + limit) as u64)) {
            let prev = self.previous_hash(n)?;
            let (block, _, _) = self.read_block(n, &prev, &head.author, &identity)?;
            blocks.push(block);
        }

        Ok(blocks)
    }
}

// ── Schema helper (re-exported from schema_version.rs convention) ─────────────

/// Return `true` if this runtime can interpret the given ledger block schema version string.
pub fn can_read_schema(schema: &str) -> bool {
    KNOWN_SCHEMA_VERSIONS.contains(&schema)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    #[test]
    fn pack_unpack_roundtrip() {
        let data = b"hello world this is a test block payload";
        let packed = pack(data).unwrap();
        let unpacked = unpack(&packed).unwrap();
        assert_eq!(&unpacked, data);
    }

    #[test]
    fn pack_unpack_large_compressible() {
        // 100 KB of repeated bytes — should compress well
        let data = vec![b'A'; 100_000];
        let packed = pack(&data).unwrap();
        assert_eq!(packed[0], b'Z'); // should be compressed
        let unpacked = unpack(&packed).unwrap();
        assert_eq!(unpacked, data);
    }

    #[test]
    fn append_and_verify() {
        let dir = tempdir().unwrap();
        let ledger = Ledger::new(dir.path());

        ledger
            .append("CREDIT_DELTA", json!({"peer": "p1", "amount": 10}))
            .unwrap();
        ledger
            .append("CREDIT_DELTA", json!({"peer": "p2", "amount": 20}))
            .unwrap();

        let report = ledger.verify(None).unwrap();
        assert_eq!(report.blocks, 2);
        assert_eq!(report.status, "VERIFIED_LOCAL_CHAIN");
        assert!(!report.global_consensus);
    }

    #[test]
    fn invalid_kind_rejected() {
        let dir = tempdir().unwrap();
        let ledger = Ledger::new(dir.path());
        let res = ledger.append("invalid-kind", json!({}));
        assert!(matches!(res, Err(SignedLedgerError::IntegrityViolation(_))));
    }

    #[test]
    fn can_read_schema_known_version() {
        assert!(can_read_schema(LEDGER_SCHEMA_VERSION));
        assert!(!can_read_schema("urace-signed-block-v99"));
    }
}
