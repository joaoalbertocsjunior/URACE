//! Automated feature equity trading: order book, bid/ask matching, auto-trade policies, settlement triggers.
//!
//! Ported from `runtime/urace/equity_auto_trade.py`.
//!
//! ## §62z / Authority boundary
//! [`fill_listing`] transfers UCR (via `sell_equity` semantics): any call that
//! supplies a non-zero `price_units` MUST be gated through `urace-authority`
//! before execution.  The helpers [`auto_buy`] and [`auto_sell`] are tagged with
//! `// §62z: spend/transfer — REQUIRES authority gate before wiring to runtime`
//! comments at every execution point.  Until the authority gate is wired,
//! callers must not invoke them in a live spend path.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use time::OffsetDateTime;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// 100 UCR = 100_000_000 indivisible units (UNIT).
pub const UNIT: u64 = 100_000_000;

/// Listings expire after 30 days (seconds).
pub const LISTING_EXPIRY_SECONDS: i64 = 30 * 86_400;

/// Maximum network-wide basis points per feature (100%).
pub const MAX_EQUITY_BP_PER_FEATURE: u64 = 10_000;

/// 24-hour wash-trade detection window (seconds).
pub const WASH_TRADE_WINDOW_SECONDS: i64 = 86_400;

/// Price-momentum ceiling multiplier (1.5× 7-day median).
pub const PRICE_MOMENTUM_MAX_MULTIPLIER_NUM: u64 = 3;
pub const PRICE_MOMENTUM_MAX_MULTIPLIER_DEN: u64 = 2;

/// Price-momentum look-back window (7 days, seconds).
pub const PRICE_MOMENTUM_WINDOW_SECONDS: i64 = 7 * 86_400;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum AutoTradeError {
    #[error("seller {seller_id:?} holds {held} bp, cannot list {requested} bp")]
    InsufficientEquity {
        seller_id: String,
        held: u64,
        requested: u64,
    },
    #[error("minimum listing is {min} bp, got {got}")]
    BelowMinimum { min: u64, got: u64 },
    #[error("feature {0:?} is DEPLETED — no borrow revenue remains; use zero-price transfer")]
    Depleted(String),
    #[error("listing {0:?} not found")]
    ListingNotFound(String),
    #[error("listing {0:?} is not OPEN")]
    ListingNotOpen(String),
    #[error("listing {0:?} has expired")]
    ListingExpired(String),
    #[error("ask_price_units cannot be negative")]
    NegativePrice,
    #[error("wash trading: {peer_id:?} bought and sold {feature_id:?} within 24h")]
    WashTrading { peer_id: String, feature_id: String },
    #[error("ask {ask} exceeds price-momentum ceiling {ceiling} (7-day median {median} × 1.5)")]
    PriceMomentum { ask: u64, ceiling: u64, median: u64 },
    #[error("unknown config section or key: {0}")]
    ConfigKey(String),
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// State of an equity listing in the order book.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ListingState {
    Open,
    Filled,
    Cancelled,
    Expired,
    NotFound,
}

/// Depletion state of a feature's borrow-revenue stream.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum DepletionState {
    Healthy,
    Slowing,
    NearDepleted,
    Depleted,
}

impl DepletionState {
    /// Whether this feature may be listed on the open market.
    pub fn listable(&self) -> bool {
        !matches!(self, DepletionState::Depleted)
    }
}

/// Depletion analysis for a feature's borrow-revenue stream.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DepletionStatus {
    pub feature_id: String,
    pub state: DepletionState,
    pub listable: bool,
    pub adoption_rate: f64,
    pub adoption_count: u64,
    pub estimated_network_size: u64,
    pub supply_pressure: f64,
    pub remaining_adopters: u64,
    /// Estimated remaining revenue per basis-point held (units).
    pub estimated_remaining_revenue_per_bp_units: u64,
    pub notes: String,
}

/// An equity listing broadcast — seller advertises bp at ask_price_units.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquityListing {
    pub listing_id: String,
    pub feature_id: String,
    pub seller_id: String,
    pub basis_points: u64,
    pub ask_price_units: u64,
    pub expires_at_unix: i64,
    pub at_unix: i64,
    pub at: String,
}

