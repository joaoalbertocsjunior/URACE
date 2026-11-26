//! M55 — Compliance audit export: generate jurisdiction-scoped compliance reports.

use serde::{Deserialize, Serialize};

/// Categories of events that must appear in compliance reports.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ComplianceEventKind {
    TokenTransfer,
    GovernanceVote,
    PeerAdmission,
    KeyRotation,
    PolicyUpdate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceEvent {
    pub event_id: String,
    pub kind: ComplianceEventKind,
    pub actor_peer_id: String,
    pub amount_ucr: Option<i64>,
    pub at_unix: u64,
    pub jurisdiction: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceReport {
    pub jurisdiction: String,
    pub period_start_unix: u64,
    pub period_end_unix: u64,
    pub events: Vec<ComplianceEvent>,
    pub total_transfer_volume_ucr: i64,
    pub generated_at_unix: u64,
}

/// Generate a compliance report for `jurisdiction` covering [period_start_unix, period_end_unix].
/// Filters events by jurisdiction and time range, sums transfer volume.
pub fn generate_compliance_report(
    events: &[ComplianceEvent],
    jurisdiction: &str,
    period_start_unix: u64,
    period_end_unix: u64,
    generated_at_unix: u64,
) -> ComplianceReport {
    let filtered: Vec<ComplianceEvent> = events
        .iter()
        .filter(|e| {
            e.jurisdiction == jurisdiction
                && e.at_unix >= period_start_unix
                && e.at_unix <= period_end_unix
        })
        .cloned()
        .collect();

    let total_transfer_volume_ucr = filtered
        .iter()
        .filter(|e| e.kind == ComplianceEventKind::TokenTransfer)
        .filter_map(|e| e.amount_ucr)
        .sum();

    ComplianceReport {
        jurisdiction: jurisdiction.to_string(),
        period_start_unix,
        period_end_unix,
        events: filtered,
        total_transfer_volume_ucr,
        generated_at_unix,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_event(
        id: &str,
        kind: ComplianceEventKind,
        at_unix: u64,
        jurisdiction: &str,
        amount_ucr: Option<i64>,
    ) -> ComplianceEvent {
        ComplianceEvent {
            event_id: id.to_string(),
            kind,
            actor_peer_id: "peer-1".to_string(),
            amount_ucr,
            at_unix,
            jurisdiction: jurisdiction.to_string(),
        }
    }

    #[test]
    fn filters_to_correct_jurisdiction() {
        let events = vec![
            make_event("e1", ComplianceEventKind::GovernanceVote, 100, "EU", None),
            make_event("e2", ComplianceEventKind::GovernanceVote, 100, "US", None),
            make_event("e3", ComplianceEventKind::PeerAdmission, 200, "EU", None),
        ];
        let report = generate_compliance_report(&events, "EU", 0, 1000, 9999);
        assert_eq!(report.events.len(), 2);
        assert!(report.events.iter().all(|e| e.jurisdiction == "EU"));
    }

    #[test]
    fn filters_to_time_range() {
        let events = vec![
            make_event("e1", ComplianceEventKind::KeyRotation, 50, "EU", None),
            make_event("e2", ComplianceEventKind::KeyRotation, 100, "EU", None),
            make_event("e3", ComplianceEventKind::KeyRotation, 200, "EU", None),
            make_event("e4", ComplianceEventKind::KeyRotation, 300, "EU", None),
        ];
        let report = generate_compliance_report(&events, "EU", 100, 200, 9999);
        assert_eq!(report.events.len(), 2);
        let ids: Vec<&str> = report.events.iter().map(|e| e.event_id.as_str()).collect();
        assert!(ids.contains(&"e2"));
        assert!(ids.contains(&"e3"));
    }

    #[test]
    fn sums_transfer_volume_correctly() {
        let events = vec![
            make_event(
                "t1",
                ComplianceEventKind::TokenTransfer,
                100,
                "EU",
                Some(500),
            ),
            make_event(
                "t2",
                ComplianceEventKind::TokenTransfer,
                150,
                "EU",
                Some(300),
            ),
            // Non-transfer events should not add to volume
            make_event("v1", ComplianceEventKind::GovernanceVote, 120, "EU", None),
        ];
        let report = generate_compliance_report(&events, "EU", 0, 1000, 9999);
        assert_eq!(report.total_transfer_volume_ucr, 800);
    }

    #[test]
    fn empty_events_produces_zero_volume_report() {
        let report = generate_compliance_report(&[], "EU", 0, 1000, 9999);
        assert_eq!(report.events.len(), 0);
        assert_eq!(report.total_transfer_volume_ucr, 0);
        assert_eq!(report.jurisdiction, "EU");
        assert_eq!(report.period_start_unix, 0);
        assert_eq!(report.period_end_unix, 1000);
    }
}
