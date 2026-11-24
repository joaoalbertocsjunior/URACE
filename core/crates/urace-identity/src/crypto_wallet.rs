//! Wallet key management — Ed25519 signing for peer-associated wallet identity.
//!
//! Invariants (from CLAUDE.md / runtime/urace/CLAUDE.md):
//! - Private key material MUST NEVER appear in logs, exceptions, or return values
//!   other than designated export calls.
//! - `Debug` impl for `Wallet` must NOT print the private key.
//! - Constant-time comparison for all signature/key checks — delegated to
//!   `urace_crypto::ed25519_verify` which uses ed25519-dalek's constant-time verify.

use rand_core::{CryptoRng, RngCore};
use thiserror::Error;
use urace_crypto::{ed25519_verify, Keypair};

#[derive(Debug, Error)]
pub enum WalletError {
    #[error("signature verification failed")]
    VerificationFailed,
    #[error("invalid public key bytes")]
    InvalidPublicKey,
}

/// An Ed25519 wallet tied to a `peer_id`.
///
/// # Security
/// The `Debug` implementation is manually written to omit the private key.
/// Private key material is accessible only via `urace_crypto::Keypair::to_seed`
/// and must be treated as secret.
pub struct Wallet {
    keypair: Keypair,
    pub peer_id: String,
    pub wallet_id: String,
}

impl std::fmt::Debug for Wallet {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Deliberately omit keypair / private key material.
        write!(
            f,
            "Wallet {{ wallet_id: {:?}, peer_id: {:?} }}",
            self.wallet_id, self.peer_id
        )
    }
}

fn random_id<R: RngCore + CryptoRng>(rng: &mut R) -> String {
    let mut b = [0u8; 16];
    rng.fill_bytes(&mut b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    format!(
        "{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        u32::from_be_bytes([b[0], b[1], b[2], b[3]]),
        u16::from_be_bytes([b[4], b[5]]),
        u16::from_be_bytes([b[6], b[7]]),
        u16::from_be_bytes([b[8], b[9]]),
        {
            let hi = u16::from_be_bytes([b[10], b[11]]) as u64;
            let lo = u32::from_be_bytes([b[12], b[13], b[14], b[15]]) as u64;
            (hi << 32) | lo
        }
    )
}

impl Wallet {
    /// Create a new wallet for `peer_id`.
    pub fn new<R: RngCore + CryptoRng>(peer_id: &str, rng: &mut R) -> Self {
        let keypair = Keypair::generate(rng);
        let wallet_id = random_id(rng);
        Wallet {
            keypair,
            peer_id: peer_id.to_string(),
            wallet_id,
        }
    }

    /// Return the hex-encoded Ed25519 public key.
    pub fn public_key_hex(&self) -> String {
        hex::encode(self.keypair.public_key_bytes())
    }

    /// Return the raw 32-byte Ed25519 public key.
    pub fn public_key_bytes(&self) -> [u8; 32] {
        self.keypair.public_key_bytes()
    }

    /// Sign `msg` with the wallet's Ed25519 private key.  Returns the 64-byte signature.
    ///
    /// Private key material never leaves this call.
    pub fn sign_message(&self, msg: &[u8]) -> [u8; 64] {
        self.keypair.sign(msg)
    }

    /// Verify that `sig` is a valid Ed25519 signature over `msg` by this wallet's public key.
    ///
    /// Uses constant-time comparison via `ed25519-dalek`'s internal verify.
    pub fn verify_message(&self, msg: &[u8], sig: &[u8; 64]) -> bool {
        let pub_bytes = self.keypair.public_key_bytes();
        ed25519_verify(&pub_bytes, msg, sig).is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn rng() -> StdRng {
        StdRng::seed_from_u64(99)
    }

    #[test]
    fn sign_verify_roundtrip() {
        let wallet = Wallet::new("peer-abc", &mut rng());
        let msg = b"urace-wallet-test-message";
        let sig = wallet.sign_message(msg);
        assert!(wallet.verify_message(msg, &sig));
    }

    #[test]
    fn tampered_message_rejected() {
        let wallet = Wallet::new("peer-xyz", &mut rng());
        let sig = wallet.sign_message(b"original");
        assert!(!wallet.verify_message(b"tampered", &sig));
    }

    #[test]
    fn tampered_signature_rejected() {
        let wallet = Wallet::new("peer-xyz", &mut rng());
        let mut sig = wallet.sign_message(b"msg");
        sig[0] ^= 0xFF;
        assert!(!wallet.verify_message(b"msg", &sig));
    }

    #[test]
    fn debug_does_not_leak_private_key() {
        let wallet = Wallet::new("peer-debug", &mut rng());
        let dbg = format!("{wallet:?}");
        // Debug must contain wallet_id and peer_id.
        assert!(dbg.contains("wallet_id"));
        assert!(dbg.contains("peer_id"));
        // Must NOT contain "keypair", "signing", or the private key hex.
        assert!(!dbg.contains("keypair"), "Debug must not expose keypair field");
        assert!(!dbg.contains("signing"), "Debug must not expose signing key");
        // Verify the hex of the seed is not present.
        let seed = wallet.keypair.to_seed();
        let seed_hex = hex::encode(seed.as_ref());
        assert!(!dbg.contains(&seed_hex), "Debug must not contain seed hex");
    }

    #[test]
    fn two_wallets_have_different_keys() {
        let w1 = Wallet::new("peer-1", &mut StdRng::seed_from_u64(1));
        let w2 = Wallet::new("peer-2", &mut StdRng::seed_from_u64(2));
        assert_ne!(w1.public_key_hex(), w2.public_key_hex());
        assert_ne!(w1.wallet_id, w2.wallet_id);
    }

    #[test]
    fn cross_wallet_signature_rejected() {
        let w1 = Wallet::new("peer-1", &mut StdRng::seed_from_u64(10));
        let w2 = Wallet::new("peer-2", &mut StdRng::seed_from_u64(20));
        let msg = b"cross-wallet-test";
        let sig_from_w1 = w1.sign_message(msg);
        // w2 must not accept a signature made by w1.
        assert!(!w2.verify_message(msg, &sig_from_w1));
    }

    #[test]
    fn public_key_hex_is_64_chars() {
        let wallet = Wallet::new("peer-pk", &mut rng());
        assert_eq!(wallet.public_key_hex().len(), 64);
    }
}