/// Audit row kinds emitted by this module.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum AutoTradeAuditRow {
    EquityListing {
        listing_id: String,
        feature_id: String,
        seller_id: String,
        basis_points: u64,
        ask_price_units: u64,
        expires_at_unix: i64,
        at_unix: i64,
        at: String,
    },
    EquityListingFilled {
        listing_id: String,
        feature_id: String,
        seller_id: String,
        buyer_id: String,
        basis_points: u64,
        price_units: u64,
        at_unix: i64,
        at: String,
    },
    EquityListingCancelled {
        listing_id: String,
        seller_id: String,
        at_unix: i64,
        at: String,
    },
}

/// Per-peer auto-buy configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoBuyConfig {
    pub enabled: bool,
    pub min_quality_wilson: f64,
    pub min_adoption_count: u64,
    pub max_price_multiplier: f64,
    pub max_bp_per_feature: u64,
    /// 0 = unlimited.
    pub max_spend_per_run_units: u64,
    pub max_adoption_rate: f64,
    pub min_supply_pressure: f64,
    pub min_remaining_adopters: u64,
    pub min_lucrativity_score: f64,
    pub lucrativity_window_days: f64,
    pub warm_up_borrow_threshold: u64,
}

impl Default for AutoBuyConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            min_quality_wilson: 0.65,
            min_adoption_count: 5,
            max_price_multiplier: 1.0,
            max_bp_per_feature: 2_000,
            max_spend_per_run_units: 0,
            max_adoption_rate: 0.70,
            min_supply_pressure: 0.25,
            min_remaining_adopters: 5,
            min_lucrativity_score: 0.10,
            lucrativity_window_days: 30.0,
            warm_up_borrow_threshold: 5,
        }
    }
}

/// Per-peer auto-sell configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoSellConfig {
    pub enabled: bool,
    pub min_return_multiplier: f64,
    pub bp_to_sell_per_trigger: u64,
    pub min_hold_bp_to_trigger: u64,
    pub sell_on_near_depleted: bool,
    pub sell_on_slowing: bool,
    pub auto_replicate: bool,
    pub replication_offer_cooldown: i64,
}

impl Default for AutoSellConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            min_return_multiplier: 2.0,
            bp_to_sell_per_trigger: 1_000,
            min_hold_bp_to_trigger: 500,
            sell_on_near_depleted: false,
            sell_on_slowing: false,
            auto_replicate: false,
            replication_offer_cooldown: 86_400,
        }
    }
}

/// Auto-mint configuration for completed minimal-work outputs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoMintConfig {
    pub enabled: bool,
    pub max_complexity_threshold: f64,
    pub min_quality_score: f64,
}

impl Default for AutoMintConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            max_complexity_threshold: 0.5,
            min_quality_score: 0.6,
        }
    }
}

/// Full auto-trade configuration (auto_buy + auto_sell + auto_mint).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AutoTradeConfig {
    pub auto_buy: AutoBuyConfig,
    pub auto_sell: AutoSellConfig,
    pub auto_mint: AutoMintConfig,
}

/// Named preset strategies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AutoTradePreset {
    Conservative,
    Balanced,
    Aggressive,
}

