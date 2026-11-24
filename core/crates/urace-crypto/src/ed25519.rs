//! Ed25519 key management for node identity and fleet policy signing.
//!
//! Used in R-5 fleet policy (owner-signed policies with monotonic generation)
//! and wherever URACE requires asymmetric signatures (identity, federation).

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand_core::{CryptoRng, RngCore};
use thiserror::Error;
use zeroize::Zeroizing;

pub use ed25519_dalek::PUBLIC_KEY_LENGTH;
pub use ed25519_dalek::SIGNATURE_LENGTH;

#[derive(Debug, Error)]
pub enum Ed25519Error {
    #[error("invalid public key bytes")]
    InvalidPublicKey,
    #[error("invalid signature bytes")]
    InvalidSignature,
    #[error("signature verification failed")]
    VerificationFailed,
}

/// An Ed25519 signing keypair. `SigningKey` zeroizes its own memory on drop (v2.x).
pub struct Keypair {
    // SigningKey in ed25519-dalek v2 implements Drop+Zeroize internally.
    signing: SigningKey,
    pub verifying: VerifyingKey,
}

impl Keypair {
    /// Generate a new random keypair.
    pub fn generate<R: RngCore + CryptoRng>(rng: &mut R) -> Self {
        let signing = SigningKey::generate(rng);
        let verifying = signing.verifying_key();
        Keypair { signing, verifying }
    }

    /// Restore from raw 32-byte private key seed.
    pub fn from_seed(seed: &[u8; 32]) -> Self {
        let signing = SigningKey::from_bytes(seed);
        let verifying = signing.verifying_key();
        Keypair { signing, verifying }
    }

    /// Export 32-byte private key seed — caller must zeroize after use.
    pub fn to_seed(&self) -> Zeroizing<[u8; 32]> {
        Zeroizing::new(self.signing.to_bytes())
    }

    pub fn public_key_bytes(&self) -> [u8; PUBLIC_KEY_LENGTH] {
        self.verifying.to_bytes()
    }

    pub fn sign(&self, msg: &[u8]) -> [u8; SIGNATURE_LENGTH] {
        self.signing.sign(msg).to_bytes()
    }
}

/// Verify an Ed25519 signature given the raw public key bytes.
pub fn verify(
    public_key: &[u8; PUBLIC_KEY_LENGTH],
    msg: &[u8],
    signature: &[u8; SIGNATURE_LENGTH],
) -> Result<(), Ed25519Error> {
    let vk = VerifyingKey::from_bytes(public_key)
        .map_err(|_| Ed25519Error::InvalidPublicKey)?;
    let sig = Signature::from_bytes(signature);
    vk.verify(msg, &sig).map_err(|_| Ed25519Error::VerificationFailed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn rng() -> StdRng { StdRng::seed_from_u64(0) }

    #[test]
    fn sign_verify_roundtrip() {
        let kp = Keypair::generate(&mut rng());
        let msg = b"fleet-policy-payload";
        let sig = kp.sign(msg);
        assert!(verify(&kp.public_key_bytes(), msg, &sig).is_ok());
    }

    #[test]
    fn tampered_message_rejected() {
        let kp = Keypair::generate(&mut rng());
        let sig = kp.sign(b"original");
        assert!(matches!(
            verify(&kp.public_key_bytes(), b"tampered", &sig),
            Err(Ed25519Error::VerificationFailed)
        ));
    }

    #[test]
    fn from_seed_round_trip() {
        let kp = Keypair::generate(&mut rng());
        let seed = kp.to_seed();
        let kp2 = Keypair::from_seed(&seed);
        assert_eq!(kp.public_key_bytes(), kp2.public_key_bytes());
    }
}
