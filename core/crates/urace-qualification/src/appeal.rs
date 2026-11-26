//! M49 — Trial outcome appeal window.
//!
//! An active appeal blocks minting for the duration of the appeal window.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const DEFAULT_APPEAL_WINDOW_SECS: u64 = 86_400; // 24 hours

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AppealStatus {
    Active,
    Resolved { upheld: bool, resolved_at: u64 },
    Expired { expired_at: u64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Appeal {
    pub work_id: String,
    pub appellant_peer_id: String,
    pub filed_at_secs: u64,
    pub window_secs: u64,
    pub status: AppealStatus,
    pub reason: String,
}

impl Appeal {
    /// Returns true if the appeal is still within its active window.
    pub fn is_active(&self, now_secs: u64) -> bool {
        matches!(self.status, AppealStatus::Active)
            && now_secs < self.filed_at_secs + self.window_secs
    }

    /// Returns true if minting should be blocked (appeal active and not expired).
    pub fn blocks_mint(&self, now_secs: u64) -> bool {
        self.is_active(now_secs)
    }
}

pub struct AppealRegistry {
    appeals: HashMap<String, Appeal>, // work_id -> appeal
}

impl AppealRegistry {
    pub fn new() -> Self {
        AppealRegistry {
            appeals: HashMap::new(),
        }
    }

    pub fn file(&mut self, appeal: Appeal) {
        self.appeals.insert(appeal.work_id.clone(), appeal);
    }

    /// Returns true if an active, unexpired appeal exists for the given `work_id`.
    pub fn is_mint_blocked(&self, work_id: &str, now_secs: u64) -> bool {
        self.appeals
            .get(work_id)
            .map(|a| a.blocks_mint(now_secs))
            .unwrap_or(false)
    }

    /// Resolve an appeal for `work_id`. No-op if no appeal exists.
    pub fn resolve(&mut self, work_id: &str, upheld: bool, now_secs: u64) {
        if let Some(appeal) = self.appeals.get_mut(work_id) {
            appeal.status = AppealStatus::Resolved {
                upheld,
                resolved_at: now_secs,
            };
        }
    }
}

impl Default for AppealRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_appeal(work_id: &str, filed_at: u64) -> Appeal {
        Appeal {
            work_id: work_id.to_string(),
            appellant_peer_id: "peer-A".to_string(),
            filed_at_secs: filed_at,
            window_secs: DEFAULT_APPEAL_WINDOW_SECS,
            status: AppealStatus::Active,
            reason: "test appeal".to_string(),
        }
    }

    #[test]
    fn active_appeal_blocks_mint() {
        let mut reg = AppealRegistry::new();
        reg.file(make_appeal("work-1", 1_000_000));
        // now_secs is well inside the window
        assert!(reg.is_mint_blocked("work-1", 1_000_000 + 3600));
    }

    #[test]
    fn expired_appeal_does_not_block() {
        let mut reg = AppealRegistry::new();
        reg.file(make_appeal("work-2", 1_000_000));
        // now_secs is past filed_at + window_secs
        let after_expiry = 1_000_000 + DEFAULT_APPEAL_WINDOW_SECS + 1;
        assert!(!reg.is_mint_blocked("work-2", after_expiry));
    }

    #[test]
    fn resolved_appeal_does_not_block() {
        let mut reg = AppealRegistry::new();
        reg.file(make_appeal("work-3", 1_000_000));
        // Resolve the appeal
        reg.resolve("work-3", false, 1_000_000 + 100);
        // Even inside the window, a resolved appeal should not block
        assert!(!reg.is_mint_blocked("work-3", 1_000_000 + 200));
    }
}