impl AutoTradePreset {
    /// Apply preset overrides to `config`, returning the modified copy.
    pub fn apply(self, mut config: AutoTradeConfig) -> AutoTradeConfig {
        match self {
            AutoTradePreset::Conservative => {
                config.auto_buy.min_quality_wilson = 0.75;
                config.auto_buy.min_adoption_count = 10;
                config.auto_buy.max_price_multiplier = 0.9;
                config.auto_buy.max_bp_per_feature = 1_000;
                config.auto_buy.max_adoption_rate = 0.60;
                config.auto_buy.min_supply_pressure = 0.30;
                config.auto_buy.min_remaining_adopters = 10;
                config.auto_buy.min_lucrativity_score = 0.20;
                config.auto_sell.min_return_multiplier = 3.0;
                config.auto_sell.bp_to_sell_per_trigger = 500;
                config.auto_sell.min_hold_bp_to_trigger = 1_000;
            }
            AutoTradePreset::Balanced => {
                config.auto_buy.min_quality_wilson = 0.65;
                config.auto_buy.min_adoption_count = 5;
                config.auto_buy.max_price_multiplier = 1.0;
                config.auto_buy.max_bp_per_feature = 2_000;
                config.auto_buy.max_adoption_rate = 0.70;
                config.auto_buy.min_supply_pressure = 0.25;
                config.auto_buy.min_remaining_adopters = 5;
                config.auto_buy.min_lucrativity_score = 0.10;
                config.auto_sell.min_return_multiplier = 2.0;
                config.auto_sell.bp_to_sell_per_trigger = 1_000;
                config.auto_sell.min_hold_bp_to_trigger = 500;
            }
            AutoTradePreset::Aggressive => {
                config.auto_buy.min_quality_wilson = 0.50;
                config.auto_buy.min_adoption_count = 3;
                config.auto_buy.max_price_multiplier = 1.2;
                config.auto_buy.max_bp_per_feature = 3_000;
                config.auto_buy.max_adoption_rate = 0.80;
                config.auto_buy.min_supply_pressure = 0.15;
                config.auto_buy.min_remaining_adopters = 3;
                config.auto_buy.min_lucrativity_score = 0.05;
                config.auto_sell.min_return_multiplier = 1.5;
                config.auto_sell.bp_to_sell_per_trigger = 2_000;
                config.auto_sell.min_hold_bp_to_trigger = 250;
            }
        }
        config
    }
}

// ---------------------------------------------------------------------------
// Supply-pressure helper
// ---------------------------------------------------------------------------

/// Quadratic supply-pressure decay: 1.0 at zero spend, approaching 0 as
/// spend grows relative to network size.  Mirrors Python `supply_pressure_multiplier`.
pub fn supply_pressure(total_feature_spend_units: u64, network_size: u64) -> f64 {
    let net = network_size.max(1) as f64;
    // scale: 1 adoption ≈ UNIT / 100 spend
    let scale = (UNIT / 100) as f64 * net;
    let x = total_feature_spend_units as f64 / scale;
    (1.0 - x).max(0.0).powi(2)
}

// ---------------------------------------------------------------------------
// Depletion analysis
// ---------------------------------------------------------------------------

/// Minimal audit-row view needed by depletion analysis (caller provides).
pub struct DepletionInput<'a> {
    /// Pre-filtered CREDIT_DELTA spend rows for this feature.
    pub adopter_peer_ids: &'a [String],
    /// Total units spent on borrows for this feature (all time).
    pub total_feature_spend_units: u64,
    /// Estimated live network size.
    pub estimated_network_size: u64,
}

/// Evaluate how close a feature is to borrow-revenue exhaustion.
pub fn feature_depletion_status(feature_id: &str, input: &DepletionInput<'_>) -> DepletionStatus {
    let net = input.estimated_network_size.max(1);
    let adoption_count = input.adopter_peer_ids.len() as u64;
    let adoption_rate = (adoption_count as f64 / net as f64).min(1.0);
    let remaining_adopters = net.saturating_sub(adoption_count);

    let sp = supply_pressure(input.total_feature_spend_units, net);
    let mint_per = UNIT / 100; // 0.01 tokens per adoption (approximate)
    let rev_per_bp = (remaining_adopters as f64 * mint_per as f64 * sp
        / MAX_EQUITY_BP_PER_FEATURE as f64) as u64;

    let (state, notes) = if adoption_rate > 0.95 || sp < 0.05 {
        (
            DepletionState::Depleted,
            format!(
                "{:.0}% adopted, supply_pressure={:.3}. No meaningful borrow revenue remains.",
                adoption_rate * 100.0,
                sp
            ),
        )
    } else if adoption_rate > 0.80 || sp < 0.20 {
        (
            DepletionState::NearDepleted,
            format!(
                "{:.0}% adopted, supply_pressure={:.3}. Revenue declining rapidly; consider selling.",
                adoption_rate * 100.0,
                sp
            ),
        )
    } else if adoption_rate > 0.50 || sp < 0.50 {
        (
            DepletionState::Slowing,
            format!(
                "{:.0}% adopted, supply_pressure={:.3}. Growth slowing; peak revenue likely passed.",
                adoption_rate * 100.0,
                sp
            ),
        )
    } else {
        (
            DepletionState::Healthy,
            format!(
                "{:.0}% adopted, supply_pressure={:.3}. Significant borrow revenue potential remains.",
                adoption_rate * 100.0,
                sp
            ),
        )
    };

    let listable = state.listable();
    DepletionStatus {
        feature_id: feature_id.to_owned(),
        state,
        listable,
        adoption_rate,
        adoption_count,
        estimated_network_size: net,
        supply_pressure: sp,
        remaining_adopters,
        estimated_remaining_revenue_per_bp_units: rev_per_bp,
        notes,
    }
}

