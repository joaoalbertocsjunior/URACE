//! Lightning Network settlement rail — R-11 addition from mesh-llm pattern.
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
        LightningRail { node_alias: node_alias.into() }
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
