//! EVM keypair — secp256k1 (k256) signing for Ethereum-compatible addresses.
//!
//! # Security invariants
//! - Private key bytes are never logged or included in `Debug` output.
//! - `to_bytes()` is an intentional export — callers must treat the return value as secret.
//! - No hardcoded private keys anywhere in this module.

use k256::ecdsa::{RecoveryId, SigningKey, VerifyingKey};
use k256::elliptic_curve::rand_core::OsRng;
use sha3::{Digest, Keccak256};
use thiserror::Error;

// ── Error ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum EvmKeypairError {
    #[error("invalid private key bytes: {0}")]
    InvalidKey(String),
    #[error("signing error: {0}")]
    SigningError(String),
    #[error("invalid address format: {0}")]
    InvalidAddress(String),
}

// ── EvmKeypair ────────────────────────────────────────────────────────────────

/// secp256k1 keypair for Ethereum-compatible signing.
///
/// # Debug
/// The `Debug` implementation does **not** print private key material.
pub struct EvmKeypair {
    signing_key: SigningKey,
}

impl std::fmt::Debug for EvmKeypair {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "EvmKeypair {{ address: {:?} }}", self.address())
    }
}

impl EvmKeypair {
    /// Generate a fresh keypair using the OS CSPRNG.
    pub fn generate() -> Self {
        let signing_key = SigningKey::random(&mut OsRng);
        EvmKeypair { signing_key }
    }

