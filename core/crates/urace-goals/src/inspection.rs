//! `inspection` — vitals/scoring engine ported from Python `inspection.py`.
//!
//! Provides goal scoring, eligibility gating (§2571 Capability Envelope Gate,
//! §74 self-evolution policy), vitals snapshots, and render helpers for the
//! CLI and web UI.
//!
//! All `state` / `config` parameters are `serde_json::Value` maps (matching
//! the Python dicts).  Functions that read time compare against
//! `chrono::Utc::now()` so the behaviour is identical to the Python code.

use std::collections::HashMap;

use regex_lite::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

// ── tiny helpers ──────────────────────────────────────────────────────────────

/// Return `Utc::now()` as an ISO-8601 string (matches Python `now()`).
fn now_iso() -> String {
    // We use a hand-rolled formatter so we don't need the `chrono` feature flag.
    // The result is e.g. "2026-11-24T14:00:00.000000+00:00".
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format as a simple UTC ISO string — good enough for the render helpers.
    let (y, mo, d, h, mi, s) = epoch_to_parts(secs);
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+00:00", y, mo, d, h, mi, s)
}

fn epoch_to_parts(mut secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60; secs /= 60;
    let mi = secs % 60; secs /= 60;
    let h = secs % 24; secs /= 24;
    // days since 1970-01-01
    let (y, mo, d) = days_to_ymd(secs);
    (y, mo, d, h, mi, s)
}

fn days_to_ymd(mut days: u64) -> (u64, u64, u64) {
    // Gregorian calendar — basic implementation.
    let mut year = 1970u64;
    loop {
        let leap = is_leap(year);
        let dy = if leap { 366 } else { 365 };
        if days < dy { break; }
        days -= dy;
        year += 1;
    }
    let leap = is_leap(year);
    let month_days: [u64; 12] = [31,
        if leap { 29 } else { 28 },
        31,30,31,30,31,31,30,31,30,31];
    let mut month = 1u64;
    for &md in &month_days {
        if days < md { break; }
        days -= md;
        month += 1;
    }
    (year, month, days + 1)
}

fn is_leap(y: u64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

/// Parse an ISO-8601 string to a Unix timestamp (seconds).
/// Returns `None` if the string cannot be parsed.
fn parse_iso(s: &str) -> Option<f64> {
    // We use a simple hand-rolled parser for the common formats produced by
    // Python's datetime.isoformat().  Supported:
    //   "2026-11-24T14:00:00+00:00"
    //   "2026-11-24T14:00:00.123456+00:00"
    //   "2026-11-24T14:00:00Z"
    //   "2026-11-24T14:00:00"  (assumed UTC)
    let s = s.trim();
    if s.len() < 19 { return None; }
    let (date_part, rest) = s.split_at(10);
    let time_part = rest.trim_start_matches('T');
    // Strip offset
    let (time_core, offset_secs) = if let Some(pos) = time_part.rfind('+') {
        let (tc, off) = time_part.split_at(pos);
        let off_secs = parse_offset(off).unwrap_or(0);
        (tc, off_secs)
    } else if let Some(pos) = time_part.rfind('-') {
        // Could be a negative offset
        let (tc, off) = time_part.split_at(pos);
        let off_secs = -parse_offset(off).unwrap_or(0);
        (tc, off_secs)
    } else {
        (time_part.trim_end_matches('Z'), 0i64)
    };
    // Parse date
    let dp: Vec<&str> = date_part.splitn(3, '-').collect();
    if dp.len() != 3 { return None; }
    let y: u64 = dp[0].parse().ok()?;
    let mo: u64 = dp[1].parse().ok()?;
    let d: u64 = dp[2].parse().ok()?;
    // Parse time
    let tp: Vec<&str> = time_core.splitn(3, ':').collect();
    if tp.len() < 2 { return None; }
    let h: u64 = tp[0].parse().ok()?;
    let mi: u64 = tp[1].parse().ok()?;
    let (whole_s, frac_s) = if tp.len() == 3 {
        let raw = tp[2];
        if let Some(dot) = raw.find('.') {
            let (w, f) = raw.split_at(dot);
            (w.parse::<u64>().ok()?, format!("0{}", f).parse::<f64>().ok()?)
        } else {
            (raw.parse::<u64>().ok()?, 0.0)
        }
    } else {
        (0, 0.0)
    };
    // Days since epoch
    let days = ymd_to_days(y, mo, d)?;
    let secs = days * 86400 + h * 3600 + mi * 60 + whole_s;
    Some(secs as f64 + frac_s - offset_secs as f64)
}

fn parse_offset(s: &str) -> Option<i64> {
    // "+HH:MM" or "-HH:MM"
    let s = s.trim_start_matches('+').trim_start_matches('-');
    let parts: Vec<&str> = s.splitn(2, ':').collect();
    if parts.len() == 2 {
        let h: i64 = parts[0].parse().ok()?;
        let m: i64 = parts[1].parse().ok()?;
        Some(h * 3600 + m * 60)
    } else {
        None
    }
}

fn ymd_to_days(y: u64, mo: u64, d: u64) -> Option<u64> {
    if mo < 1 || mo > 12 || d < 1 { return None; }
    let mut days: u64 = 0;
    for yr in 1970..y {
        days += if is_leap(yr) { 366 } else { 365 };
    }
    let leap = is_leap(y);
    let month_days: [u64; 12] = [31,
        if leap { 29 } else { 28 },
        31,30,31,30,31,30,31,31,30,31,30,31][..12].try_into().ok()?;
    for m in 1..mo {
        days += month_days[(m - 1) as usize];
    }
    days += d - 1;
    Some(days)
}

fn now_ts() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

// ── document_metrics ──────────────────────────────────────────────────────────

/// Count normative rules, behavioural tests, and unresolved markers in product
/// files listed in `config["product_files"]`.
pub fn document_metrics(config: &Value) -> HashMap<String, f64> {
    let empty = vec![];
    let files = config["product_files"].as_array().unwrap_or(&empty);
    let mut combined = String::new();
    for f in files {
        if let Some(path) = f.as_str() {
            if let Ok(text) = std::fs::read_to_string(path) {
                combined.push('\n');
                combined.push_str(&text);
            }
        }
    }

    let normative = Regex::new(r"\bMUST(?: NOT)?\b").unwrap()
        .find_iter(&combined).count();
    let tests = Regex::new(r"(?m)^\*\*[A-Z]{1,2} —").unwrap()
        .find_iter(&combined).count();
    let todos = Regex::new(r"(?i)\b(?:TODO|TBD|FIXME)\b").unwrap()
        .find_iter(&combined).count();

    let mut m = HashMap::new();
    m.insert("normative_rules".into(), normative as f64);
    m.insert("behavioral_tests".into(), tests as f64);
    m.insert("unresolved_markers".into(), todos as f64);
    m
}

// ── compare ───────────────────────────────────────────────────────────────────

/// Return `"stable"`, `"improved"`, or `"regressed"`.
///
/// `direction` is `"nondecreasing"` or anything else (treated as decreasing).
pub fn compare(direction: &str, current: f64, reference: f64) -> &'static str {
    let delta = current - reference;
    if delta == 0.0 {
        return "stable";
    }
    let improved = if direction == "nondecreasing" { delta > 0.0 } else { delta < 0.0 };
    if improved { "improved" } else { "regressed" }
}

// ── §2571 Capability Envelope Gate ───────────────────────────────────────────

fn has_capability_expansion_authority(state: &Value, objective: &Value) -> bool {
    let obj_id = objective["id"].as_str().unwrap_or("");
    let obj_title = objective["title"].as_str().unwrap_or("");
    let empty = vec![];
    let drs = state["decision_records"].as_array().unwrap_or(&empty);
    for dr in drs {
        if dr["kind"].as_str() != Some("AUTHORITY_GRANT") {
            continue;
        }
        let authorized = dr["authorized_objective_ids"].as_array().unwrap_or(&empty);
        if !obj_id.is_empty() && authorized.iter().any(|v| v.as_str() == Some(obj_id)) {
            return true;
        }
        let subj = dr["subject"].as_str().unwrap_or("");
        if !obj_id.is_empty() && subj.contains(obj_id) {
            return true;
        }
        if !obj_title.is_empty() && subj.contains(obj_title) {
            return true;
        }
        if dr["capability_expansion_authorized"].as_bool().unwrap_or(false) {
            return true;
        }
    }
    false
}

/// Record an integrity gap when a CAPABILITY_DEFINING objective lacks authority
/// (§2571).  Pure side-effect — separated from `objective_is_eligible` so that
/// function remains a query.
pub fn emit_capability_envelope_gap(state: &mut Value, objective: &Value) {
    let objective_id = objective["id"].as_str().unwrap_or("unknown");
    let base_id = format!("igap-cap-envelope-{}", objective_id);

    let maturity: Option<String> = state["sweet_spot_assessments"]
        .as_array()
        .and_then(|a| a.last())
        .and_then(|last| last["maturity_level"].as_str())
        .map(|s| s.to_string());

    let gaps = state["integrity_gaps"]
        .as_array()
        .cloned()
        .unwrap_or_default();

    let existing_ids: std::collections::HashSet<String> = gaps
        .iter()
        .filter_map(|g| g["id"].as_str().map(|s| s.to_string()))
        .collect();

    let mut gap_id = base_id.clone();
    let mut recurrence = 1usize;
    while existing_ids.contains(&gap_id) {
        recurrence += 1;
        gap_id = format!("{}-{}", base_id, recurrence);
    }

    let detail = format!(
        "CAPABILITY_DEFINING objective '{}' requires explicit DecisionRecord(kind=AUTHORITY_GRANT) at {} maturity",
        objective["title"].as_str().unwrap_or(""),
        maturity.as_deref().unwrap_or("unknown")
    );

    let new_gap = json!({
        "id": gap_id,
        "objective": objective_id,
        "kind": "capability-envelope-breach",
        "severity": "WARNING",
        "detail": detail,
        "at": now_iso(),
        "resolved": false,
    });

    let mut updated_gaps = gaps;
    updated_gaps.push(new_gap);
    state["integrity_gaps"] = Value::Array(updated_gaps);
}

// ── objective_is_eligible ─────────────────────────────────────────────────────

/// Return `true` if `objective` passes all eligibility gates.
///
/// May mutate `state` to record an integrity gap (§2571).
pub fn objective_is_eligible(state: &mut Value, objective: &Value) -> bool {
    // §2571 Capability Envelope Gate
    if objective["kind"].as_str() == Some("CAPABILITY_DEFINING") {
        let maturity: Option<String> = state["sweet_spot_assessments"]
            .as_array()
            .and_then(|a| a.last())
            .and_then(|last| last["maturity_level"].as_str())
            .map(|s| s.to_string());
        if matches!(maturity.as_deref(), Some("CAPABLE") | Some("OPTIMIZED")) {
            if !has_capability_expansion_authority(state, objective) {
                let obj_id = objective["id"].as_str().unwrap_or("unknown").to_string();
                let base_id = format!("igap-cap-envelope-{}", obj_id);
                let empty = vec![];
                let gaps = state["integrity_gaps"].as_array().unwrap_or(&empty).clone();
                let already_recorded = gaps.iter().any(|g| {
                    !g["resolved"].as_bool().unwrap_or(false)
                        && g["kind"].as_str() == Some("capability-envelope-breach")
                        && (g["objective"].as_str() == Some(&obj_id)
                            || g["id"].as_str() == Some(&base_id))
                });
                if !already_recorded {
                    let obj_clone = objective.clone();
                    emit_capability_envelope_gap(state, &obj_clone);
                }
                return false;
            }
        }
    }

    // Non-runtime scopes are always eligible.
    let scope = objective["scope"].as_str().unwrap_or("");
    if scope != "runtime" && scope != "rebootstrap" {
        return true;
    }

    // §74: NECESSARY_ONLY is the default; DISABLED must be explicit.
    let mode = state["self_evolution_policy"]["mode"]
        .as_str()
        .unwrap_or("NECESSARY_ONLY")
        .to_uppercase();
    if mode == "CONTINUOUS" {
        return true;
    }
    if mode == "NECESSARY_ONLY" {
        let necessity = objective["necessity_evidence"].as_str().unwrap_or("").trim().to_string();
        let lower_impact = objective["lower_impact_route_sufficient"]
            .as_bool()
            .unwrap_or(true);
        return !necessity.is_empty() && !lower_impact;
    }
    false
}

