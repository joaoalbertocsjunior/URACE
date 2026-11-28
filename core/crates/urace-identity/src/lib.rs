//! `urace-identity` — Identity and key management cluster for URACE.
//!
//! Modules:
//! - [`key_lifecycle`] — Key rotation, revocation, encrypted export/import.
//! - [`mesh_identity`] — Cryptographically-random node identity; stable persistence.
//! - [`session_dek`] — Session DEK: random generation and HKDF-SHA256 derivation.
//! - [`shamir_delivery`] — Share delivery tracking (in-memory + append-only Journal).
//! - [`crypto_wallet`] — Ed25519 wallet: sign, verify, secure Debug.
//! - [`multisig`] — M68: threshold-of-N multi-party signing coordinator.
//! - [`key_ceremony`] — M61: verifiable key-ceremony records with integrity hashing.

pub mod crypto_wallet;
pub mod evm_keypair;
pub mod hsm;
pub mod identity_continuity;
pub mod key_ceremony;
pub mod key_lifecycle;
pub mod mesh_identity;
pub mod multisig;
pub mod session_dek;
pub mod shamir_delivery;
pub mod tpm;

// Convenience re-exports.
pub use crypto_wallet::{Wallet, WalletError};
pub use key_lifecycle::{KeyError, KeyRecord, KeyState, KeyStore};
pub use mesh_identity::{
    generate_node_identity, load_node_identity, persist_node_identity, IdentityError, NodeIdentity,
};
pub use session_dek::{DekError, SessionDek};
pub use shamir_delivery::{DeliveryError, DeliveryTracker, ShareDelivery};
pub use key_ceremony::CeremonyRecord;
pub use multisig::{MultisigCoordinator, MultisigError, MultisigOperation};
pub use hsm::{HsmBackend, HsmError, HsmKeyHandle, SoftwareHsm};
pub use identity_continuity::{
    build_migration_claim, canonical_payload, verify_migration, ContinuityError, MigrationClaim,
    MIGRATION_CLAIM_MAX_AGE_SECS,
};
pub use tpm::{AttestationReport, SoftwareTpm, TpmBackend, TpmError};
pub use evm_keypair::{EvmKeypair, EvmKeypairError};