// ---------------------------------------------------------------------------
// Listing integrity guards
// ---------------------------------------------------------------------------

/// Check for wash trading (buy + sell same feature within 24h).
/// Returns Err if the round-trip is detected.
pub fn check_wash_trading(
    rows: &[serde_json::Value],
    peer_id: &str,
    feature_id: &str,
    now_unix: i64,
) -> Result<(), AutoTradeError> {
    let cutoff = now_unix - WASH_TRADE_WINDOW_SECONDS;
    let bought = rows.iter().any(|r| {
        matches!(
            r.get("kind").and_then(|v| v.as_str()),
            Some("EQUITY_LISTING_FILLED") | Some("EQUITY_SELL")
        ) && r.get("buyer_id").and_then(|v| v.as_str()) == Some(peer_id)
            && r.get("feature_id").and_then(|v| v.as_str()) == Some(feature_id)
            && r.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64 > cutoff
    });
    let sold = rows.iter().any(|r| {
        matches!(
            r.get("kind").and_then(|v| v.as_str()),
            Some("EQUITY_LISTING") | Some("EQUITY_SELL")
        ) && r.get("seller_id").and_then(|v| v.as_str()) == Some(peer_id)
            && r.get("feature_id").and_then(|v| v.as_str()) == Some(feature_id)
            && r.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64 > cutoff
    });
    if bought && sold {
        return Err(AutoTradeError::WashTrading {
            peer_id: peer_id.to_owned(),
            feature_id: feature_id.to_owned(),
        });
    }
    Ok(())
}