// ── goal_is_schedulable ───────────────────────────────────────────────────────

/// Return `true` if `objective` can be scheduled now.
pub fn goal_is_schedulable(state: &mut Value, objective: &Value) -> bool {
    let status = objective["status"].as_str().unwrap_or("");
    if !matches!(status, "planned" | "policy_blocked" | "needs_reassessment" | "deferred_budget") {
        return false;
    }
    if let Some(not_before) = objective["not_before"].as_str() {
        match parse_iso(not_before) {
            Some(ts) if ts > now_ts() => return false,
            None => return false,
            _ => {}
        }
    }
    // Check dependencies
    let empty_arr = vec![];
    let objectives_arr = state["objectives"].as_array().cloned().unwrap_or_default();
    let by_id: HashMap<String, Value> = objectives_arr
        .iter()
        .filter_map(|o| o["id"].as_str().map(|id| (id.to_string(), o.clone())))
        .collect();
    let deps = objective["dependencies"].as_array().unwrap_or(&empty_arr);
    for dep in deps {
        if let Some(dep_id) = dep.as_str() {
            if by_id.get(dep_id).and_then(|o| o["status"].as_str()) != Some("completed") {
                return false;
            }
        }
    }
    objective_is_eligible(state, objective)
}

// ── objective_score ───────────────────────────────────────────────────────────

/// Compute the total priority score for an objective.
pub fn objective_score(objective: &Value) -> f64 {
    objective_score_breakdown(objective)
        .get("total")
        .copied()
        .unwrap_or(0.0)
}

/// Compute priority score components and their sum as `"total"`.
pub fn objective_score_breakdown(objective: &Value) -> HashMap<String, f64> {
    let mut declared = objective["priority"].as_f64().unwrap_or(50.0);
    if let Some(floor) = objective["priority_floor"].as_f64() {
        declared = declared.max(floor);
    }
    if let Some(ceil) = objective["priority_ceiling"].as_f64() {
        declared = declared.min(ceil);
    }

    // Deadline pressure (0..15)
    let deadline_pressure = if let Some(dl) = objective["deadline"].as_str() {
        parse_iso(dl).map(|dl_ts| {
            let days = (dl_ts - now_ts()) / 86400.0;
            if days <= 0.0 {
                15.0
            } else {
                (15.0 * (1.0 - (days.min(30.0) / 30.0))).max(0.0)
            }
        }).unwrap_or(0.0)
    } else {
        0.0
    };

    // Starvation correction (0..5)
    let waiting_age = if let Some(created) = objective["created_at"].as_str() {
        parse_iso(created).map(|ts| {
            let days = ((now_ts() - ts) / 86400.0).max(0.0);
            (days / 30.0).min(5.0)
        }).unwrap_or(0.0)
    } else {
        0.0
    };

    let mut components = HashMap::new();
    components.insert("priority".into(), declared);
    components.insert(
        "pinned_attention".into(),
        if objective["pinned"].as_bool().unwrap_or(false) { 20.0 } else { 0.0 },
    );
    components.insert(
        "expected_value".into(),
        20.0 * objective["expected_value"].as_f64().unwrap_or(0.5),
    );
    components.insert(
        "urgency".into(),
        10.0 * objective["urgency"].as_f64().unwrap_or(0.5),
    );
    components.insert("deadline_pressure".into(), deadline_pressure);
    components.insert(
        "dependency_unblocking".into(),
        objective["dependency_unblocking_adjustment"].as_f64().unwrap_or(0.0),
    );
    components.insert("starvation_correction".into(), waiting_age);
    components.insert(
        "confidence".into(),
        5.0 * objective["confidence"].as_f64().unwrap_or(0.5),
    );
    components.insert(
        "estimated_cost_penalty".into(),
        -10.0 * objective["estimated_cost"].as_f64().unwrap_or(0.5),
    );
    components.insert(
        "risk_penalty".into(),
        -10.0 * objective["risk"].as_f64().unwrap_or(0.5),
    );
    components.insert(
        "scope_attention".into(),
        objective["scope_attention_adjustment"].as_f64().unwrap_or(0.0),
    );
    components.insert(
        "feedback_adjustment".into(),
        objective["feedback_priority_adjustment"].as_f64().unwrap_or(0.0),
    );

    let total: f64 = components.values().sum();
    components.insert("total".into(), total);
    components
}

// ── goal_portfolio ────────────────────────────────────────────────────────────

/// Build an advisory, explainable forecast over all objectives.
pub fn goal_portfolio(state: &Value) -> Value {
    let mut state_mut = state.clone();
    let empty_arr = vec![];
    let objectives_raw = state["objectives"].as_array().unwrap_or(&empty_arr).clone();

    // Compute dependency-unblocking adjustments.
    let mut dep_counts: HashMap<String, usize> = objectives_raw
        .iter()
        .filter_map(|o| o["id"].as_str().map(|id| (id.to_string(), 0)))
        .collect();
    for obj in &objectives_raw {
        for dep in obj["dependencies"].as_array().unwrap_or(&empty_arr) {
            if let Some(dep_id) = dep.as_str() {
                if let Some(c) = dep_counts.get_mut(dep_id) {
                    *c += 1;
                }
            }
        }
    }

    let mut objectives: Vec<Value> = objectives_raw
        .into_iter()
        .map(|mut o| {
            if let Some(id) = o["id"].as_str() {
                let adj = (2.0 * dep_counts.get(id).copied().unwrap_or(0) as f64).min(10.0);
                o["dependency_unblocking_adjustment"] = json!(adj);
            }
            o
        })
        .collect();

    // Sort by (schedulable, score) descending.
    objectives.sort_by(|a, b| {
        let sa = goal_is_schedulable(&mut state_mut, a) as u8;
        let sb = goal_is_schedulable(&mut state_mut, b) as u8;
        let score_a = objective_score(a);
        let score_b = objective_score(b);
        sb.cmp(&sa).then_with(|| score_b.partial_cmp(&score_a).unwrap_or(std::cmp::Ordering::Equal))
    });

    let now_ts_val = now_ts();
    let mut cursor_min = now_ts_val;
    let mut cursor_max = now_ts_val;

    let by_id: HashMap<String, Value> = objectives
        .iter()
        .filter_map(|o| o["id"].as_str().map(|id| (id.to_string(), o.clone())))
        .collect();

    let mut rows = vec![];
    for (rank, goal) in objectives.iter().enumerate() {
        let deps: Vec<Value> = goal["dependencies"]
            .as_array()
            .unwrap_or(&empty_arr)
            .clone();
        let blockers: Vec<Value> = deps
            .iter()
            .filter(|dep| {
                dep.as_str()
                    .and_then(|id| by_id.get(id))
                    .and_then(|o| o["status"].as_str())
                    != Some("completed")
            })
            .cloned()
            .collect();

        let eligible = goal_is_schedulable(&mut state_mut, goal);

        // Estimate hours.
        let est = &goal["estimate"];
        let mut low = est["min_hours"].as_f64().unwrap_or(0.0).max(0.0);
        let mut high = est["max_hours"].as_f64().unwrap_or(low).max(low);
        let mut confidence = goal["estimate_confidence"].as_str().unwrap_or("low").to_string();
        let mut estimate_basis = "declared".to_string();

        if high == 0.0 {
            // Try historical completed goals.
            let mut comparable: Vec<f64> = objectives
                .iter()
                .filter_map(|prior| {
                    if prior["status"].as_str() != Some("completed")
                        || prior["scope"] != goal["scope"]
                    {
                        return None;
                    }
                    let created_ts = parse_iso(prior["created_at"].as_str()?)?;
                    let completed_ts = parse_iso(prior["completed_at"].as_str()?)?;
                    Some(((completed_ts - created_ts) / 3600.0).max(0.0))
                })
                .collect();
            if !comparable.is_empty() {
                comparable.sort_by(|a, b| a.partial_cmp(b).unwrap());
                let nominal = comparable[comparable.len() / 2];
                confidence = "medium".into();
                estimate_basis = "historical completed goals".into();
                low = nominal * 0.5;
                high = nominal * 1.5;
            } else {
                let nominal = (8.0 * goal["estimated_cost"].as_f64().unwrap_or(0.5)).max(0.25);
                estimate_basis = "estimated-cost proxy".into();
                low = nominal * 0.5;
                high = nominal * 1.5;
            }
        }

        let (earliest, latest) = if eligible && high > 0.0 {
            cursor_min += low * 3600.0;
            cursor_max += high * 3600.0;
            let e = {
                let (y, mo, d, h, mi, s) = epoch_to_parts(cursor_min as u64);
                format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+00:00", y, mo, d, h, mi, s)
            };
            let l = {
                let (y, mo, d, h, mi, s) = epoch_to_parts(cursor_max as u64);
                format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+00:00", y, mo, d, h, mi, s)
            };
            (Value::String(e), Value::String(l))
        } else {
            (Value::Null, Value::Null)
        };

        let mut reasons = vec![];
        if goal["pinned"].as_bool().unwrap_or(false) {
            reasons.push("pinned attention".to_string());
        }
        if let Some(dl) = goal["deadline"].as_str() {
            reasons.push(format!("deadline {}", dl));
        }
        if !blockers.is_empty() {
            let ids: Vec<&str> = blockers.iter().filter_map(|b| b.as_str()).collect();
            reasons.push(format!("waiting for {}", ids.join(", ")));
        }
        if let Some(nb) = goal["not_before"].as_str() {
            reasons.push(format!("deferred until {}", nb));
        }
        reasons.push("value, urgency, confidence, cost, risk and scope evidence".into());

        rows.push(json!({
            "rank": rank + 1,
            "id": goal["id"],
            "title": goal["title"],
            "status": goal["status"],
            "eligible": eligible,
            "score": objective_score(goal),
            "score_breakdown": objective_score_breakdown(goal).into_iter()
                .map(|(k, v)| (k, json!(v)))
                .collect::<serde_json::Map<_, _>>(),
            "dependencies": deps,
            "blockers": blockers,
            "estimate": {
                "min_hours": low,
                "max_hours": high,
                "confidence": confidence,
                "basis": estimate_basis,
            },
            "forecast": {
                "earliest": earliest,
                "latest": latest,
                "advisory": true,
            },
            "priority_reason": reasons.join("; "),
        }));
    }

    json!({
        "generated_at": now_iso(),
        "basis": "advisory sequential capacity; recalculated at lifecycle boundaries",
        "goals": rows,
        // These fields exist in Python but depend on sub-modules not ported here;
        // we provide empty placeholders so callers can still round-trip the shape.
        "implementation_sequence": [],
        "request_claim_trace": [],
        "uncertainty_followups": [],
    })
}

// ── work_evaluations ──────────────────────────────────────────────────────────

