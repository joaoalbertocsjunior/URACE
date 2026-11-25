pub mod atomic_write;
pub mod compaction;
pub mod credit_ledger;
pub mod escrow;
pub mod journal;
pub mod ledger_compaction;
pub mod ledger_economics;
pub mod ledger_reputation;
pub mod ledger_sync;
pub mod schema_version;
pub mod signed_ledger;
pub mod token_ledger;
pub mod tokenomics;
pub mod units;

pub use atomic_write::{atomic_append_jsonl, atomic_write};
pub use compaction::{
    check_retention_violations, get_compaction_status, load_amendments, load_index,
    load_manifest, verify_manifest_on_startup, ArchiveAmendment, CompactionEngine,
    CompactionEvent, CompactionFieldError, CompactionIndex, CompactionManifest, CompactionMode,
    CompactionSummary, RetentionGap, RetentionPolicy,
};
pub use credit_ledger::{CreditError, CreditLedger, PEER_CAP, UNIT};
pub use escrow::{EscrowEntry, EscrowError, EscrowStore};
pub use journal::{Journal, JournalError};
pub use ledger_compaction::{compact, CompactionError, CompactionResult};
pub use ledger_economics::{
    combined_rep_score, distribution_fee_units, epoch_decay_amount,
    feature_borrow_cost_units, feature_borrow_cost_with_rep, feature_complexity_score,
    feature_earn_cap_units, supply_pressure_multiplier, wilson_lower, LedgerEconomics,
};
pub use ledger_reputation::{discount, ReputationEntry, ReputationError, ReputationStore};
pub use ledger_sync::{
    apply_tail_payload, balance_from_seal, build_sync_attestation, build_sync_payload,
    exchange_checkpoint, fork_resolution_policy, latest_seal, prune_to_window,
    row_sha256, sync_summary, tail_since_seal, verify_tail, CheckpointRecord,
    ForkAction, ForkResolution, MergeResult, SyncAttestation, SyncPayload, SyncSummary,
    DEFAULT_TAIL_ROWS, SCHEMA as LEDGER_SYNC_SCHEMA,
};
pub use schema_version::{can_read_schema, validate_row_schema, SchemaVersionError, CURRENT_SCHEMA_VERSION};
pub use signed_ledger::{
    pack, unpack, AppendResult, BlockPayload, HeadRecord, Ledger, LedgerIdentity,
    SignedBlock, SignedLedgerError, VerifyReport, LEDGER_SCHEMA_VERSION,
};
pub use token_ledger::{TokenLedger, TokenLedgerError, DEFAULT_BASELINE_GRANT};
pub use tokenomics::{mint_amount, mint_on_qualified_acceptance, PEER_CAP as TOKEN_PEER_CAP, UNIT as TOKEN_UNIT, UCR_TO_SAT};
pub use units::{earn_units as units_earn, from_chain_units, from_display, spend_units as units_spend, to_chain_units, to_display, UnitsError, UNIT as UCR_UNIT};
