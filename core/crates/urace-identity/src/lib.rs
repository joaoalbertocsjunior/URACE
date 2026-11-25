//! `urace-identity` — Identity and key management cluster for URACE.
//!
//! Modules:
//! - [`key_lifecycle`] — Key rotation, revocation, encrypted export/import.
//! - [`mesh_identity`] — Cryptographically-random node identity; stable persistence.
//! - [`session_dek`] — Session DEK: random generation and HKDF-SHA256 derivation.
//! - [`shamir_delivery`] — Share delivery tracking (in-memory + append-only Journal).
//! - [`crypto_wallet`] — Ed25519 wallet: sign, verify, secure Debug.

pub mod crypto_wallet;
pub mod key_lifecycle;
pub mod mesh_identity;
pub mod session_dek;
pub mod shamir_delivery;

// Convenience re-exports.
pub use crypto_wallet::{Wallet, WalletError};
pub use key_lifecycle::{KeyError, KeyRecord, KeyState, KeyStore};
pub use mesh_identity::{
    generate_node_identity, load_node_identity, persist_node_identity, IdentityError, NodeIdentity,
};
pub use session_dek::{DekError, SessionDek};
pub use shamir_delivery::{DeliveryError, DeliveryTracker, ShareDelivery};