/// Validate that ask_price does not exceed 1.5× 7-day median of recent filled sales.
pub fn validate_ask_price_momentum(
    rows: &[serde_json::Value],
    feature_id: &str,
    ask_price_units: u64,
    now_unix: i64,
) -> Result<(), AutoTradeError> {
    let cutoff = now_unix - PRICE_MOMENTUM_WINDOW_SECONDS;
    let mut recent: Vec<u64> = rows
        .iter()
        .filter(|r| {
            r.get("kind").and_then(|v| v.as_str()) == Some("EQUITY_SELL")
                && r.get("feature_id").and_then(|v| v.as_str()) == Some(feature_id)
                && r.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64 > cutoff
        })
        .filter_map(|r| {
            r.get("price_units")
                .and_then(|v| v.as_u64())
                .filter(|&p| p > 0)
        })
        .collect();
    if recent.is_empty() {
        return Ok(());
    }
    recent.sort_unstable();
    let n = recent.len();
    let median = if n % 2 == 1 {
        recent[n / 2]
    } else {
        (recent[n / 2 - 1] + recent[n / 2]) / 2
    };
    let ceiling = median * PRICE_MOMENTUM_MAX_MULTIPLIER_NUM / PRICE_MOMENTUM_MAX_MULTIPLIER_DEN;
    if ask_price_units > ceiling {
        return Err(AutoTradeError::PriceMomentum {
            ask: ask_price_units,
            ceiling,
            median,
        });
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Listing state helpers
// ---------------------------------------------------------------------------

/// Return all open (unfilled, uncancelled, unexpired) listings from an audit log.
pub fn open_listings(rows: &[serde_json::Value], now_unix: i64) -> Vec<EquityListing> {
    let mut listings: std::collections::HashMap<String, EquityListing> =
        std::collections::HashMap::new();
    let mut filled: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut cancelled: std::collections::HashSet<String> = std::collections::HashSet::new();

    for r in rows {
        match r.get("kind").and_then(|v| v.as_str()) {
            Some("EQUITY_LISTING") => {
                if let (
                    Some(lid),
                    Some(fid),
                    Some(sid),
                    Some(bp),
                    Some(ask),
                    Some(exp),
                    Some(at_unix),
                    Some(at),
                ) = (
                    r.get("listing_id").and_then(|v| v.as_str()),
                    r.get("feature_id").and_then(|v| v.as_str()),
                    r.get("seller_id").and_then(|v| v.as_str()),
                    r.get("basis_points").and_then(|v| v.as_u64()),
                    r.get("ask_price_units").and_then(|v| v.as_u64()),
                    r.get("expires_at_unix").and_then(|v| v.as_i64()),
                    r.get("at_unix").and_then(|v| v.as_i64()),
                    r.get("at").and_then(|v| v.as_str()),
                ) {
                    listings.insert(
                        lid.to_owned(),
                        EquityListing {
                            listing_id: lid.to_owned(),
                            feature_id: fid.to_owned(),
                            seller_id: sid.to_owned(),
                            basis_points: bp,
                            ask_price_units: ask,
                            expires_at_unix: exp,
                            at_unix,
                            at: at.to_owned(),
                        },
                    );
                }
            }
            Some("EQUITY_LISTING_FILLED") => {
                if let Some(lid) = r.get("listing_id").and_then(|v| v.as_str()) {
                    filled.insert(lid.to_owned());
                }
            }
            Some("EQUITY_LISTING_CANCELLED") => {
                if let Some(lid) = r.get("listing_id").and_then(|v| v.as_str()) {
                    cancelled.insert(lid.to_owned());
                }
            }
            _ => {}
        }
    }

    listings
        .into_values()
        .filter(|lst| {
            !filled.contains(&lst.listing_id)
                && !cancelled.contains(&lst.listing_id)
                && now_unix <= lst.expires_at_unix
        })
        .collect()
}

/// Determine the state of a specific listing.
pub fn listing_state(rows: &[serde_json::Value], listing_id: &str, now_unix: i64) -> ListingState {
    let filled = rows.iter().any(|r| {
        r.get("kind").and_then(|v| v.as_str()) == Some("EQUITY_LISTING_FILLED")
            && r.get("listing_id").and_then(|v| v.as_str()) == Some(listing_id)
    });
    if filled {
        return ListingState::Filled;
    }
    let cancelled = rows.iter().any(|r| {
        r.get("kind").and_then(|v| v.as_str()) == Some("EQUITY_LISTING_CANCELLED")
            && r.get("listing_id").and_then(|v| v.as_str()) == Some(listing_id)
    });
    if cancelled {
        return ListingState::Cancelled;
    }
    let listing = rows.iter().find(|r| {
        r.get("kind").and_then(|v| v.as_str()) == Some("EQUITY_LISTING")
            && r.get("listing_id").and_then(|v| v.as_str()) == Some(listing_id)
    });
    match listing {
        None => ListingState::NotFound,
        Some(lst) => {
            let exp = lst
                .get("expires_at_unix")
                .and_then(|v| v.as_i64())
                .unwrap_or(0);
            if now_unix > exp {
                ListingState::Expired
            } else {
                ListingState::Open
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Auto-buy result
// ---------------------------------------------------------------------------

/// A single filled purchase from an auto-buy run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoBuyFill {
    pub listing_id: String,
    pub feature_id: String,
    pub basis_points: u64,
    pub price_units: u64,
}

/// A skipped listing from an auto-buy or auto-sell run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoSkip {
    pub listing_id: Option<String>,
    pub feature_id: String,
    pub reason: String,
}

/// Summary returned by [`evaluate_auto_buy`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoBuyReport {
    pub bought: Vec<AutoBuyFill>,
    pub skipped: Vec<AutoSkip>,
    pub spent_units: u64,
}

/// A single auto-sell listing emitted from an auto-sell run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoSellListed {
    pub listing_id: String,
    pub feature_id: String,
    pub basis_points: u64,
    pub ask_price_units: u64,
    pub depletion_state: String,
    pub depletion_triggered: bool,
}

/// Summary returned by [`evaluate_auto_sell`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoSellReport {
    pub listed: Vec<AutoSellListed>,
    pub skipped: Vec<AutoSkip>,
}

// ---------------------------------------------------------------------------
// Auto-buy policy evaluator (pure — does NOT perform I/O or authority calls)
// ---------------------------------------------------------------------------

/// Context provided by the caller for a single listing during auto-buy evaluation.
pub struct AutoBuyContext<'a> {
    pub listing: &'a EquityListing,
    pub quality_wilson: f64,
    pub adoption_count: u64,
    pub depletion: &'a DepletionStatus,
    pub lucrativity_score: f64,
    pub buyer_current_bp: u64,
    pub base_borrow_units: u64,
}