    /// Reconstruct a keypair from raw 32-byte secp256k1 scalar bytes.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, EvmKeypairError> {
        let signing_key = SigningKey::from_bytes(bytes.into())
            .map_err(|e| EvmKeypairError::InvalidKey(e.to_string()))?;
        Ok(EvmKeypair { signing_key })
    }

    /// Export the raw 32-byte private scalar. **Handle as secret.**
    pub fn to_bytes(&self) -> Vec<u8> {
        self.signing_key.to_bytes().to_vec()
    }

    /// Return the Ethereum address: `"0x" + hex(last_20_bytes(keccak256(uncompressed_pubkey[1..])))`.
    pub fn address(&self) -> String {
        let verifying_key: &VerifyingKey = self.signing_key.verifying_key();
        // Uncompressed point: 0x04 ++ x(32) ++ y(32) = 65 bytes.
        let uncompressed = verifying_key
            .to_encoded_point(false)
            .as_bytes()
            .to_owned();
        // Skip the 0x04 prefix; hash the remaining 64 bytes.
        let mut hasher = Keccak256::new();
        hasher.update(&uncompressed[1..]);
        let hash = hasher.finalize();
        // Last 20 bytes.
        let addr_bytes = &hash[12..32];
        format!("0x{}", hex::encode(addr_bytes))
    }

    /// Sign a 32-byte hash and return a 65-byte signature: `r(32) ++ s(32) ++ v(1)`.
    ///
    /// `v` is the recovery id (0 or 1), **not** EIP-155 adjusted.
    /// For EIP-155 chains use `v + 2 * chain_id + 35`.
    pub fn sign_hash(&self, hash: &[u8; 32]) -> [u8; 65] {
        use k256::ecdsa::signature::hazmat::PrehashSigner;
        let (sig, recid): (k256::ecdsa::Signature, RecoveryId) = self
            .signing_key
            .sign_prehash(hash)
            .expect("sign_prehash on secp256k1 is infallible for valid keys");
        let sig_bytes = sig.to_bytes();
        let mut out = [0u8; 65];
        out[..32].copy_from_slice(&sig_bytes[..32]); // r
        out[32..64].copy_from_slice(&sig_bytes[32..]); // s
        out[64] = recid.to_byte(); // v
        out
    }

    /// Build ERC-20 `transfer(address,uint256)` ABI calldata.
    ///
    /// Returns the hex-encoded calldata **without** the `0x` prefix.
    ///
    /// Layout:
    /// ```text
    /// 4 bytes  selector  = keccak256("transfer(address,uint256)")[0..4] = a9059cbb
    /// 32 bytes to_padded = 0x000...000 ++ addr_bytes(20)
    /// 32 bytes amount    = big-endian uint256
    /// ```
    pub fn encode_erc20_transfer(to: &str, amount: u128) -> Result<String, EvmKeypairError> {
        // Validate address.
        let to = to.trim();
        if !to.starts_with("0x") || to.len() != 42 {
            return Err(EvmKeypairError::InvalidAddress(format!(
                "expected 0x + 40 hex chars, got: {to}"
            )));
        }
        let addr_bytes = hex::decode(&to[2..])
            .map_err(|_| EvmKeypairError::InvalidAddress(format!("non-hex address: {to}")))?;

        // Selector: first 4 bytes of keccak256("transfer(address,uint256)").
        // This is a constant: 0xa9059cbb — computed here for auditability.
        let selector = {
            let mut h = Keccak256::new();
            h.update(b"transfer(address,uint256)");
            let hash = h.finalize();
            [hash[0], hash[1], hash[2], hash[3]]
        };
        debug_assert_eq!(selector, [0xa9, 0x05, 0x9c, 0xbb]);

        let mut calldata = Vec::with_capacity(4 + 32 + 32);
        calldata.extend_from_slice(&selector);

        // address: left-padded to 32 bytes.
        calldata.extend_from_slice(&[0u8; 12]);
        calldata.extend_from_slice(&addr_bytes);

        // amount: big-endian uint256 (we use u128, so upper 16 bytes are zero).
        calldata.extend_from_slice(&[0u8; 16]);
        calldata.extend_from_slice(&amount.to_be_bytes());

        Ok(hex::encode(calldata))
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generate_and_address() {
        let kp = EvmKeypair::generate();
        let addr = kp.address();
        assert!(addr.starts_with("0x"), "address must start with 0x");
        assert_eq!(addr.len(), 42, "address must be 42 chars (0x + 40 hex)");
    }

    #[test]
    fn from_bytes_roundtrip() {
        let kp = EvmKeypair::generate();
        let raw = kp.to_bytes();
        let kp2 = EvmKeypair::from_bytes(&raw).unwrap();
        assert_eq!(kp.address(), kp2.address());
    }

    #[test]
    fn sign_hash_produces_65_bytes() {
        let kp = EvmKeypair::generate();
        let hash = [0xab_u8; 32];
        let sig = kp.sign_hash(&hash);
        assert_eq!(sig.len(), 65);
        // v is 0 or 1
        assert!(sig[64] <= 1, "recovery id must be 0 or 1");
    }

    #[test]
    fn encode_erc20_transfer_valid() {
        let calldata = EvmKeypair::encode_erc20_transfer(
            "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            1_000_000_u128,
        )
        .unwrap();
        // 4 + 32 + 32 = 68 bytes = 136 hex chars
        assert_eq!(calldata.len(), 136);
        // Selector a9059cbb
        assert!(calldata.starts_with("a9059cbb"));
    }

    #[test]
    fn encode_erc20_transfer_bad_address() {
        let result = EvmKeypair::encode_erc20_transfer("not-an-address", 1);
        assert!(matches!(result, Err(EvmKeypairError::InvalidAddress(_))));
    }

    #[test]
    fn debug_does_not_leak_private_key() {
        let kp = EvmKeypair::generate();
        let dbg = format!("{kp:?}");
        // Must not contain the raw key hex.
        let key_hex = hex::encode(kp.to_bytes());
        assert!(!dbg.contains(&key_hex));
        assert!(dbg.contains("EvmKeypair"));
    }

    #[test]
    fn two_keypairs_have_different_addresses() {
        let kp1 = EvmKeypair::generate();
        let kp2 = EvmKeypair::generate();
        assert_ne!(kp1.address(), kp2.address());
    }
}
