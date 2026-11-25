//! `urace-exchange` — P2P feature market: catalog, equity, matching, policy, and runtime registry.

pub mod equity_auto_trade;
pub mod feature_catalog;
pub mod feature_equity;
pub mod feature_matcher;
pub mod feature_policy;
pub mod local_feature_sources;
pub mod runtime_features;

pub use equity_auto_trade::{
    AutoBuyConfig, AutoBuyContext, AutoBuyFill, AutoBuyReport, AutoMintConfig, AutoSellConfig,
    AutoSellContext, AutoSellListed, AutoSellReport, AutoSkip, AutoTradeConfig, AutoTradeError,
    AutoTradePreset, DepletionState, DepletionStatus, EquityListing, ListingState,
    evaluate_auto_buy_listing, evaluate_auto_sell_position, feature_depletion_status,
    listing_state, open_listings, supply_pressure,
};
pub use feature_catalog::{AtomDescriptor, CatalogError, FeatureAtom, FeatureCatalog, Lifecycle};
pub use feature_equity::{EquityError, EquityPosition, FeatureEquityLedger};
pub use feature_matcher::{best_match, match_features, MatchScore};
pub use feature_policy::{EffectivePolicy, FeaturePolicy, PolicyError};
pub use local_feature_sources::{
    BindingStatus, SourceBindingError, SourceBindingResult, SourceFileEntry,
    compute_local_source_binding, resolve_local_source_binding,
};
pub use runtime_features::{FeatureRegistry, RegistryError, RuntimeFeature};
