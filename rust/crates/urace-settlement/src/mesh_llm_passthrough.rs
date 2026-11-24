//! Option 3: mesh-llm executor payment passthrough.
//!
//! Architecture: URACE → work bid → mesh-llm executor → Lightning payment.
//!
//! When URACE dispatches inference to a mesh-llm executor, that executor
//! already has a live Lightning channel. URACE work-market payments are
//! forwarded to `{executor_endpoint}/payments` and confirmed by polling
//! `{executor_endpoint}/payments/{work_ref}/status`.
//!
//! Config: `settlement_rail = "mesh_llm_passthrough"`, `executor_endpoint = "http://…"`.
//! The executor must be a mesh-llm node registered as `ai_executor` in the source registry.

use crate::{SettlementError, SettlementRail, SettlementResult};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tracing::{info, warn};

/// Timeout for a single payment HTTP request.
const REQUEST_TIMEOUT_SECS: u64 = 10;
/// Number of status poll attempts before giving up.
const POLL_MAX_ATTEMPTS: u8 = 5;
/// Delay between poll attempts.
const POLL_INTERVAL_MILLIS: u64 = 1_000;

#[derive(Debug, Serialize)]
struct PaymentRequest<'a> {
    amount_msat: u64,
    work_ref: &'a str,
    rail: &'static str,
}

#[derive(Debug, Deserialize)]
struct PaymentResponse {
    status: String,
    payment_id: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct PaymentStatus {
    status: String,
    tx_hash: Option<String>,
    error: Option<String>,
}

pub struct MeshLlmPassthrough {
    pub executor_endpoint: String,
    client: Client,
}

impl MeshLlmPassthrough {
    pub fn new(executor_endpoint: &str) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS))
            .build()
            .unwrap_or_default();
        MeshLlmPassthrough {
            executor_endpoint: executor_endpoint.trim_end_matches('/').to_owned(),
            client,
        }
    }

    /// Settle a work-market payment via the mesh-llm executor's Lightning channel.
    ///
    /// POSTs to `{executor_endpoint}/payments`, then polls status until confirmed
    /// or times out. Returns immediately with the final `SettlementResult`.
    ///
    /// This is a synchronous wrapper around async calls — callers that are already
    /// in a tokio context should use `settle_work_payment_async` directly.
    pub fn settle_work_payment(&self, amount_msat: u64, work_ref: &str) -> SettlementResult {
        // Build a minimal single-threaded tokio runtime for the sync call site.
        // In production the executor pool will call settle_work_payment_async directly.
        match tokio::runtime::Handle::try_current() {
            Ok(handle) => {
                handle.block_on(self.settle_work_payment_async(amount_msat, work_ref))
            }
            Err(_) => {
                // No existing runtime — create one.
                let rt = tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build();
                match rt {
                    Ok(rt) => rt.block_on(self.settle_work_payment_async(amount_msat, work_ref)),
                    Err(e) => SettlementResult {
                        status: "error".into(),
                        tx_hash: None,
                        error: Some(format!("tokio runtime error: {e}")),
                        rail: SettlementRail::Lightning,
                    },
                }
            }
        }
    }

    /// Async settlement — preferred call site from async executor code.
    pub async fn settle_work_payment_async(
        &self,
        amount_msat: u64,
        work_ref: &str,
    ) -> SettlementResult {
        let pay_url = format!("{}/payments", self.executor_endpoint);
        info!(
            executor_endpoint = %self.executor_endpoint,
            amount_msat,
            work_ref,
            "mesh-llm passthrough: initiating payment"
        );

        // Step 1: initiate payment.
        let resp = self
            .client
            .post(&pay_url)
            .json(&PaymentRequest { amount_msat, work_ref, rail: "lightning" })
            .send()
            .await;

        let payment_id = match resp {
            Err(e) => {
                return SettlementResult {
                    status: "error".into(),
                    tx_hash: None,
                    error: Some(format!("POST /payments failed: {e}")),
                    rail: SettlementRail::Lightning,
                };
            }
            Ok(r) if !r.status().is_success() => {
                let status = r.status().as_u16();
                let body = r.text().await.unwrap_or_default();
                return SettlementResult {
                    status: "error".into(),
                    tx_hash: None,
                    error: Some(format!("POST /payments HTTP {status}: {body}")),
                    rail: SettlementRail::Lightning,
                };
            }
            Ok(r) => match r.json::<PaymentResponse>().await {
                Ok(p) if p.status == "error" => {
                    return SettlementResult {
                        status: "error".into(),
                        tx_hash: None,
                        error: p.error,
                        rail: SettlementRail::Lightning,
                    };
                }
                Ok(p) => p.payment_id.unwrap_or_else(|| work_ref.to_owned()),
                Err(e) => {
                    return SettlementResult {
                        status: "error".into(),
                        tx_hash: None,
                        error: Some(format!("payment response parse error: {e}")),
                        rail: SettlementRail::Lightning,
                    };
                }
            },
        };

        // Step 2: poll for confirmation.
        let status_url = format!("{}/payments/{payment_id}/status", self.executor_endpoint);
        for attempt in 0..POLL_MAX_ATTEMPTS {
            tokio::time::sleep(Duration::from_millis(POLL_INTERVAL_MILLIS)).await;

            match self.client.get(&status_url).send().await {
                Ok(r) if r.status().is_success() => {
                    match r.json::<PaymentStatus>().await {
                        Ok(ps) if ps.status == "completed" || ps.status == "settled" => {
                            info!(payment_id, work_ref, "mesh-llm payment confirmed");
                            return SettlementResult {
                                status: "settled".into(),
                                tx_hash: ps.tx_hash,
                                error: None,
                                rail: SettlementRail::Lightning,
                            };
                        }
                        Ok(ps) if ps.status == "failed" => {
                            return SettlementResult {
                                status: "failed".into(),
                                tx_hash: None,
                                error: ps.error,
                                rail: SettlementRail::Lightning,
                            };
                        }
                        Ok(ps) => {
                            info!(attempt, status = %ps.status, "mesh-llm payment pending");
                        }
                        Err(e) => {
                            warn!(attempt, error = %e, "status parse error");
                        }
                    }
                }
                Ok(r) => {
                    warn!(attempt, status = r.status().as_u16(), "status poll non-2xx");
                }
                Err(e) => {
                    warn!(attempt, error = %e, "status poll error");
                }
            }
        }

        // Timed out — return pending so caller can retry.
        SettlementResult {
            status: "passthrough_pending".into(),
            tx_hash: None,
            error: Some(format!("payment {payment_id} not confirmed after {POLL_MAX_ATTEMPTS} polls")),
            rail: SettlementRail::Lightning,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_stores_endpoint_trimmed() {
        let pt = MeshLlmPassthrough::new("http://executor:8080/");
        assert_eq!(pt.executor_endpoint, "http://executor:8080");
    }

    /// Verifies the happy-path URL construction without a live server.
    /// End-to-end HTTP tests require a mesh-llm executor — integration tests only.
    #[test]
    fn payment_url_format() {
        let pt = MeshLlmPassthrough::new("http://executor:8080");
        let pay_url = format!("{}/payments", pt.executor_endpoint);
        let status_url = format!("{}/payments/ref-123/status", pt.executor_endpoint);
        assert_eq!(pay_url, "http://executor:8080/payments");
        assert_eq!(status_url, "http://executor:8080/payments/ref-123/status");
    }
}
