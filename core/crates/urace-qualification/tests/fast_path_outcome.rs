use urace_qualification::{
    FastPathError, FastPathRegistry, OutcomeKind, OutcomeSignal, OutcomeSignalError,
    FAST_PATH_CHAIN_RESET_SECS, FAST_PATH_MAX_CHAIN_DEPTH, FAST_PATH_MAX_DIFF_BYTES,
    MINIMUM_CORROBORATING_PEERS,
};
use urace_qualification::{validate_signal, reputation_delta_from_signal};

fn valid_signal(score_delta: f64, peers: Vec<String>) -> OutcomeSignal {
    OutcomeSignal {
        signal_id: "sig-1".into(),
        feature_id: "feat-1".into(),
        executor_peer_id: "exec-1".into(),
        kind: OutcomeKind::Improvement { score_delta },
        observed_at_secs: 1_000_000,
        corroborating_peers: peers,
        evidence_hash: "a".repeat(64),
    }
}

#[test]
fn fast_path_allowed_for_small_diff() {
    let mut registry = FastPathRegistry::new();
    let decision = registry.decide("executor-1", FAST_PATH_MAX_DIFF_BYTES - 1, 1_000_000).unwrap();
    assert_eq!(decision.path, urace_qualification::QualificationPathKind::FastPath);
}

#[test]
fn chain_depth_exhausted_after_max_consecutive() {
    let mut registry = FastPathRegistry::new();
    let now = 1_000_000u64;
    for _ in 0..FAST_PATH_MAX_CHAIN_DEPTH {
        registry.decide("executor-1", 100, now).unwrap();
    }
    let err = registry.decide("executor-1", 100, now).unwrap_err();
    assert!(matches!(err, FastPathError::ChainDepthExceeded { .. }));
}

#[test]
fn chain_resets_after_manual_reset() {
    let mut registry = FastPathRegistry::new();
    let now = 1_000_000u64;
    for _ in 0..FAST_PATH_MAX_CHAIN_DEPTH {
        registry.decide("executor-1", 100, now).unwrap();
    }
    registry.reset_chain("executor-1");
    assert!(registry.decide("executor-1", 100, now).is_ok());
}

#[test]
fn outcome_signal_valid_with_three_peers() {
    let peers = vec!["peer-a".into(), "peer-b".into(), "peer-c".into()];
    let signal = valid_signal(0.5, peers);
    assert!(validate_signal(&signal, 1_000_100).is_ok());
}

#[test]
fn outcome_signal_rejected_with_two_peers() {
    let signal = valid_signal(0.5, vec!["peer-a".into(), "peer-b".into()]);
    assert!(matches!(
        validate_signal(&signal, 1_000_100),
        Err(OutcomeSignalError::InsufficientCorroboration { .. })
    ));
}

#[test]
fn reputation_delta_is_ten_percent_of_score_delta() {
    let peers = vec!["a".into(), "b".into(), "c".into()];
    let signal = valid_signal(0.5, peers);
    let delta = reputation_delta_from_signal(&signal);
    assert!((delta - 0.05).abs() < 1e-9);
}