/// Return per-goal and per-context work attribution data.
pub fn work_evaluations(state: &Value) -> Value {
    let empty_arr = vec![];
    let calls = state["executor_state"]["executor_calls"]
        .as_array()
        .unwrap_or(&empty_arr)
        .clone();
    let operations = state["operations"].as_array().unwrap_or(&empty_arr);
    let objectives = state["objectives"].as_array().unwrap_or(&empty_arr);

    let goals: Vec<Value> = objectives
        .iter()
        .rev()
        .take(100)
        .rev()
        .map(|obj| {
            let obj_id = obj["id"].as_str().unwrap_or("");
            let related: Vec<&Value> = calls
                .iter()
                .filter(|c| {
                    c["reason"].as_str() == Some(obj_id)
                        || c["objective_id"].as_str() == Some(obj_id)
                })
                .collect();
            let accepted = related.iter().filter(|c| c["outcome"].as_str() == Some("accepted")).count();
            let improved: i64 = related.iter().map(|c| c["observed_metric_effect"]["improved"].as_i64().unwrap_or(0)).sum();
            let regressed: i64 = related.iter().map(|c| c["observed_metric_effect"]["regressed"].as_i64().unwrap_or(0)).sum();
            json!({
                "id": obj["id"],
                "title": obj["title"],
                "target": obj.get("target").cloned().unwrap_or_else(|| json!("product")),
                "scope": obj["scope"],
                "status": obj["status"],
                "outcome_status": obj.get("outcome_status").cloned().unwrap_or_else(|| json!("UNVERIFIED")),
                "score": objective_score(obj),
                "score_breakdown": objective_score_breakdown(obj).into_iter()
                    .map(|(k, v)| (k, json!(v)))
                    .collect::<serde_json::Map<_, _>>(),
                "model_calls": related.len(),
                "accepted_changes": accepted,
                "metric_effect": { "improved": improved, "regressed": regressed },
                "attribution": "UNATTRIBUTED_COST_OUTCOME_ASSOCIATION",
            })
        })
        .collect();

    let context_inputs = state["context_inputs"].as_array().unwrap_or(&empty_arr);
    let contexts: Vec<Value> = context_inputs
        .iter()
        .rev()
        .take(100)
        .rev()
        .map(|ctx| {
            let ctx_id = ctx["id"].as_str().unwrap_or("");
            let related: Vec<&Value> = calls
                .iter()
                .filter(|c| c["trigger_signature"].as_str() == Some(ctx_id))
                .collect();
            let outcomes: Vec<&Value> = related.iter().map(|c| &c["outcome"]).collect();
            json!({
                "id": ctx["id"],
                "source": ctx["source"],
                "discovery_calls": related.len(),
                "outcomes": outcomes,
                "attribution": "UNATTRIBUTED_INPUT_OUTCOME_ASSOCIATION",
            })
        })
        .collect();

    let mut action_groups: serde_json::Map<String, Value> = serde_json::Map::new();
    for op in operations.iter().rev().take(100).rev() {
        let scope = op["scope"].as_str().unwrap_or("unknown");
        let group = if scope == "runtime" || scope == "rebootstrap" {
            "urace_self_evolution"
        } else {
            "product_evolution"
        };
        let entry = action_groups.entry(group.to_string()).or_insert_with(|| {
            json!({"attempted": 0, "accepted": 0, "rejected_or_no_effect": 0})
        });
        entry["attempted"] = json!(entry["attempted"].as_i64().unwrap_or(0) + 1);
        match op["status"].as_str() {
            Some("ACCEPTED") => {
                entry["accepted"] = json!(entry["accepted"].as_i64().unwrap_or(0) + 1);
            }
            Some("REJECTED_ROLLED_BACK") | Some("OBSERVED_NO_EFFECT") => {
                entry["rejected_or_no_effect"] =
                    json!(entry["rejected_or_no_effect"].as_i64().unwrap_or(0) + 1);
            }
            _ => {}
        }
    }

    json!({
        "goals": goals,
        "contexts": contexts,
        "actions": action_groups,
        "attribution": "ASSOCIATIONS_REQUIRE_CAUSAL_REVIEW",
    })
}

// ── context_view ──────────────────────────────────────────────────────────────

/// Return governing intent/authority/constraints plus user-supplied and
/// URACE-derived context.
pub fn context_view(state: &Value) -> Value {
    let empty_arr = vec![];
    let context_inputs = state["context_inputs"].as_array().unwrap_or(&empty_arr);
    let user_supplied: Vec<Value> = context_inputs
        .iter()
        .map(|item| {
            let mut m = item.as_object().cloned().unwrap_or_default();
            m.entry("origin".to_string()).or_insert_with(|| json!("USER_SUPPLIED"));
            Value::Object(m)
        })
        .collect();

    let reasoning = state["reasoning_memory"].as_array().unwrap_or(&empty_arr);
    let external_obs = state["external_metric_state"]["latest"].as_array().unwrap_or(&empty_arr);
    let objectives = state["objectives"].as_array().unwrap_or(&empty_arr);

    json!({
        "governing": {
            "intent": state["intent"],
            "authority": state["authority"],
            "constraints": state.get("constraints").cloned().unwrap_or_else(|| json!([])),
        },
        "user_supplied": user_supplied,
        "urace_derived": {
            "objectives": objectives.iter().rev().take(100).rev().cloned().collect::<Vec<_>>(),
            "reasoning_hypotheses": reasoning.iter().rev().take(100).rev().cloned().collect::<Vec<_>>(),
            "external_observations": external_obs.iter().rev().take(100).rev().cloned().collect::<Vec<_>>(),
        },
        "provenance_note": "Derived context is Evidence or a hypothesis; it does not replace user Intent or create Authority.",
    })
}

// ── resource_accounting ───────────────────────────────────────────────────────

/// Return the full resource accounting view.
pub fn resource_accounting(config: &Value, state: &Value) -> Value {
    let empty_arr = vec![];
    let executor = &state["executor_state"];
    let calls = executor["executor_calls"].as_array().unwrap_or(&empty_arr);
    let limits = &config["executor"];
    let current = now_ts();

    let recent_24h = calls
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < 86400.0))
        .count();
    let recent_30d = calls
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < 2592000.0))
        .count();

    let runtime = &state["runtime_efficiency"];
    let probe_count = runtime["availability_probes"].as_u64().unwrap_or(0) as usize;
    let readiness_transitions = state["evidence"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .filter(|e| e["kind"].as_str() == Some("executor-availability"))
        .count();

    let context_links: std::collections::HashSet<String> = calls
        .iter()
        .filter_map(|c| c["trigger_signature"].as_str().map(|s| s.to_string()))
        .collect();
    let unused_context = state["context_inputs"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .filter(|item| {
            item["id"]
                .as_str()
                .map_or(true, |id| !context_links.contains(id))
        })
        .count();

    let open_statuses = ["planned", "policy_blocked", "deferred_budget", "needs_reassessment"];
    let stale_goals = state["objectives"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .filter(|obj| {
            open_statuses.contains(&obj["status"].as_str().unwrap_or(""))
                && obj["created_at"]
                    .as_str()
                    .and_then(parse_iso)
                    .map_or(false, |ts| current - ts >= 2592000.0)
        })
        .count();

    let unproductive = calls
        .iter()
        .filter(|c| {
            matches!(
                c["outcome"].as_str(),
                Some("failed") | Some("no_action") | Some("ineligible") | Some("no_effect") | Some("concurrent_change")
            )
        })
        .count();

    let streak = executor["unproductive_discovery_streak"].as_u64().unwrap_or(0) as usize;
    let exhausted_threshold = limits["discovery_yield_exhausted_threshold"]
        .as_u64()
        .unwrap_or(5) as usize;
    let discovery_exhausted = streak >= exhausted_threshold;

    let productive_30d = calls
        .iter()
        .filter(|c| {
            c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < 2592000.0)
                && matches!(c["outcome"].as_str(), Some("objective_created") | Some("accepted"))
        })
        .count();
    let discovery_yield_30d: Option<f64> = if !calls.is_empty() {
        Some(productive_30d as f64 / calls.len() as f64)
    } else {
        None
    };

    let executor_failures: usize = executor["failures"].as_array().map_or(0, |a| a.len());
    let systematic_active = executor["systematic_failure_cooldown_until"]
        .as_str()
        .and_then(parse_iso)
        .map_or(false, |ts| ts > current);
    let external_failure_streak = state["external_metric_state"]["failure_streak"]
        .as_i64()
        .unwrap_or(0);

    let sinks = json!({
        "unproductive_model_calls": unproductive,
        "unused_context_inputs": unused_context,
        "stale_open_goals_30d": stale_goals,
        "executor_failures": executor_failures,
        "systematic_failure_active": systematic_active,
        "external_failure_streak": external_failure_streak,
    });
    let review_required = unproductive > 0
        || unused_context > 0
        || stale_goals > 0
        || executor_failures > 0
        || systematic_active
        || external_failure_streak != 0;

    let discovery_loop_sink = {
        let mut d = json!({
            "unproductive_streak": streak,
            "exhausted_threshold": exhausted_threshold,
            "confirmed_active_sink": discovery_exhausted,
            "productive_yield_30d": discovery_yield_30d,
            "ceiling_interval_seconds": limits["max_discovery_interval_seconds"].as_f64().unwrap_or(4838400.0),
            "defer_reason": executor["discovery_defer_reason"],
            "qualifying_reset_conditions": ["new inbox input applied", "net-new evidence record", "intent or product-file change", "operator force-discovery"],
        });
        d
    };

    // Executor cost
    let reported_tokens = state["native_usage"]["known_tokens"].as_f64();
    let reported_cost = state["native_usage"]["reported_cost_usd"].as_f64();
    let cost = if let Some(c) = reported_cost {
        json!({"unit": "provider_currency", "value": c, "source": "PROVIDER_REPORTED"})
    } else if let Some(t) = reported_tokens {
        json!({"unit": "tokens", "value": t, "source": "EXECUTOR_REPORTED"})
    } else {
        json!({"unit": "model_calls", "value": calls.len(), "source": "CALL_COUNT_PROXY"})
    };

    // Remaining capacity helpers (null = no ceiling)
    let remaining_24h: Value = match limits["max_executor_calls_per_24h"].as_u64() {
        Some(limit) => json!((limit as usize).saturating_sub(recent_24h)),
        None => Value::Null,
    };
    let remaining_30d: Value = match limits["max_executor_calls_per_30d"].as_u64() {
        Some(limit) => json!((limit as usize).saturating_sub(recent_30d)),
        None => Value::Null,
    };

    let probe_seconds = runtime["availability_probe_seconds"].as_f64().unwrap_or(0.0);
    let availability_probe_efficiency = json!({
        "readiness_transitions_observed": readiness_transitions,
        "transitions_per_probe": if probe_count > 0 { json!(readiness_transitions as f64 / probe_count as f64) } else { Value::Null },
        "probe_seconds_per_transition": if probe_count > 0 && readiness_transitions > 0 { json!(probe_seconds / readiness_transitions as f64) } else { Value::Null },
        "measurement_coverage": if probe_count > 0 { "CURRENT_COUNTERS" } else { "HISTORICAL_PROBE_COUNT_UNAVAILABLE" },
        "interpretation": "operational resource-versus-readiness proxy; not Executor price, usage, balance, or credit",
    });

    let mut sinks_obj = sinks.as_object().cloned().unwrap_or_default();
    sinks_obj.insert("review_required".into(), json!(review_required));

    json!({
        "native_usage": state.get("native_usage").cloned().unwrap_or_else(|| json!({})),
        "executor_cost": cost,
        "estimated_executor_capacity": {
            "available": executor["available"],
            "remaining_calls_24h": remaining_24h,
            "remaining_calls_30d": remaining_30d,
            "basis": "configured call ceilings and readiness; null remaining calls means no configured call ceiling, not provider credit balance",
        },
        "deterministic_resources": {
            "cycles": runtime["cycles"].as_u64().unwrap_or(0),
            "availability_probes": probe_count,
            "availability_probe_seconds": probe_seconds,
            "availability_checks_suppressed": runtime["availability_checks_suppressed"].as_u64().unwrap_or(0),
            "external_collections": runtime["external_collections"].as_u64().unwrap_or(0),
            "durable_writes": runtime["durable_writes"].as_u64().unwrap_or(0),
            "suppressed_writes": runtime["suppressed_writes"].as_u64().unwrap_or(0),
        },
        "availability_probe_efficiency": availability_probe_efficiency,
        "resource_sink_indicators": Value::Object(sinks_obj),
        "discovery_loop_yield_sink": discovery_loop_sink,
        "non_combinable_dimensions": true,
    })
}

// ── executor_efficiency_vital ─────────────────────────────────────────────────

/// Return bounded cost/outcome evidence without asserting causal attribution.
pub fn executor_efficiency_vital(config: &Value, state: &Value) -> Value {
    let empty_arr = vec![];
    let calls = state["executor_state"]["executor_calls"]
        .as_array()
        .unwrap_or(&empty_arr);
    let current = now_ts();

    let window = |seconds: f64| -> Value {
        let selected: Vec<&Value> = calls
            .iter()
            .filter(|c| {
                c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < seconds)
            })
            .collect();
        let count = selected.len();
        let productive = selected
            .iter()
            .filter(|c| matches!(c["outcome"].as_str(), Some("objective_created") | Some("accepted")))
            .count();
        let accepted = selected
            .iter()
            .filter(|c| c["outcome"].as_str() == Some("accepted"))
            .count();
        let improved: i64 = selected
            .iter()
            .map(|c| c["observed_metric_effect"]["improved"].as_i64().unwrap_or(0))
            .sum();
        let regressed: i64 = selected
            .iter()
            .map(|c| c["observed_metric_effect"]["regressed"].as_i64().unwrap_or(0))
            .sum();
        json!({
            "model_calls": count,
            "productive_calls": productive,
            "productive_yield": if count > 0 { json!(productive as f64 / count as f64) } else { Value::Null },
            "accepted_changes": accepted,
            "calls_per_accepted_change": if accepted > 0 { json!(count as f64 / accepted as f64) } else { Value::Null },
            "observed_metric_improvements": improved,
            "observed_metric_regressions": regressed,
            "attribution": "UNATTRIBUTED_COST_OUTCOME_ASSOCIATION",
        })
    };

    let executor_state = &state["executor_state"];
    let streak = executor_state["unproductive_discovery_streak"].as_u64().unwrap_or(0) as usize;
    let exhausted_threshold = config["executor"]["discovery_yield_exhausted_threshold"]
        .as_u64()
        .unwrap_or(5) as usize;
    let exhausted = streak >= exhausted_threshold;

    let mut yield_entry = json!({
        "unproductive_streak": streak,
        "exhausted_threshold": exhausted_threshold,
        "discovery_yield_exhausted": exhausted,
        "defer_reason": executor_state["discovery_defer_reason"],
    });
    if exhausted {
        yield_entry["qualifying_reset_conditions"] = json!([
            "new inbox input applied",
            "net-new evidence record",
            "intent or product-file change",
            "operator force-discovery",
        ]);
    }

    json!({
        "unit": "model_calls",
        "short_run_24h": window(86400.0),
        "long_run_30d": window(2592000.0),
        "discovery_loop_yield": yield_entry,
    })
}

