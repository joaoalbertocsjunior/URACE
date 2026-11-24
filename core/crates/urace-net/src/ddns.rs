//! Optional DDNS updater — mirrors `ddns.py` (DuckDNS + generic provider).
//!
//! `DdnsUpdater` posts IP changes to a provider endpoint via HTTP.
//! Real endpoint logic is provider-specific; DuckDNS is the primary target.

use thiserror::Error;
use tracing::{debug, warn};

/// Public IP detection URLs — tried in order until one responds.
const PUBLIC_IP_SOURCES: &[&str] = &[
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://checkip.amazonaws.com",
];

const DUCKDNS_UPDATE_URL: &str = "https://www.duckdns.org/update";

#[derive(Debug, Error)]
pub enum DdnsError {
    #[error("DDNS not configured: {0}")]
    NotConfigured(String),
    #[error("HTTP error: {0}")]
    HttpError(String),
}

/// DDNS updater — sends IP change notifications to the configured provider.
#[derive(Debug, Clone)]
pub struct DdnsUpdater {
    /// Provider name, e.g. "duckdns" or a full base URL.
    pub provider: String,
    /// Hostname / subdomain to update.
    pub hostname: String,
    /// API token / secret.
    pub token: String,
}

impl DdnsUpdater {
    /// Create a new updater.
    pub fn new(provider: &str, hostname: &str, token: &str) -> Self {
        Self {
            provider: provider.to_string(),
            hostname: hostname.to_string(),
            token: token.to_string(),
        }
    }

    /// Update the DNS record for `self.hostname` to point at `ip`.
    ///
    /// Dispatches to the provider-specific implementation.
    /// For unknown providers the update URL is treated as `provider` directly.
    pub async fn update_ip(&self, ip: &str) -> Result<(), DdnsError> {
        if self.token.is_empty() {
            return Err(DdnsError::NotConfigured("token is empty".into()));
        }
        if self.hostname.is_empty() {
            return Err(DdnsError::NotConfigured("hostname is empty".into()));
        }

        match self.provider.as_str() {
            "duckdns" => self.update_duckdns(ip).await,
            other => {
                // Generic: treat `provider` as a base URL and append query params.
                if other.starts_with("https://") || other.starts_with("http://") {
                    self.update_generic(other, ip).await
                } else {
                    Err(DdnsError::NotConfigured(format!(
                        "unknown provider '{other}' — use 'duckdns' or a full HTTPS URL"
                    )))
                }
            }
        }
    }

    async fn update_duckdns(&self, ip: &str) -> Result<(), DdnsError> {
        let url = format!(
            "{base}?domains={domain}&token={token}&ip={ip}",
            base = DUCKDNS_UPDATE_URL,
            domain = urlencoded(&self.hostname),
            token = urlencoded(&self.token),
            ip = urlencoded(ip),
        );
        debug!(url = %url, "DuckDNS update request");
        let client = reqwest::Client::new();
        let resp = client
            .get(&url)
            .send()
            .await
            .map_err(|e| DdnsError::HttpError(e.to_string()))?;
        let body = resp
            .text()
            .await
            .map_err(|e| DdnsError::HttpError(e.to_string()))?;
        if body.to_uppercase().starts_with("OK") {
            Ok(())
        } else {
            warn!(response = %body, "DuckDNS returned non-OK response");
            Err(DdnsError::HttpError(format!("DuckDNS responded: {body}")))
        }
    }

    async fn update_generic(&self, base_url: &str, ip: &str) -> Result<(), DdnsError> {
        let url = format!(
            "{base}?hostname={host}&ip={ip}&token={token}",
            base = base_url,
            host = urlencoded(&self.hostname),
            ip = urlencoded(ip),
            token = urlencoded(&self.token),
        );
        debug!(url = %url, "Generic DDNS update request");
        let client = reqwest::Client::new();
        client
            .put(&url)
            .send()
            .await
            .map_err(|e| DdnsError::HttpError(e.to_string()))?;
        Ok(())
    }
}

/// Minimal percent-encoding for query string values (spaces, &, = only).
fn urlencoded(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            ' ' => "%20".to_string(),
            '&' => "%26".to_string(),
            '=' => "%3D".to_string(),
            '+' => "%2B".to_string(),
            '#' => "%23".to_string(),
            _ => c.to_string(),
        })
        .collect()
}

/// Attempt to detect the current public IPv4 via well-known HTTP endpoints.
///
/// Returns the first valid IPv4 string found, or `None` if all fail.
pub async fn get_current_public_ip() -> Option<String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .ok()?;

    for &url in PUBLIC_IP_SOURCES {
        match client.get(url).send().await {
            Ok(resp) => {
                if let Ok(text) = resp.text().await {
                    let ip = text.trim().to_string();
                    // Validate: looks like an IPv4 address
                    if is_valid_ipv4(&ip) {
                        debug!(ip = %ip, source = %url, "public IP detected");
                        return Some(ip);
                    }
                }
            }
            Err(e) => {
                debug!(url = %url, error = %e, "public IP source unreachable");
            }
        }
    }
    None
}

fn is_valid_ipv4(s: &str) -> bool {
    let parts: Vec<&str> = s.split('.').collect();
    if parts.len() != 4 {
        return false;
    }
    parts.iter().all(|p| p.parse::<u8>().is_ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ddns_updater_new() {
        let u = DdnsUpdater::new("duckdns", "myhostname", "mytoken");
        assert_eq!(u.provider, "duckdns");
        assert_eq!(u.hostname, "myhostname");
        assert_eq!(u.token, "mytoken");
    }

    #[tokio::test]
    async fn test_update_ip_empty_token_returns_not_configured() {
        let u = DdnsUpdater::new("duckdns", "host", "");
        let err = u.update_ip("1.2.3.4").await.unwrap_err();
        assert!(matches!(err, DdnsError::NotConfigured(_)));
    }

    #[tokio::test]
    async fn test_update_ip_empty_hostname_returns_not_configured() {
        let u = DdnsUpdater::new("duckdns", "", "token");
        let err = u.update_ip("1.2.3.4").await.unwrap_err();
        assert!(matches!(err, DdnsError::NotConfigured(_)));
    }

    #[tokio::test]
    async fn test_update_ip_unknown_provider() {
        let u = DdnsUpdater::new("unknownprovider", "host", "token");
        let err = u.update_ip("1.2.3.4").await.unwrap_err();
        assert!(matches!(err, DdnsError::NotConfigured(_)));
    }

    #[test]
    fn test_is_valid_ipv4() {
        assert!(is_valid_ipv4("1.2.3.4"));
        assert!(is_valid_ipv4("192.168.0.1"));
        assert!(!is_valid_ipv4("not_an_ip"));
        assert!(!is_valid_ipv4("1.2.3"));
        assert!(!is_valid_ipv4("1.2.3.4.5"));
        assert!(!is_valid_ipv4(""));
    }

    #[test]
    fn test_urlencoded() {
        assert_eq!(urlencoded("hello world"), "hello%20world");
        assert_eq!(urlencoded("a&b=c"), "a%26b%3Dc");
        assert_eq!(urlencoded("plain"), "plain");
    }
}
