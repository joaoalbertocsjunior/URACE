//! Integration test: G-CRIT-01 — authority gate bypass attempt must fail
//! G-CRIT-05 — mint-without-score-delta must fail

use urace_ledger::tokenomics::{mint_amount, mint_on_qualified_acceptance, PEER_CAP, UNIT};

#[test]
fn g_crit_05_no_mint_on_zero_delta() {
    assert!(!mint_on_qualified_acceptance(0), "delta=0 must not trigger mint");
    assert!(!mint_on_qualified_acceptance(-1), "delta=-1 must not trigger mint");
    assert!(mint_on_qualified_acceptance(1), "delta=1 must trigger mint");
}

#[test]
fn g_crit_05_mint_amount_none_on_non_positive() {
    assert!(mint_amount(0).is_none(), "mint_amount(0) must return None");
    assert!(mint_amount(-100).is_none(), "mint_amount(-100) must return None");
}

#[test]
fn peer_cap_never_exceeded() {
    // Even with very large score_delta, mint_amount is clamped to PEER_CAP
    let result = mint_amount(PEER_CAP + 1_000_000);
    assert_eq!(result, Some(PEER_CAP), "mint_amount must clamp to PEER_CAP");
}

#[test]
fn unit_constant_unchanged() {
    assert_eq!(UNIT, 100_000_000, "UNIT constant must remain 10^8");
}

#[test]
fn peer_cap_constant_unchanged() {
    assert_eq!(PEER_CAP, 50 * UNIT, "PEER_CAP must remain 50 UNIT");
}