// ── evolution_vital ───────────────────────────────────────────────────────────

/// Return the evolution diagnostic for two time windows.
pub fn evolution_vital(config: &Value, state: &Value) -> Value {
    let settings = if state["evaluation_system"].is_object() {
        &state["evaluation_system"]
    } else {
        &config["evaluation_system"]
    };
    let empty_obj = json!({});
    let settings = if settings.is_null() { &empty_obj } else { settings };
    let weights = &settings["weights"];
    let current = now_ts();

    let recent_items = |items: &[Value], seconds: f64, field: &str| -> Vec<Value> {
        items
            .iter()
            .filter(|item| {
                item[field]
                    .as_str()
                    .and_then(parse_iso)
                    .map_or(false, |ts| current - ts < seconds)
            })
            .cloned()
            .collect()
    };

    let empty_arr = vec![];
    let all_calls = state["executor_state"]["executor_calls"]
        .as_array()
        .unwrap_or(&empty_arr);
    let all_objectives = state["objectives"].as_array().unwrap_or(&empty_arr);

    let window = |seconds: f64| -> Value {
        let calls = recent_items(all_calls, seconds, "at");
        let objectives = recent_items(all_objectives, seconds, "created_at");
        let executions: Vec<&Value> = calls
            .iter()
            .filter(|c| c["stage"].as_str() == Some("execution"))
            .collect();
        let effects: Vec<&Value> = executions
            .iter()
            .filter_map(|c| {
                let e = &c["observed_metric_effect"];
                if e.is_object() { Some(e) } else { None }
            })
            .collect();
        let improved: i64 = effects.iter().map(|e| e["improved"].as_i64().unwrap_or(0)).sum();
        let regressed: i64 = effects.iter().map(|e| e["regressed"].as_i64().unwrap_or(0)).sum();

        let mut components: HashMap<String, f64> = HashMap::new();
        if !calls.is_empty() {
            let productive = calls
                .iter()
                .filter(|c| matches!(c["outcome"].as_str(), Some("objective_created") | Some("accepted")))
                .count();
            components.insert("productive_call_yield".into(), productive as f64 / calls.len() as f64);
        }
        if !executions.is_empty() {
            let accepted = executions.iter().filter(|c| c["outcome"].as_str() == Some("accepted")).count();
            components.insert("execution_acceptance".into(), accepted as f64 / executions.len() as f64);
        }
        if improved + regressed > 0 {
            components.insert("regression_safety".into(), improved as f64 / (improved + regressed) as f64);
        }
        if !objectives.is_empty() {
            let completed = objectives.iter().filter(|o| o["status"].as_str() == Some("completed")).count();
            components.insert("goal_completion".into(), completed as f64 / objectives.len() as f64);
        }

        let applicable_weight: f64 = components.keys().map(|name| weights[name].as_f64().unwrap_or(0.0)).sum();
        let score: Option<f64> = if applicable_weight > 0.0 {
            Some(100.0 * components.iter().map(|(name, v)| v * weights[name].as_f64().unwrap_or(0.0)).sum::<f64>() / applicable_weight)
        } else {
            None
        };

        let evidence_units = calls.len() + objectives.len() + improved as usize + regressed as usize;
        let minimum = settings["minimum_evidence_units"].as_u64().unwrap_or(5).max(1) as usize;
        let days = seconds / 86400.0;
        let accepted_exec = executions.iter().filter(|c| c["outcome"].as_str() == Some("accepted")).count();

        json!({
            "diagnostic_score": score,
            "score_scale": "0..100",
            "components": components.into_iter().map(|(k, v)| (k, json!(v))).collect::<serde_json::Map<_, _>>(),
            "confidence": (evidence_units as f64 / minimum as f64).min(1.0),
            "evidence_units": evidence_units,
            "accepted_change_rate_per_day": accepted_exec as f64 / days,
            "metric_improvement_rate_per_day": improved as f64 / days,
            "metric_regression_rate_per_day": regressed as f64 / days,
            "model_calls": calls.len(),
            "attribution": "UNATTRIBUTED_DIAGNOSTIC_ASSOCIATION",
        })
    };

    json!({
        "system_version": settings.get("version").cloned().unwrap_or_else(|| json!(1)),
        "short_run_24h": window(86400.0),
        "long_run_30d": window(2592000.0),
        "change_needed": settings.get("change_needed").cloned().unwrap_or_else(|| json!(false)),
        "last_assessment": settings.get("last_assessment").cloned().unwrap_or(Value::Null),
    })
}

// ── _objective_outcomes ───────────────────────────────────────────────────────

fn objective_outcomes(state: &Value) -> Value {
    let empty_arr = vec![];
    let objectives = state["objectives"].as_array().unwrap_or(&empty_arr);
    let now_ts_val = now_ts();
    let open_statuses = ["planned", "policy_blocked", "deferred_budget", "needs_reassessment"];

    let mut by_status: HashMap<String, usize> = HashMap::new();
    let mut stalled_30d = 0usize;

    for obj in objectives {
        let s = obj["status"].as_str().unwrap_or("unknown").to_string();
        *by_status.entry(s.clone()).or_insert(0) += 1;
        if open_statuses.contains(&s.as_str()) {
            if let Some(ts) = obj["created_at"].as_str().and_then(parse_iso) {
                if now_ts_val - ts > 30.0 * 86400.0 {
                    stalled_30d += 1;
                }
            }
        }
    }

    let total: usize = by_status.values().sum();
    let completed = by_status.get("completed").copied().unwrap_or(0);
    let completion_rate: Value = if total > 0 { json!(completed as f64 / total as f64) } else { Value::Null };
    let stall_rate: Value = if total > 0 { json!(stalled_30d as f64 / total as f64) } else { Value::Null };

    json!({
        "total": total,
        "by_status": by_status.into_iter().map(|(k, v)| (k, json!(v))).collect::<serde_json::Map<_, _>>(),
        "completion_rate": completion_rate,
        "stalled_30d": stalled_30d,
        "stall_rate": stall_rate,
    })
}

// ── VitalsSnapshot & vitals_snapshot ─────────────────────────────────────────

/// Strongly-typed snapshot of the most important runtime vitals.
/// The full JSON vitals (produced by `vitals_snapshot_full`) carries additional
/// fields; this struct covers the fields consumed by the web UI and TUI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VitalsSnapshot {
    pub lifecycle_state: String,
    pub aps_score: f64,
    pub cycle_count: usize,
    pub objectives_count: usize,
    pub evidence_count: usize,
    pub last_cycle_at: Option<String>,
    pub executor_efficiency: Value,
    pub evolution: Value,
    pub goal_portfolio: Value,
    pub work_evaluations: Value,
    pub resource_accounting: Value,
}

/// Build a `VitalsSnapshot` from config + state.
pub fn vitals_snapshot(config: &Value, state: &Value) -> VitalsSnapshot {
    let empty_arr = vec![];
    VitalsSnapshot {
        lifecycle_state: state["lifecycle_state"]
            .as_str()
            .unwrap_or("UNKNOWN")
            .to_string(),
        aps_score: state["aps_score"].as_f64().unwrap_or(0.0),
        cycle_count: state["runtime_efficiency"]["cycles"]
            .as_u64()
            .unwrap_or(0) as usize,
        objectives_count: state["objectives"].as_array().map_or(0, |a| a.len()),
        evidence_count: state["evidence"].as_array().map_or(0, |a| a.len()),
        last_cycle_at: state["checkpoints"]
            .as_array()
            .and_then(|a| a.last())
            .and_then(|c| c["at"].as_str())
            .map(|s| s.to_string()),
        executor_efficiency: executor_efficiency_vital(config, state),
        evolution: evolution_vital(config, state),
        goal_portfolio: goal_portfolio(state),
        work_evaluations: work_evaluations(state),
        resource_accounting: resource_accounting(config, state),
    }
}