/// Evaluate whether a single listing passes the auto-buy policy gates.
///
/// Returns `Ok(())` if it passes, `Err(reason)` with a human-readable skip
/// reason if it fails.  Does NOT execute anything — caller is responsible for
/// the §62z-gated `fill_listing` call.
pub fn evaluate_auto_buy_listing(
    cfg: &AutoBuyConfig,
    buyer_id: &str,
    ctx: &AutoBuyContext<'_>,
    spent_so_far: u64,
) -> Result<(), String> {
    let lst = ctx.listing;

    if lst.seller_id == buyer_id {
        return Err("own_listing".to_owned());
    }
    if ctx.quality_wilson < cfg.min_quality_wilson {
        return Err(format!(
            "quality {:.2} < {:.2}",
            ctx.quality_wilson, cfg.min_quality_wilson
        ));
    }
    // Adoption gate with cold-start warm-up bypass
    if ctx.adoption_count < cfg.min_adoption_count
        && (cfg.warm_up_borrow_threshold == 0 || ctx.adoption_count >= cfg.warm_up_borrow_threshold)
    {
        return Err(format!(
            "adoption {} < {}",
            ctx.adoption_count, cfg.min_adoption_count
        ));
        // new feature — quality gate alone decides; adoption gate waived
    }
    // Price gate
    if cfg.max_price_multiplier > 0.0 {
        let max_price = (ctx.base_borrow_units as f64 * cfg.max_price_multiplier) as u64;
        if max_price > 0 && lst.ask_price_units > max_price {
            return Err(format!(
                "ask {} > max_price {}",
                lst.ask_price_units, max_price
            ));
        }
    }
    // Depletion guards
    if ctx.depletion.adoption_rate > cfg.max_adoption_rate {
        return Err(format!(
            "depletion: adoption_rate {:.0}% > {:.0}%",
            ctx.depletion.adoption_rate * 100.0,
            cfg.max_adoption_rate * 100.0
        ));
    }
    if ctx.depletion.supply_pressure < cfg.min_supply_pressure {
        return Err(format!(
            "depletion: supply_pressure {:.3} < {:.3}",
            ctx.depletion.supply_pressure, cfg.min_supply_pressure
        ));
    }
    if ctx.depletion.remaining_adopters < cfg.min_remaining_adopters {
        return Err(format!(
            "depletion: remaining_adopters {} < {}",
            ctx.depletion.remaining_adopters, cfg.min_remaining_adopters
        ));
    }
    if ctx.depletion.state == DepletionState::Depleted {
        return Err("depletion: feature is DEPLETED — no borrow revenue remains".to_owned());
    }
    // Lucrativity gate
    if ctx.lucrativity_score < cfg.min_lucrativity_score {
        return Err(format!(
            "lucrativity {:.3} < {:.3}",
            ctx.lucrativity_score, cfg.min_lucrativity_score
        ));
    }
    // Anti-concentration
    if ctx.buyer_current_bp + lst.basis_points > cfg.max_bp_per_feature {
        return Err(format!(
            "would hold {} > max_bp {}",
            ctx.buyer_current_bp + lst.basis_points,
            cfg.max_bp_per_feature
        ));
    }
    // Budget
    if cfg.max_spend_per_run_units > 0
        && spent_so_far + lst.ask_price_units > cfg.max_spend_per_run_units
    {
        return Err("run_budget_exhausted".to_owned());
    }

    // §62z: spend/transfer — REQUIRES authority gate before wiring to runtime.
    // fill_listing() deducts UCR from buyer; every call here is a qualifying spend.
    // Do NOT call fill_listing without routing through urace-authority first.

    Ok(())
}

