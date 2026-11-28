//! Lightning Network settlement rail — R-11 addition from mesh-llm pattern.
//!
//! Two types live here:
//! - `LightningRail` — always compiled, stub returns structured results.
//! - `LightningSettlementAdapter` — feature-gated (`lightning`), wires ldk-node.
//!
//! ldk-node crate (MIT) is listed in Cargo.toml as optional.
//! Full wiring deferred to when feature = "lightning" is activated in production.
//! Stub returns structured results without panicking.
//!
//! TODO(lightning): When `--features lightning` is activated:
//!   1. Create ldk_node::Builder with node_alias and listening address.
//!   2. Connect to LSP for inbound liquidity.
//!   3. Wire pay_invoice to ldk_node::Node::bolt11_payment().send().
//!   4. Wire generate_invoice to ldk_node::Node::bolt11_payment().receive().

use crate::{SettlementError, SettlementRail, SettlementResult};

/// Lightning Network settlement rail.
///
/// Full ldk-node wiring is deferred — this stub returns structured results.
pub struct LightningRail {
    pub node_alias: String,
}

impl LightningRail {
    pub fn new(node_alias: impl Into<String>) -> Self {
        LightningRail {
            node_alias: node_alias.into(),
        }
    }

    /// Pay a BOLT-11 invoice.
    ///
    /// Stub — returns `status = "lightning_stub"` until ldk-node is wired.
    pub fn pay_invoice(&self, bolt11: &str, amount_msat: u64) -> SettlementResult {
        tracing::info!(
            node_alias = %self.node_alias,
            bolt11 = %&bolt11[..bolt11.len().min(32)],
            amount_msat,
            "LightningRail::pay_invoice (stub)"
        );
        SettlementResult {
            status: "lightning_stub".into(),
            tx_hash: None,
            error: Some("ldk-node not wired; activate feature = lightning".into()),
            rail: SettlementRail::Lightning,
        }
    }

    /// TODO(settlement-lightning): Wire ldk-node for live Lightning payments.
    ///
    /// Steps:
    ///   1. Enable the `lightning` feature flag in Cargo.toml
    ///   2. Initialize `ldk_node::Builder` with the peer's seed from urace-identity
    ///   3. Connect to configured LSP (Lightning Service Provider)
    ///   4. Call `node.bolt11_payment().send(invoice)` for outbound
    ///   5. For inbound: `node.bolt11_payment().receive(amount_msat, description, expiry_secs)`
    ///
    /// Config needed: `network.lsp_address`, `network.lightning_port`.
    /// Feature flag: `--features lightning` activates ldk-node dep.
    pub fn pay_live(&self, _invoice: &str) -> Result<serde_json::Value, SettlementError> {
        Err(SettlementError::NotConfigured(
            "live Lightning payment not yet implemented; activate feature = lightning".into(),
        ))
    }

    /// Generate a BOLT-11 invoice for receiving `amount_msat` millisatoshis.
    ///
    /// Stub — returns `Err(NotConfigured)` until ldk-node is wired.
    pub fn generate_invoice(
        &self,
        amount_msat: u64,
        description: &str,
    ) -> Result<String, SettlementError> {
        tracing::info!(
            node_alias = %self.node_alias,
            amount_msat,
            description,
            "LightningRail::generate_invoice (stub)"
        );
        Err(SettlementError::NotConfigured(
            "ldk-node not configured; activate feature = lightning to enable Lightning Network rail".into(),
        ))
    }
}

// ── LightningSettlementAdapter (feature = "lightning") ───────────────────────

/// Full Lightning Network settlement adapter backed by ldk-node.
///
/// Activate with: `cargo build --features lightning -p urace-settlement`
#[cfg(feature = "lightning")]
pub struct LightningSettlementAdapter {
    pub node_dir: String,
    pub network: ldk_node::bitcoin::Network,
    node: ldk_node::Node,
}

#[cfg(feature = "lightning")]
impl LightningSettlementAdapter {
    /// Create and start an ldk-node instance at `node_dir` using Regtest by default.
    ///
    /// The node is started immediately; call `node.stop()` on drop if needed.
    pub fn new(node_dir: &str) -> Result<Self, SettlementError> {
        Self::new_with_network(node_dir, ldk_node::bitcoin::Network::Regtest)
    }

    /// Create and start a node for an explicit network.
    pub fn new_with_network(
        node_dir: &str,
        network: ldk_node::bitcoin::Network,
    ) -> Result<Self, SettlementError> {
        let mut builder = ldk_node::Builder::new();
        builder.set_storage_dir_path(node_dir.to_owned());
        builder.set_network(network);

        let node = builder
            .build()
            .map_err(|e| SettlementError::NotConfigured(format!("ldk-node build failed: {e}")))?;

        node.start()
            .map_err(|e| SettlementError::NotConfigured(format!("ldk-node start failed: {e}")))?;

        Ok(LightningSettlementAdapter {
            node_dir: node_dir.to_owned(),
            network,
            node,
        })
    }

    /// Generate a BOLT11 invoice for `amount_sats`.
    ///
    /// Returns the BOLT11 string on success.
    pub fn create_invoice(
        &self,
        amount_sats: u64,
        description: &str,
    ) -> Result<String, SettlementError> {
        let amount_msat = amount_sats
            .checked_mul(1000)
            .ok_or_else(|| SettlementError::Rpc("amount overflow".into()))?;

        let invoice = self
            .node
            .bolt11_payment()
            .receive(
                amount_msat,
                description,
                3600, // expiry 1 hour
            )
            .map_err(|e| SettlementError::Rpc(format!("create_invoice failed: {e}")))?;

        Ok(invoice.to_string())
    }

    /// Pay a BOLT11 invoice.
    ///
    /// Returns the hex-encoded PaymentId on success (use `check_payment` to poll for completion).
    pub fn pay_invoice(&self, invoice: &str) -> Result<String, SettlementError> {
        use std::str::FromStr;
        let bolt11 = ldk_node::lightning_invoice::Bolt11Invoice::from_str(invoice)
            .map_err(|e| SettlementError::Rpc(format!("invalid invoice: {e}")))?;

        let payment_id = self
            .node
            .bolt11_payment()
            .send(&bolt11, None)
            .map_err(|e| SettlementError::Rpc(format!("pay_invoice failed: {e}")))?;

        Ok(hex::encode(payment_id.0))
    }

    /// Check whether a payment identified by its hex-encoded `PaymentId` (from `pay_invoice`)
    /// has succeeded.
    pub fn check_payment(&self, payment_id_hex: &str) -> bool {
        let id_bytes = match hex::decode(payment_id_hex) {
            Ok(b) if b.len() == 32 => b,
            _ => return false,
        };
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&id_bytes);
        let payment_id = ldk_node::lightning::ln::channelmanager::PaymentId(arr);
        self.node
            .payment(&payment_id)
            .map(|p| {
                matches!(
                    p.status,
                    ldk_node::payment::PaymentStatus::Succeeded
                )
            })
            .unwrap_or(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pay_invoice_stub() {
        let rail = LightningRail::new("test-node");
        let result = rail.pay_invoice("lnbc1...", 1_000_000);
        assert_eq!(result.status, "lightning_stub");
        assert!(result.error.is_some());
        assert_eq!(result.rail, SettlementRail::Lightning);
    }

    #[test]
    fn test_generate_invoice_stub_errors() {
        let rail = LightningRail::new("test-node");
        let result = rail.generate_invoice(5_000_000, "test payment");
        assert!(matches!(result, Err(SettlementError::NotConfigured(_))));
    }
}