/// Build the full vitals JSON map (matches the Python `vitals_snapshot` output).
pub fn vitals_snapshot_full(config: &Value, state: &Value) -> Value {
    let empty_arr = vec![];
    let profile = match state["progress_profiles"].as_array().and_then(|a| a.first()) {
        Some(p) => p.clone(),
        None => json!({"measures": {}, "next_follow_up": null}),
    };

    // Progress metrics
    let measures = profile["measures"].as_object().cloned().unwrap_or_default();
    let mut progress: serde_json::Map<String, Value> = serde_json::Map::new();
    for (name, measure) in &measures {
        let current = measure["current"].as_f64().unwrap_or(0.0);
        let baseline = measure["baseline"].as_f64().unwrap_or(0.0);
        let previous = measure["previous"].as_f64();
        let reference = previous.unwrap_or(baseline);
        let direction = measure["direction"].as_str().unwrap_or("nondecreasing");
        let target = measure["target"].as_f64().unwrap_or(0.0);
        progress.insert(name.clone(), json!({
            "baseline": baseline,
            "previous": measure.get("previous").cloned().unwrap_or(Value::Null),
            "current": current,
            "target": target,
            "direction": direction,
            "trend": compare(direction, current, reference),
        }));
    }

    let executor_state = &state["executor_state"];
    let current = now_ts();
    let calls_30d: Vec<&Value> = state["executor_state"]["executor_calls"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < 2592000.0))
        .collect();
    let calls_24h: Vec<&&Value> = calls_30d
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| current - ts < 86400.0))
        .collect();

    let settings = &config["executor"];
    let external = &state["external_metric_state"];
    let runtime_efficiency = &state["runtime_efficiency"];
    let efficiency_cycles = runtime_efficiency["cycles"].as_u64().unwrap_or(0) as usize;
    let suppressed_writes = runtime_efficiency["suppressed_writes"].as_u64().unwrap_or(0) as usize;

    // Custom vitals
    let observed_values: HashMap<String, Value> = external["latest"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .map(|obs| {
            let source = obs["source"].as_str().unwrap_or("unknown").to_string();
            (source, obs["values"].clone())
        })
        .collect();
    let flattened: HashMap<String, f64> = observed_values
        .values()
        .filter_map(|v| v.as_object())
        .flat_map(|m| m.iter().filter_map(|(k, v)| v.as_f64().map(|f| (k.clone(), f))))
        .collect();

    let custom_vitals: Vec<Value> = state["vital_definitions"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .map(|def| {
            let numerator_name = def["numerator"].as_str().unwrap_or("");
            let denominator_name = def["denominator"].as_str();
            let numerator = flattened.get(numerator_name).copied();
            let denominator = denominator_name.and_then(|n| flattened.get(n).copied());
            let (value, status): (Value, &str) = if numerator.is_none() {
                (Value::Null, "AWAITING_METRIC")
            } else if denominator_name.is_some() && (denominator.is_none() || denominator == Some(0.0)) {
                (Value::Null, "AWAITING_VALID_DENOMINATOR")
            } else {
                let v = if let Some(denom) = denominator {
                    numerator.unwrap() / denom
                } else {
                    numerator.unwrap()
                };
                (json!(v), "OBSERVED")
            };
            let mut d = def.as_object().cloned().unwrap_or_default();
            d.insert("value".into(), value);
            d.insert("status".into(), json!(status));
            d.insert("attribution".into(), json!("UNATTRIBUTED_OBSERVATION"));
            Value::Object(d)
        })
        .collect();

    // Evolution / scores
    let evolution = evolution_vital(config, state);
    let long_evolution = &evolution["long_run_30d"];

    let progress_known = !progress.is_empty();
    let progress_len = progress.len() as f64;
    let progress_score: Option<f64> = if progress_known {
        let improved = progress.values().filter(|m| m["trend"].as_str() == Some("improved")).count() as f64;
        let stable = progress.values().filter(|m| m["trend"].as_str() == Some("stable")).count() as f64;
        Some((improved + 0.5 * stable) / progress_len)
    } else {
        None
    };
    let lifecycle = state["lifecycle_state"].as_str().unwrap_or("UNKNOWN");
    let safety_score = if lifecycle == "BLOCKED" || state["unresolved_effects"].as_array().map_or(false, |a| !a.is_empty()) {
        0.0f64
    } else {
        1.0f64
    };
    let efficiency_score = long_evolution["diagnostic_score"].as_f64();
    let evidence_min = config["evaluation_system"]["minimum_evidence_units"].as_u64().unwrap_or(5).max(1) as f64;
    let evidence_units_long = long_evolution["evidence_units"].as_f64().unwrap_or(0.0);
    let long_confidence = long_evolution["confidence"].as_f64().unwrap_or(0.0);

    let dimensions = json!({
        "outcome_progress": {
            "score": progress_score,
            "confidence": if progress_known { 0.7 } else { 0.0 },
            "source": "declared progress measures",
        },
        "evidence_quality": {
            "score": (evidence_units_long / evidence_min).min(1.0),
            "confidence": long_confidence,
            "source": "30-day evolution evidence",
        },
        "safety_and_continuity": {
            "score": safety_score,
            "confidence": 1.0,
            "source": "blockers and unresolved effects",
        },
        "resource_efficiency": {
            "score": efficiency_score,
            "confidence": long_confidence,
            "source": "30-day qualified evolution diagnostic",
        },
    });

    let dim_arr = dimensions.as_object().unwrap();
    let available: Vec<&Value> = dim_arr.values().filter(|d| !d["score"].is_null()).collect();
    let coverage = available.len() as f64 / dim_arr.len() as f64;
    let mut vetoes = vec![];
    if safety_score == 0.0 {
        vetoes.push("failed safety or continuity condition");
    }
    let qualified = coverage == 1.0
        && available.iter().all(|d| d["confidence"].as_f64().unwrap_or(0.0) >= 0.5)
        && vetoes.is_empty();
    let overall_score: Value = if qualified {
        let sum: f64 = available.iter().filter_map(|d| d["score"].as_f64()).sum();
        json!(sum / available.len() as f64)
    } else {
        Value::Null
    };

    let system_scorecard = json!({
        "dimensions": dimensions,
        "coverage": coverage,
        "vetoes": vetoes,
        "overall_diagnostic_score": overall_score,
        "overall_status": if qualified { "QUALIFIED" } else { "WITHHELD" },
        "meaning": "decision aid only; never Authority, acceptance, causal proof, or a substitute for a failed guardrail",
    });

    // Controller recovery
    let repair_registry = state["system_repair_registry"].as_object().cloned().unwrap_or_default();
    let mut repair_statuses: HashMap<String, usize> = HashMap::new();
    for entry in repair_registry.values() {
        let s = entry["status"].as_str().unwrap_or("UNKNOWN").to_string();
        *repair_statuses.entry(s).or_insert(0) += 1;
    }

    let unproductive_streak = executor_state["unproductive_discovery_streak"].as_u64().unwrap_or(0);
    let disc_threshold = settings["discovery_yield_exhausted_threshold"].as_u64().unwrap_or(5);
    let disc_exhausted = unproductive_streak >= disc_threshold;

    let productive_yield_30d: Value = if !calls_30d.is_empty() {
        let p = calls_30d.iter().filter(|c| matches!(c["outcome"].as_str(), Some("objective_created") | Some("accepted"))).count();
        json!(p as f64 / calls_30d.len() as f64)
    } else {
        Value::Null
    };
    let productive_yield_24h: Value = if !calls_24h.is_empty() {
        let p = calls_24h.iter().filter(|c| matches!(c["outcome"].as_str(), Some("objective_created") | Some("accepted"))).count();
        json!(p as f64 / calls_24h.len() as f64)
    } else {
        Value::Null
    };

    // Source adapters summary
    let sources_obj = state["sources"].as_object();
    let sources_total = sources_obj.map_or(0, |m| m.len());
    let mut by_status_sources: serde_json::Map<String, Value> = serde_json::Map::new();
    for s in &["CONFIGURED", "OBSERVED", "ACTED"] {
        let count = sources_obj.map_or(0, |m| {
            m.values().filter(|r| r["status"].as_str() == Some(s)).count()
        });
        by_status_sources.insert(s.to_string(), json!(count));
    }
    let observed_sources: Vec<Value> = sources_obj
        .map_or(vec![], |m| {
            m.iter()
                .filter(|(_, r)| matches!(r["status"].as_str(), Some("OBSERVED") | Some("ACTED")))
                .map(|(sid, r)| json!({
                    "id": sid,
                    "kind": r["kind"],
                    "status": r["status"],
                    "enabled": r.get("enabled").cloned().unwrap_or_else(|| json!(true)),
                }))
                .collect()
        });

    let connectors: Vec<Value> = {
        let mut map: serde_json::Map<String, Value> = serde_json::Map::new();
        for src in config["external_metrics"]["sources"].as_array().unwrap_or(&empty_arr) {
            if let Some(id) = src["id"].as_str() {
                let mut s = src.as_object().cloned().unwrap_or_default();
                s.insert("status".into(), json!("ACTIVE"));
                map.insert(id.to_string(), Value::Object(s));
            }
        }
        for src in state["connector_sources"].as_array().unwrap_or(&empty_arr) {
            if let Some(id) = src["id"].as_str() {
                map.insert(id.to_string(), src.clone());
            }
        }
        map.into_values().collect()
    };

    json!({
        "type": "urace_vitals",
        "at": now_iso(),
        "lifecycle": lifecycle,
        "state_version": state["state_version"],
        "progress_metrics": Value::Object(progress),
        "progress_metric_source": "live_product",
        "executor_credit_usage": {
            "unit": "model_calls",
            "calls_24h": calls_24h.len(),
            "limit_24h": settings.get("max_executor_calls_per_24h").cloned().unwrap_or_else(|| json!(2)),
            "calls_30d": calls_30d.len(),
            "limit_30d": settings.get("max_executor_calls_per_30d").cloned().unwrap_or_else(|| json!(12)),
            "status": executor_state.get("discovery_budget_status").cloned().unwrap_or_else(|| json!("WITHIN_BUDGET")),
            "unproductive_streak": unproductive_streak,
            "discovery_yield_exhausted_threshold": disc_threshold,
            "discovery_yield_exhausted": disc_exhausted,
            "discovery_productive_yield_30d": productive_yield_30d,
            "discovery_productive_yield_24h": productive_yield_24h,
            "discovery_defer_reason": executor_state.get("discovery_defer_reason").cloned().unwrap_or(Value::Null),
            "transport_attempts_30d": calls_30d.iter().map(|c| c["transport_attempts"].as_u64().unwrap_or(1)).sum::<u64>(),
            "capacity_deferred_logical_calls_30d": calls_30d.iter().filter(|c| c["outcome"].as_str() == Some("deferred_provider_capacity")).count(),
            "capacity_status": executor_state.get("capacity_status").cloned().unwrap_or_else(|| json!("AVAILABLE_OR_UNKNOWN")),
            "capacity_retry_at": executor_state.get("capacity_retry_at").cloned().unwrap_or(Value::Null),
        },
        "executor_pool": executor_state.get("provider_pool").cloned().unwrap_or_else(|| json!({})),
        "executor_efficiency": executor_efficiency_vital(config, state),
        "evolution": evolution,
        "system_scorecard": system_scorecard,
        "work_evaluations": work_evaluations(state),
        "resource_accounting": resource_accounting(config, state),
        "runtime_efficiency": {
            "cycles": efficiency_cycles,
            "durable_writes": runtime_efficiency["durable_writes"].as_u64().unwrap_or(0),
            "suppressed_writes": suppressed_writes,
            "write_suppression_ratio": if efficiency_cycles > 0 { json!(suppressed_writes as f64 / efficiency_cycles as f64) } else { Value::Null },
            "state_bytes": 0, // state file size not available without I/O here; callers may supply
            "availability_failure_streak": executor_state.get("availability_failure_streak").cloned().unwrap_or_else(|| json!(0)),
            "external_failure_streak": external.get("failure_streak").cloned().unwrap_or_else(|| json!(0)),
            "external_next_collection_at": external.get("next_collection_at").cloned().unwrap_or(Value::Null),
        },
        "controller_recovery": {
            "registered_identities": repair_registry.len(),
            "statuses": repair_statuses.into_iter().map(|(k, v)| (k, json!(v))).collect::<serde_json::Map<_, _>>(),
        },
        "scope_priorities": state.get("scope_priority_system").cloned().unwrap_or_else(|| json!({})),
        "external_evidence": {
            "mode": external.get("mode").cloned().unwrap_or_else(|| json!("DISABLED")),
            "last_collection": external.get("last_collection").cloned().unwrap_or(Value::Null),
            "observed_sources": external["latest"].as_array().map_or(0, |a| a.len()),
            "values": observed_values.into_iter().map(|(k, v)| (k, v)).collect::<serde_json::Map<_, _>>(),
            "metric_definitions": state.get("metric_definitions").cloned().unwrap_or_else(|| json!([])),
            "vital_definitions": state.get("vital_definitions").cloned().unwrap_or_else(|| json!([])),
            "custom_vitals": custom_vitals,
            "connectors": connectors,
            "errors": external.get("errors").cloned().unwrap_or_else(|| json!([])),
        },
        "source_adapters": {
            "total": sources_total,
            "by_status": Value::Object(by_status_sources),
            "observed": observed_sources,
        },
        "health": {
            "recorded_blockers": state["blockers"].as_array().map_or(0, |a| a.len()),
            "lifecycle_blocked": lifecycle == "BLOCKED",
            "unresolved_effects": state["unresolved_effects"].as_array().map_or(0, |a| a.len()),
            "pending_validation": state["pending_validation"].as_array().map_or(0, |a| a.len()),
            "executor_available": executor_state.get("available").cloned().unwrap_or(Value::Null),
            "next_follow_up": profile["next_follow_up"],
        },
        "policies": {
            "self_evolution": state["self_evolution_policy"]["mode"].as_str().unwrap_or("DISABLED"),
            "authority_boundary": {
                "delegated": state["authority"].get("delegated").cloned().unwrap_or_else(|| json!([])),
                "reserved": state["authority"].get("reserved").cloned().unwrap_or_else(|| json!([])),
            },
            "destination_anchor": {
                "digest": state["destination_anchor"].get("digest").cloned().unwrap_or(Value::Null),
                "purpose": state["destination_anchor"].get("purpose").cloned().unwrap_or(Value::Null),
                "established_at": state["destination_anchor"].get("established_at").cloned().unwrap_or(Value::Null),
            },
        },
        "value_trajectory": {
            "acceleration": state["value_trajectory"].get("acceleration").cloned().unwrap_or(Value::Null),
            "cumulative_value": state["value_trajectory"]["cumulative_value"].as_f64().unwrap_or(0.0),
            "peak_velocity": state["value_trajectory"]["peak_velocity"].as_f64().unwrap_or(0.0),
            "checkpoints_recorded": state["value_trajectory"]["checkpoints"].as_array().map_or(0, |a| a.len()),
            "self_correction": false, // value_trajectory.self_correction_needed — not ported yet
        },
        "objective_outcomes": objective_outcomes(state),
    })
}

// ── render ────────────────────────────────────────────────────────────────────

/// Render a text summary of state (matches Python `render(state)`).
pub fn render(state: &Value) -> String {
    let empty_obj = json!({});
    let profile = state["progress_profiles"]
        .as_array()
        .and_then(|a| a.first())
        .unwrap_or(&empty_obj);
    let executor_state = &state["executor_state"];
    let empty_arr = vec![];
    let measures = profile["measures"].as_object().cloned().unwrap_or_default();

    let mut lines = vec![
        format!("Lifecycle: {}", state["lifecycle_state"].as_str().unwrap_or("UNKNOWN")),
        format!("Intent: {}", state["intent"]["purpose"].as_str().unwrap_or("")),
        format!("State version: {}", state["state_version"]),
        format!("Current objective: {}", state["current_objective"].as_str().unwrap_or("none")),
        "Progress:".to_string(),
    ];
    for (name, measure) in &measures {
        let baseline = measure["baseline"].as_f64().unwrap_or(0.0);
        let current = measure["current"].as_f64().unwrap_or(0.0);
        let target = measure["target"].as_f64().unwrap_or(0.0);
        lines.push(format!("  {}: baseline={} current={} target={}", name, baseline, current, target));
    }
    lines.push(format!("Next follow-up: {}", profile["next_follow_up"]));
    lines.push(format!("Executor available: {}", executor_state["available"]));
    let pool = executor_state["provider_pool"].as_object();
    let pool_str = pool.map_or("none".to_string(), |p| {
        if p.is_empty() {
            "none".to_string()
        } else {
            p.iter()
                .filter_map(|(pid, ps)| {
                    if ps.is_object() {
                        Some(format!(" {}(available={} authenticated={})", pid, ps["available"], ps["authenticated"]))
                    } else {
                        None
                    }
                })
                .collect::<String>()
        }
    });
    lines.push(format!("Executor pool:{}", pool_str));
    lines.push(format!("Last availability check: {}",
        executor_state["last_availability_check"].as_str().unwrap_or("never")));
    lines.push(format!("Executor failures: {}", executor_state["failures"].as_array().map_or(0, |a| a.len())));
    lines.push(format!("Executor calls retained (30d): {}",
        executor_state["executor_calls"].as_array().map_or(0, |a| a.len())));
    lines.push(format!("Executor budget: {}",
        executor_state["discovery_budget_status"].as_str().unwrap_or("WITHIN_BUDGET")));

    let streak = executor_state["unproductive_discovery_streak"].as_u64().unwrap_or(0);
    let threshold = 5u64;
    lines.push(format!("Unproductive discovery streak: {}/{} (exhausted at threshold)", streak, threshold));
    if streak >= threshold {
        lines.push("DISCOVERY_YIELD_EXHAUSTED: streak reached threshold; next discovery requires a qualifying reset event (new goal, new evidence, intent change, or force-discovery)".to_string());
    }
    if let Some(reason) = executor_state["discovery_defer_reason"].as_str() {
        lines.push(format!("Discovery defer reason: {}", reason));
    }
    lines.push(format!("Self-evolution policy: {}",
        state["self_evolution_policy"]["mode"].as_str().unwrap_or("DISABLED")));
    lines.push(format!("External metrics: {} ({} sources observed)",
        state["external_metric_state"]["mode"].as_str().unwrap_or("DISABLED"),
        state["external_metric_state"]["latest"].as_array().map_or(0, |a| a.len())));
    lines.push(format!("Reasoning memory: {} structured patterns",
        state["reasoning_memory"].as_array().map_or(0, |a| a.len())));
    lines.push(format!("Unresolved effects: {}",
        state["unresolved_effects"].as_array().map_or(0, |a| a.len())));

    // Technique gate summary
    if let Some(log) = state["technique_application_log"].as_array() {
        let recent: Vec<&Value> = if log.len() > 12 { &log[log.len()-12..] } else { log }.iter().collect();
        let summary: serde_json::Map<String, Value> = recent
            .iter()
            .filter_map(|r| r["technique"].as_str().map(|t| (t.to_string(), r["verdict"].clone())))
            .collect();
        lines.push(format!("  technique-gate: {:?}", summary));
    }

    let eval_sys = &state["evaluation_system"];
    let last_assessment = eval_sys["last_assessment"].as_str().unwrap_or("").to_lowercase();
    let evidence_count = state["evidence"].as_array().map_or(0, |a| a.len());
    let min_units = eval_sys["minimum_evidence_units"].as_u64().unwrap_or(5) as usize;
    let evidence_blocked = last_assessment.contains("insufficient") || evidence_count < min_units;
    if evidence_blocked {
        let shortfall = min_units.saturating_sub(evidence_count);
        lines.extend([
            "Evidence-blocked: True".to_string(),
            "  missing-dimension: evidence_quality".to_string(),
            format!("  shortfall: {} evidence units below minimum ({})", shortfall, min_units),
            "  advancement-blocked: True".to_string(),
            format!("  earliest-qualifying-condition: accumulate {} additional evidence units or lower evaluation minimum", shortfall),
        ]);
    }
    lines.join("\n")
}

// ── render_vitals ─────────────────────────────────────────────────────────────

/// Render a focused vitals summary string.
pub fn render_vitals(vitals: &VitalsSnapshot) -> String {
    let eff = &vitals.executor_efficiency;
    let short = &eff["short_run_24h"];
    let long = &eff["long_run_30d"];
    let evo = &vitals.evolution;
    let evo_short = &evo["short_run_24h"];
    let evo_long = &evo["long_run_30d"];

    let mut lines = vec![
        format!("URACE core vitals"),
        format!("Lifecycle: {} (aps_score={} cycles={})", vitals.lifecycle_state, vitals.aps_score, vitals.cycle_count),
        format!("Objectives: {} | Evidence: {}", vitals.objectives_count, vitals.evidence_count),
        "Progress: (see vitals_snapshot_full for per-metric detail)".to_string(),
        format!(
            "Short-run efficiency (24h): productive-yield={} accepted={} calls-per-accepted={}",
            short["productive_yield"], short["accepted_changes"], short["calls_per_accepted_change"]
        ),
        format!(
            "Long-run efficiency (30d): productive-yield={} accepted={} calls-per-accepted={} metric-improved={} metric-regressed={}",
            long["productive_yield"], long["accepted_changes"], long["calls_per_accepted_change"],
            long["observed_metric_improvements"], long["observed_metric_regressions"]
        ),
        format!("Attribution: {}", long["attribution"]),
        format!(
            "Evolution vital: short-score={} short-confidence={} long-score={} long-confidence={} accepted/day={} attribution={}",
            evo_short["diagnostic_score"], evo_short["confidence"],
            evo_long["diagnostic_score"], evo_long["confidence"],
            evo_long["accepted_change_rate_per_day"], evo_long["attribution"]
        ),
        format!(
            "Work evaluations: goals={} contexts={} action-groups={}",
            vitals.work_evaluations["goals"].as_array().map_or(0, |a| a.len()),
            vitals.work_evaluations["contexts"].as_array().map_or(0, |a| a.len()),
            vitals.work_evaluations["actions"].as_object().map_or(0, |m| m.len()),
        ),
        format!(
            "Resource accounting: executor={} {} source={}",
            vitals.resource_accounting["executor_cost"]["value"],
            vitals.resource_accounting["executor_cost"]["unit"].as_str().unwrap_or(""),
            vitals.resource_accounting["executor_cost"]["source"].as_str().unwrap_or(""),
        ),
        format!("Goal portfolio: {} goals ranked", vitals.goal_portfolio["goals"].as_array().map_or(0, |a| a.len())),
        format!("Last cycle at: {}", vitals.last_cycle_at.as_deref().unwrap_or("never")),
    ];
    lines.join("\n")
}

// ── render_cycle ──────────────────────────────────────────────────────────────

/// Render one autonomous cycle event as a string (or JSON).
pub fn render_cycle(state: &Value, outcome: &Value, index: usize, json_mode: bool, verbose: bool) -> String {
    let empty_obj = json!({});
    let empty_arr = vec![];
    let profile = state["progress_profiles"]
        .as_array()
        .and_then(|a| a.first())
        .unwrap_or(&empty_obj);
    let executor_state = &state["executor_state"];
    let measures = profile["measures"].as_object().cloned().unwrap_or_default();

    let mut metrics: serde_json::Map<String, Value> = serde_json::Map::new();
    for (name, measure) in &measures {
        let current = measure["current"].as_f64().unwrap_or(0.0);
        let baseline = measure["baseline"].as_f64().unwrap_or(0.0);
        let previous = measure["previous"].as_f64();
        let reference = previous.unwrap_or(baseline);
        let direction = measure["direction"].as_str().unwrap_or("nondecreasing");
        metrics.insert(name.clone(), json!({
            "baseline": baseline,
            "previous": measure.get("previous").cloned().unwrap_or(Value::Null),
            "current": current,
            "target": measure["target"].as_f64().unwrap_or(0.0),
            "trend": compare(direction, current, reference),
        }));
    }

    let objective = outcome["objective"].as_object().map(|_| &outcome["objective"]);
    let plan = outcome["plan"].as_object().map(|_| &outcome["plan"]);
    let execution = outcome["execution"].as_object().map(|_| &outcome["execution"]);

    let decision_trace = json!({
        "decision": objective.map_or_else(|| outcome["outcome"].clone(), |o| o["title"].clone()),
        "basis": objective.map_or_else(|| outcome.get("reason").cloned().unwrap_or_else(|| json!("cycle assessment")), |o| o["reason"].clone()),
        "authority": if objective.is_some() { "delegated lifecycle navigation" } else { "no consequential action selected" },
        "planned_steps": plan.map_or_else(|| json!([]), |p| p["steps"].clone()),
        "validation": execution.map_or_else(
            || if objective.is_some() { json!("pending") } else { json!("not applicable") },
            |e| e["status"].clone()
        ),
        "changed_files": execution.map_or_else(|| json!([]), |e| e["changed_files"].clone()),
        "alternatives": outcome.get("candidate_comparison").cloned().unwrap_or_else(|| json!([])),
    });

    let budget_now = now_ts();
    let budget_calls_30d: Vec<&Value> = executor_state["executor_calls"]
        .as_array()
        .unwrap_or(&empty_arr)
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| budget_now - ts < 2592000.0))
        .collect();
    let budget_calls_24h: Vec<&&Value> = budget_calls_30d
        .iter()
        .filter(|c| c["at"].as_str().and_then(parse_iso).map_or(false, |ts| budget_now - ts < 86400.0))
        .collect();

    let event = json!({
        "type": "autonomous_cycle",
        "cycle": index,
        "at": now_iso(),
        "lifecycle": state["lifecycle_state"],
        "outcome": outcome,
        "metrics": Value::Object(metrics.clone()),
        "metric_system": state.get("metric_system").cloned().unwrap_or_else(|| json!({})),
        "executor_available": executor_state["available"],
        "executor_credit_budget": {
            "calls_24h": budget_calls_24h.len(),
            "limit_24h": 2,
            "calls_30d": budget_calls_30d.len(),
            "limit_30d": 12,
            "unproductive_streak": executor_state["unproductive_discovery_streak"].as_u64().unwrap_or(0),
            "status": executor_state.get("discovery_budget_status").cloned().unwrap_or_else(|| json!("WITHIN_BUDGET")),
        },
        "executor_efficiency_vital": executor_efficiency_vital(&json!({}), state),
        "evolution_vital": evolution_vital(&json!({}), state),
        "resource_accounting": resource_accounting(&json!({}), state),
        "self_evolution_policy": state.get("self_evolution_policy").cloned().unwrap_or_else(|| json!({"mode": "DISABLED"})),
        "external_metrics": state.get("external_metric_state").cloned().unwrap_or_else(|| json!({"mode": "DISABLED", "latest": [], "errors": []})),
        "reasoning_memory_summary": {
            "entries": state["reasoning_memory"].as_array().map_or(0, |a| a.len()),
            "recurring_signatures": state["pattern_memory"].as_object().map_or(0, |m| {
                m.values().filter(|v| v["recurring"].as_bool().unwrap_or(false)).count()
            }),
        },
        "decision_trace": decision_trace,
        "next_follow_up": profile["next_follow_up"],
        "state_version": state["state_version"],
        "recovery_manifest": executor_state.get("recovery_manifest").cloned().unwrap_or(Value::Null),
        "progress_vector": executor_state.get("progress_vector").cloned().unwrap_or(Value::Null),
        "progress_stagnant_cycles": executor_state.get("progress_stagnant_cycles").cloned().unwrap_or_else(|| json!(0)),
    });

    if json_mode {
        return serde_json::to_string(&event).unwrap_or_default();
    }

    let summary = objective
        .map(|o| o["title"].as_str().unwrap_or("").to_string())
        .unwrap_or_else(|| {
            outcome["reason"].as_str()
                .unwrap_or_else(|| outcome["outcome"].as_str().unwrap_or(""))
                .to_string()
        });
    let lifecycle = event["lifecycle"].as_str().unwrap_or("UNKNOWN");
    let outcome_str = outcome["outcome"].as_str().unwrap_or("");
    let at_str = event["at"].as_str().unwrap_or("");
    let mut lines = vec![
        format!("[{}] cycle={} lifecycle={} outcome={}", at_str, index, lifecycle, outcome_str),
        format!("  activity: {}", summary),
    ];

    if !verbose {
        let changed_files: Vec<&str> = event["decision_trace"]["changed_files"]
            .as_array()
            .map_or(vec![], |a| a.iter().filter_map(|v| v.as_str()).collect());
        if !changed_files.is_empty() {
            lines.push(format!("  changed: {}", changed_files.join(", ")));
        }
        let validation = event["decision_trace"]["validation"].as_str().unwrap_or("");
        let next = event["next_follow_up"].as_str().unwrap_or("");
        lines.push(format!("  validation: {} | next: {}", validation, next));
        let budget_status = event["executor_credit_budget"]["status"].as_str().unwrap_or("WITHIN_BUDGET");
        if budget_status != "WITHIN_BUDGET" {
            let defer = executor_state["discovery_defer_reason"].as_str().unwrap_or(budget_status);
            lines.push(format!("  discovery-deferred: {}", defer));
        }
        if let Some(pv) = event["progress_vector"].as_f64() {
            lines.push(format!("  progress: {:.1}%", pv * 100.0));
        }
        if let Some(rm) = event["recovery_manifest"].as_object() {
            lines.push(format!(
                "  recovery-pending: manifest={} cause={} progress={} delta={}",
                rm.get("manifest_id").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("emission_cause").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("progress_at_emit").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("goal_delta").and_then(|v| v.as_str()).unwrap_or("unknown"),
            ));
        }
        return lines.join("\n");
    }

    // Verbose mode
    lines.extend([
        format!("  decision-basis: {}", event["decision_trace"]["basis"].as_str().unwrap_or("")),
        format!("  authority: {}", event["decision_trace"]["authority"].as_str().unwrap_or("")),
        format!("  candidate-comparison: {}", event["decision_trace"]["alternatives"]),
        format!("  validation: {}", event["decision_trace"]["validation"].as_str().unwrap_or("")),
    ]);
    let steps: Vec<&str> = event["decision_trace"]["planned_steps"]
        .as_array()
        .map_or(vec![], |a| a.iter().filter_map(|v| v.as_str()).collect());
    if !steps.is_empty() {
        lines.push(format!("  plan: {}", steps.join(" -> ")));
    }
    let changed_files: Vec<&str> = event["decision_trace"]["changed_files"]
        .as_array()
        .map_or(vec![], |a| a.iter().filter_map(|v| v.as_str()).collect());
    if !changed_files.is_empty() {
        lines.push(format!("  changed-files: {}", changed_files.join(", ")));
    }
    let budget_status = event["executor_credit_budget"]["status"].as_str().unwrap_or("WITHIN_BUDGET");
    if budget_status != "WITHIN_BUDGET" {
        let defer = executor_state["discovery_defer_reason"].as_str().unwrap_or(budget_status);
        lines.push(format!("  discovery-deferred: {}", defer));
    }
    for (name, metric) in &metrics {
        lines.push(format!(
            "  metric {}: {} trend={} baseline={} target={}",
            name, metric["current"], metric["trend"], metric["baseline"], metric["target"]
        ));
    }
    lines.extend([
        format!("  metric-system: v{} change-needed={}", event["metric_system"].get("version").and_then(|v| v.as_i64()).unwrap_or(1), event["metric_system"]["change_needed"]),
        format!("  executor-available: {}", event["executor_available"]),
        format!(
            "  executor-credit-budget: day={}/{} month={}/{} unproductive-streak={} status={}",
            event["executor_credit_budget"]["calls_24h"],
            event["executor_credit_budget"]["limit_24h"],
            event["executor_credit_budget"]["calls_30d"],
            event["executor_credit_budget"]["limit_30d"],
            event["executor_credit_budget"]["unproductive_streak"],
            event["executor_credit_budget"]["status"],
        ),
        format!(
            "  executor-efficiency-vital: short-yield={} long-yield={} long-calls-per-accepted={} attribution={}",
            event["executor_efficiency_vital"]["short_run_24h"]["productive_yield"],
            event["executor_efficiency_vital"]["long_run_30d"]["productive_yield"],
            event["executor_efficiency_vital"]["long_run_30d"]["calls_per_accepted_change"],
            event["executor_efficiency_vital"]["long_run_30d"]["attribution"].as_str().unwrap_or(""),
        ),
        format!(
            "  evolution-vital: short-score={} short-confidence={} long-score={} long-confidence={}",
            event["evolution_vital"]["short_run_24h"]["diagnostic_score"],
            event["evolution_vital"]["short_run_24h"]["confidence"],
            event["evolution_vital"]["long_run_30d"]["diagnostic_score"],
            event["evolution_vital"]["long_run_30d"]["confidence"],
        ),
        format!(
            "  resources: executor={} {} source={} remaining-day={} probes={} collections={}",
            event["resource_accounting"]["executor_cost"]["value"],
            event["resource_accounting"]["executor_cost"]["unit"].as_str().unwrap_or(""),
            event["resource_accounting"]["executor_cost"]["source"].as_str().unwrap_or(""),
            event["resource_accounting"]["estimated_executor_capacity"]["remaining_calls_24h"],
            event["resource_accounting"]["deterministic_resources"]["availability_probes"],
            event["resource_accounting"]["deterministic_resources"]["external_collections"],
        ),
        format!("  resource-sinks: {}", event["resource_accounting"]["resource_sink_indicators"]),
        format!("  self-evolution-policy: {}", event["self_evolution_policy"].get("mode").and_then(|v| v.as_str()).unwrap_or("DISABLED")),
        format!(
            "  external-metrics: {} observed={} errors={}",
            event["external_metrics"].get("mode").and_then(|v| v.as_str()).unwrap_or("DISABLED"),
            event["external_metrics"]["latest"].as_array().map_or(0, |a| a.len()),
            event["external_metrics"]["errors"].as_array().map_or(0, |a| a.len()),
        ),
        format!(
            "  reasoning-memory: entries={} recurring-signatures={}",
            event["reasoning_memory_summary"]["entries"],
            event["reasoning_memory_summary"]["recurring_signatures"],
        ),
        format!(
            "  progress-vector: {} stagnant-cycles={}",
            event["progress_vector"], event["progress_stagnant_cycles"]
        ),
        format!("  next-follow-up: {}", event["next_follow_up"]),
    ]);
    if let Some(rm) = event["recovery_manifest"].as_object() {
        lines.extend([
            format!(
                "  recovery-manifest: id={} cause={} emitted={}",
                rm.get("manifest_id").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("emission_cause").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("emitted_at").and_then(|v| v.as_str()).unwrap_or(""),
            ),
            format!(
                "    last-safe-state={} commit={}",
                rm.get("last_safe_state").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("last_safe_commit").and_then(|v| v.as_str()).unwrap_or(""),
            ),
            format!(
                "    progress-at-emit={} delta={}",
                rm.get("progress_at_emit").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("goal_delta").and_then(|v| v.as_str()).unwrap_or(""),
            ),
            format!(
                "    recommended-tier={} mode={}",
                rm.get("recommended_tier").and_then(|v| v.as_str()).unwrap_or(""),
                rm.get("execution_mode").and_then(|v| v.as_str()).unwrap_or(""),
            ),
        ]);
    }
    lines.join("\n")
}