// ---------------------------------------------------------------------------
// Auto-sell policy evaluator (pure)
// ---------------------------------------------------------------------------

/// Context for a single feature position during auto-sell evaluation.
pub struct AutoSellContext<'a> {
    pub feature_id: &'a str,
    pub held_bp: u64,
    pub purchase_cost_units: u64,
    pub market_price_units: u64,
    pub depletion: &'a DepletionStatus,
    pub base_borrow_units: u64,
}

/// Evaluate whether a held position should be listed for sale.
///
/// Returns `Ok(sell_bp)` if it qualifies, `Err(reason)` otherwise.
/// Does NOT create any listing — caller performs the §62z-gated `list_for_sale`.
pub fn evaluate_auto_sell_position(
    cfg: &AutoSellConfig,
    ctx: &AutoSellContext<'_>,
) -> Result<u64, String> {
    if ctx.held_bp < cfg.min_hold_bp_to_trigger {
        return Err(format!(
            "hold {} < min_hold_bp {}",
            ctx.held_bp, cfg.min_hold_bp_to_trigger
        ));
    }
    let depletion_triggered = (ctx.depletion.state == DepletionState::NearDepleted
        && cfg.sell_on_near_depleted)
        || (ctx.depletion.state == DepletionState::Slowing && cfg.sell_on_slowing);

    let threshold = if ctx.purchase_cost_units > 0 {
        (ctx.purchase_cost_units as f64 * cfg.min_return_multiplier) as u64
    } else {
        ctx.base_borrow_units
    };

    if !depletion_triggered && ctx.market_price_units < threshold {
        return Err(format!(
            "market {} < threshold {}",
            ctx.market_price_units, threshold
        ));
    }

    // §62z: spend/transfer — list_for_sale creates an EQUITY_LISTING that
    // triggers UCR transfer on fill; REQUIRES authority gate before wiring.

    let sell_bp = ctx.held_bp.min(cfg.bp_to_sell_per_trigger);
    Ok(sell_bp)
}

// ---------------------------------------------------------------------------
// Timestamp helper
// ---------------------------------------------------------------------------

fn now_iso() -> String {
    OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_else(|_| "1970-01-01T00:00:00Z".to_owned())
}

pub fn now_unix() -> i64 {
    OffsetDateTime::now_utc().unix_timestamp()
}

/// Generate a listing_id from current time and a seller prefix.
pub fn new_listing_id(seller_id: &str) -> String {
    format!(
        "elst-{}-{}",
        OffsetDateTime::now_utc().unix_timestamp_nanos() / 1_000_000,
        &seller_id[..seller_id.len().min(8)]
    )
}

/// Build an EQUITY_LISTING audit row value.
pub fn build_listing_row(lst: &EquityListing) -> serde_json::Value {
    serde_json::json!({
        "kind": "EQUITY_LISTING",
        "listing_id": lst.listing_id,
        "feature_id": lst.feature_id,
        "seller_id": lst.seller_id,
        "basis_points": lst.basis_points,
        "ask_price_units": lst.ask_price_units,
        "expires_at_unix": lst.expires_at_unix,
        "at_unix": lst.at_unix,
        "at": lst.at,
    })
}

/// Build an EQUITY_LISTING_FILLED audit row value.
pub fn build_fill_row(listing: &EquityListing, buyer_id: &str, at_unix: i64) -> serde_json::Value {
    serde_json::json!({
        "kind": "EQUITY_LISTING_FILLED",
        "listing_id": listing.listing_id,
        "feature_id": listing.feature_id,
        "seller_id": listing.seller_id,
        "buyer_id": buyer_id,
        "basis_points": listing.basis_points,
        "price_units": listing.ask_price_units,
        "at_unix": at_unix,
        "at": now_iso(),
    })
}