// ── command_catalog ───────────────────────────────────────────────────────────

/// Return the full command catalog (matches Python `command_catalog()`).
pub fn command_catalog() -> HashMap<String, Vec<HashMap<String, String>>> {
    let mut catalog: HashMap<String, Vec<HashMap<String, String>>> = HashMap::new();

    let immediate: Vec<HashMap<String, String>> = vec![
        [("command", "help [operation]"), ("purpose", "inspect installed operations and contextual usage without an Executor call")],
        [("command", "init"), ("purpose", "initialize durable lifecycle state")],
        [("command", "check"), ("purpose", "inspect complete lifecycle state")],
        [("command", "vitals"), ("purpose", "inspect focused metrics, cost, and health")],
        [("command", "report status|export"), ("purpose", "inspect analytics capabilities or export portable CSV/HTML and optional XLSX")],
        [("command", "configuration auto-goals status|enable|disable; configuration auto-goals replenish status|enable|disable"), ("purpose", "control one auto-goals feature and its replenishment sub-setting")],
        [("command", "configuration effort status|low|medium|high [--executor ID]"), ("purpose", "URACE resource effort; inherit --executor ID removes an override")],
        [("command", "commands"), ("purpose", "show this command contract")],
        [("command", "inbox list"), ("purpose", "inspect durable pending inputs")],
        [("command", "context list"), ("purpose", "inspect governing, user-supplied, and URACE-derived context")],
        [("command", "executor status"), ("purpose", "inspect configured Executor readiness")],
        [("command", "source|metric|vital list; goal list|inspect|forecast"), ("purpose", "inspect configuration, explain goal priority, and view advisory schedules")],
        [("command", "policy list|budget show"), ("purpose", "inspect autonomy policy and Executor limits")],
        [("command", "evaluation show"), ("purpose", "inspect the versioned evolution evaluator and current results")],
        [("command", "update download|explain"), ("purpose", "obtain and inspect a hash-identified specification candidate without changing the accepted implementation")],
        [("command", "portfolio ..."), ("purpose", "run the optional isolated-worktree portfolio helper")],
        [("command", "plan"), ("purpose", "assess and plan one cycle without execution")],
        [("command", "auto"), ("purpose", "run bounded or persistent lifecycle execution")],
        [("command", "why [change-id]"), ("purpose", "trace the decision record and governing rules for a change")],
        [("command", "rules list|show [rule-id]"), ("purpose", "inspect the active Rule Ledger")],
        [("command", "crc show|regenerate"), ("purpose", "inspect or regenerate the Cognitive Resume Context")],
        [("command", "compact|decompact [field]"), ("purpose", "compact governed list fields at a safe lifecycle boundary or restore from archive")],
        [("command", "pause|resume"), ("purpose", "pause lifecycle execution or resume from PAUSED state")],
        [("command", "intent list|add|supersede|deactivate"), ("purpose", "inspect or modify the Rule Ledger intent entries")],
        [("command", "constraint list|add|deactivate"), ("purpose", "inspect or modify the Rule Ledger constraint entries")],
        [("command", "amend [record-id] --reason <text>"), ("purpose", "amend a compacted archive record with a non-destructive provenance annotation")],
    ]
    .into_iter()
    .map(|arr| arr.into_iter().map(|(k, v)| (k.to_string(), v.to_string())).collect())
    .collect();

    let durable_input: Vec<HashMap<String, String>> = vec![
        [("command", "add-context|add-goal|add-source|add-metric|add-vital"), ("purpose", "queue authoritative input")],
        [("command", "source enable|disable|remove"), ("purpose", "queue connector control")],
        [("command", "metric|vital remove"), ("purpose", "queue observability removal")],
        [("command", "goal prioritize|schedule|pin|unpin|defer|resume|disable|cancel|delete"), ("purpose", "queue safe-boundary goal management; delete retains an audit tombstone")],
        [("command", "executor attach|detach|retry-policy"), ("purpose", "queue Executor configuration or per-Executor capacity scheduling")],
        [("command", "policy set|budget set"), ("purpose", "queue autonomy policy or Executor limit changes")],
        [("command", "evaluation set-weight|set-minimum"), ("purpose", "queue an audited evaluator revision")],
        [("command", "update apply"), ("purpose", "queue a hash-bound specification migration through isolated validation and rollback")],
    ]
    .into_iter()
    .map(|arr| arr.into_iter().map(|(k, v)| (k.to_string(), v.to_string())).collect())
    .collect();

    catalog.insert("immediate".into(), immediate);
    catalog.insert("durable_input".into(), durable_input);
    catalog
}