/// Build an EQUITY_LISTING_CANCELLED audit row value.
pub fn build_cancel_row(listing_id: &str, seller_id: &str, at_unix: i64) -> serde_json::Value {
    serde_json::json!({
        "kind": "EQUITY_LISTING_CANCELLED",
        "listing_id": listing_id,
        "seller_id": seller_id,
        "at_unix": at_unix,
        "at": now_iso(),
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn supply_pressure_decreases_with_spend() {
        let p0 = supply_pressure(0, 100);
        let p1 = supply_pressure(UNIT, 100);
        assert!(p0 > p1, "pressure should decrease as spend increases");
        assert!((p0 - 1.0).abs() < 1e-9, "zero spend = 1.0");
    }

    #[test]
    fn depletion_healthy_low_adoption() {
        let dep = feature_depletion_status(
            "feat-1",
            &DepletionInput {
                adopter_peer_ids: &["a".to_owned(), "b".to_owned()],
                total_feature_spend_units: 0,
                estimated_network_size: 100,
            },
        );
        assert_eq!(dep.state, DepletionState::Healthy);
        assert!(dep.listable);
    }

    #[test]
    fn depletion_depleted_high_adoption() {
        let peers: Vec<String> = (0..97).map(|i| format!("p{}", i)).collect();
        let dep = feature_depletion_status(
            "feat-2",
            &DepletionInput {
                adopter_peer_ids: &peers,
                total_feature_spend_units: 0,
                estimated_network_size: 100,
            },
        );
        assert_eq!(dep.state, DepletionState::Depleted);
        assert!(!dep.listable);
    }

    #[test]
    fn auto_buy_gate_own_listing_skipped() {
        let listing = EquityListing {
            listing_id: "l1".to_owned(),
            feature_id: "f1".to_owned(),
            seller_id: "alice".to_owned(),
            basis_points: 1_000,
            ask_price_units: 100,
            expires_at_unix: i64::MAX,
            at_unix: 0,
            at: "2026-01-01T00:00:00Z".to_owned(),
        };
        let dep = DepletionStatus {
            feature_id: "f1".to_owned(),
            state: DepletionState::Healthy,
            listable: true,
            adoption_rate: 0.1,
            adoption_count: 10,
            estimated_network_size: 100,
            supply_pressure: 0.9,
            remaining_adopters: 90,
            estimated_remaining_revenue_per_bp_units: 1_000,
            notes: String::new(),
        };
        let ctx = AutoBuyContext {
            listing: &listing,
            quality_wilson: 0.9,
            adoption_count: 10,
            depletion: &dep,
            lucrativity_score: 0.5,
            buyer_current_bp: 0,
            base_borrow_units: 100,
        };
        let cfg = AutoBuyConfig {
            enabled: true,
            ..Default::default()
        };
        let result = evaluate_auto_buy_listing(&cfg, "alice", &ctx, 0);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "own_listing");
    }

    #[test]
    fn auto_sell_below_min_hold_skipped() {
        let dep = DepletionStatus {
            feature_id: "f2".to_owned(),
            state: DepletionState::Healthy,
            listable: true,
            adoption_rate: 0.1,
            adoption_count: 5,
            estimated_network_size: 50,
            supply_pressure: 0.8,
            remaining_adopters: 45,
            estimated_remaining_revenue_per_bp_units: 500,
            notes: String::new(),
        };
        let ctx = AutoSellContext {
            feature_id: "f2",
            held_bp: 100,
            purchase_cost_units: 50,
            market_price_units: 200,
            depletion: &dep,
            base_borrow_units: 100,
        };
        let cfg = AutoSellConfig {
            enabled: true,
            min_hold_bp_to_trigger: 500,
            ..Default::default()
        };
        let result = evaluate_auto_sell_position(&cfg, &ctx);
        assert!(result.is_err());
    }

    #[test]
    fn wash_trade_detection() {
        let rows = vec![
            serde_json::json!({
                "kind": "EQUITY_LISTING_FILLED",
                "buyer_id": "alice",
                "feature_id": "f3",
                "at_unix": 1_000_000i64,
            }),
            serde_json::json!({
                "kind": "EQUITY_LISTING",
                "seller_id": "alice",
                "feature_id": "f3",
                "at_unix": 1_000_100i64,
            }),
        ];
        let result = check_wash_trading(&rows, "alice", "f3", 1_000_200);
        assert!(result.is_err());
    }
}