// ── top_level_help ────────────────────────────────────────────────────────────

/// Return the top-level help string.
pub fn top_level_help() -> String {
    r#"URACE — autonomous product improvement

  urace init                first-time setup: config, state, and directory tree
  urace start               boot daemon, join P2P network, detect executors
  urace stop                graceful shutdown
  urace status              observe: lifecycle, network, executor, goals, health
  urace                     shell — type goals and questions in plain language

Inside the shell, type naturally:

  > improve test coverage by 20%        → goal added
  > never modify production config      → rule added
  > why did you change the README?      → decision explained
  > what blocked progress today?        → blockers listed
  > run now                             → cycle triggered
  > status goals                        → goals summary
  > status network                      → network detail
  > update                              → apply pending spec update

Slash shortcuts: /status  /stop  /reload  /peers  /exit

Configure in config.json or via freeform: "enable the executor", "set effort to high"
Apply config changes with: urace reload    (or they take effect on next start)

For integrations (all hidden commands still work):
  urace <command> --help    full reference for any command
  urace help <command>      contextual help without Executor
  urace m2m '{"command":"status"}'   machine-to-machine JSON interface"#
        .to_string()
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_state() -> Value {
        json!({
            "lifecycle_state": "ACTIVE",
            "aps_score": 72.5,
            "state_version": "1.0.0",
            "objectives": [],
            "evidence": [],
            "checkpoints": [],
            "decision_records": [],
            "integrity_gaps": [],
            "sweet_spot_assessments": [],
            "executor_state": {
                "executor_calls": [],
                "failures": [],
                "unproductive_discovery_streak": 0,
                "available": true,
                "provider_pool": {},
            },
            "operations": [],
            "context_inputs": [],
            "reasoning_memory": [],
            "external_metric_state": {"mode": "DISABLED", "latest": [], "errors": [], "failure_streak": 0},
            "runtime_efficiency": {"cycles": 5, "durable_writes": 10, "suppressed_writes": 2, "availability_probes": 0, "external_collections": 0},
            "progress_profiles": [{"measures": {}, "next_follow_up": "2026-11-25T00:00:00+00:00"}],
            "intent": {"purpose": "test"},
            "authority": {},
            "unresolved_effects": [],
            "blockers": [],
            "pending_validation": [],
            "self_evolution_policy": {"mode": "NECESSARY_ONLY"},
            "evaluation_system": {"minimum_evidence_units": 5},
            "sources": {},
            "value_trajectory": {},
            "destination_anchor": {},
            "system_repair_registry": {},
        })
    }

    fn make_config() -> Value {
        json!({
            "product_files": [],
            "executor": {
                "kind": "deterministic",
                "enabled": false,
                "discovery_yield_exhausted_threshold": 5,
                "max_executor_calls_per_24h": 2,
                "max_executor_calls_per_30d": 12,
            },
            "evaluation_system": {"minimum_evidence_units": 5, "weights": {}},
            "external_metrics": {"sources": []},
        })
    }

    // ── objective_score ───────────────────────────────────────────────────────

    #[test]
    fn test_objective_score_defaults() {
        let obj = json!({});
        let score = objective_score(&obj);
        // With all defaults: priority=50, expected_value=0.5*20=10, urgency=0.5*10=5,
        // confidence=0.5*5=2.5, cost=-0.5*10=-5, risk=-0.5*10=-5, rest=0
        // = 50 + 10 + 5 + 2.5 - 5 - 5 = 57.5
        assert!((score - 57.5).abs() < 0.001, "expected ~57.5, got {}", score);
    }

    #[test]
    fn test_objective_score_pinned() {
        let obj = json!({"pinned": true, "priority": 50});
        let score = objective_score(&obj);
        // pinned_attention = 20 extra
        assert!(score > 70.0, "pinned score should exceed 70, got {}", score);
    }

    #[test]
    fn test_objective_score_priority_floor_ceiling() {
        let obj = json!({"priority": 10, "priority_floor": 60});
        let bd = objective_score_breakdown(&obj);
        assert!(*bd.get("priority").unwrap() >= 60.0);

        let obj2 = json!({"priority": 90, "priority_ceiling": 40});
        let bd2 = objective_score_breakdown(&obj2);
        assert!(*bd2.get("priority").unwrap() <= 40.0);
    }

    #[test]
    fn test_objective_score_breakdown_total_sum() {
        let obj = json!({"priority": 70, "urgency": 0.8, "risk": 0.2});
        let bd = objective_score_breakdown(&obj);
        let sum: f64 = bd.iter().filter(|(k, _)| k.as_str() != "total").map(|(_, v)| v).sum();
        let total = bd["total"];
        assert!((sum - total).abs() < 0.001, "sum {} != total {}", sum, total);
    }

    // ── compare ───────────────────────────────────────────────────────────────

    #[test]
    fn test_compare_stable() {
        assert_eq!(compare("nondecreasing", 5.0, 5.0), "stable");
    }

    #[test]
    fn test_compare_improved_nondecreasing() {
        assert_eq!(compare("nondecreasing", 6.0, 5.0), "improved");
    }

    #[test]
    fn test_compare_regressed_nondecreasing() {
        assert_eq!(compare("nondecreasing", 4.0, 5.0), "regressed");
    }

    #[test]
    fn test_compare_improved_nonincreasing() {
        assert_eq!(compare("nonincreasing", 4.0, 5.0), "improved");
    }

    // ── objective_is_eligible ─────────────────────────────────────────────────

    #[test]
    fn test_eligible_product_scope() {
        let mut state = make_state();
        let obj = json!({"id": "g1", "scope": "product", "status": "planned"});
        assert!(objective_is_eligible(&mut state, &obj));
    }

    #[test]
    fn test_not_eligible_runtime_no_evidence() {
        let mut state = make_state();
        let obj = json!({"id": "g1", "scope": "runtime", "status": "planned", "necessity_evidence": "", "lower_impact_route_sufficient": false});
        assert!(!objective_is_eligible(&mut state, &obj));
    }

    #[test]
    fn test_eligible_runtime_with_evidence() {
        let mut state = make_state();
        let obj = json!({
            "id": "g1", "scope": "runtime", "status": "planned",
            "necessity_evidence": "disk space at 95%",
            "lower_impact_route_sufficient": false,
        });
        assert!(objective_is_eligible(&mut state, &obj));
    }

    #[test]
    fn test_capability_defining_blocked_at_capable() {
        let mut state = make_state();
        state["sweet_spot_assessments"] = json!([{"maturity_level": "CAPABLE"}]);
        let obj = json!({"id": "g-cap", "kind": "CAPABILITY_DEFINING", "scope": "product", "title": "New cap"});
        assert!(!objective_is_eligible(&mut state, &obj));
        // Should have recorded an integrity gap
        let gaps = state["integrity_gaps"].as_array().unwrap();
        assert!(!gaps.is_empty());
        assert_eq!(gaps[0]["kind"].as_str(), Some("capability-envelope-breach"));
    }

    // ── vitals_snapshot ───────────────────────────────────────────────────────

    #[test]
    fn test_vitals_snapshot_fields() {
        let config = make_config();
        let state = make_state();
        let vs = vitals_snapshot(&config, &state);
        assert_eq!(vs.lifecycle_state, "ACTIVE");
        assert_eq!(vs.aps_score, 72.5);
        assert_eq!(vs.cycle_count, 5);
        assert_eq!(vs.objectives_count, 0);
        assert_eq!(vs.evidence_count, 0);
        assert!(vs.last_cycle_at.is_none());
    }

    #[test]
    fn test_vitals_snapshot_with_objectives() {
        let config = make_config();
        let mut state = make_state();
        state["objectives"] = json!([
            {"id": "o1", "title": "First", "scope": "product", "status": "planned", "priority": 60},
            {"id": "o2", "title": "Second", "scope": "product", "status": "completed", "priority": 40},
        ]);
        let vs = vitals_snapshot(&config, &state);
        assert_eq!(vs.objectives_count, 2);
        // goal_portfolio should have 2 entries
        let goals = vs.goal_portfolio["goals"].as_array().unwrap();
        assert_eq!(goals.len(), 2);
    }

    #[test]
    fn test_vitals_snapshot_full_shape() {
        let config = make_config();
        let state = make_state();
        let full = vitals_snapshot_full(&config, &state);
        assert_eq!(full["type"].as_str(), Some("urace_vitals"));
        assert!(full["executor_credit_usage"].is_object());
        assert!(full["health"].is_object());
        assert!(full["objective_outcomes"].is_object());
    }
}
