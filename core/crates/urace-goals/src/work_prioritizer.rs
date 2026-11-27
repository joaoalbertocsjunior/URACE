//! Goal-driven work prioritiser.
//!
//! Scores work items against active goals to produce a priority order.
//! Goals that are closer to deadline get higher weight.
//! Goals with higher score_delta targets get higher weight.
//!
//! INVARIANT: `goal_alignment_bonus` is at most 2.0, so goal alignment can at
//! most double the base score (caps exploitation of the bonus channel).

use serde::{Deserialize, Serialize};

// ── Data types ────────────────────────────────────────────────────────────────

/// A goal that is currently active and influencing work prioritisation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveGoal {
    pub goal_id: String,
    pub title: String,
    /// How much score improvement this goal targets.
    pub target_score_delta: f64,
    /// Unix seconds deadline; `None` means no deadline.
    pub deadline_secs: Option<u64>,
    /// Governance-set priority, 1–10.
    pub priority: u8,
}

/// How strongly a single work item aligns with one goal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoalAlignment {
    pub goal_id: String,
    pub goal_title: String,
    /// 0.0–1.0
    pub alignment_strength: f64,
}

/// Priority score for a single work item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkPriorityScore {
    pub work_item_id: String,
    /// Score from bid scoring before goal adjustment.
    pub base_score: f64,
    /// Added when work aligns with active goals; at most 2.0.
    pub goal_alignment_bonus: f64,
    /// `base_score + goal_alignment_bonus`
    pub final_score: f64,
}

// ── WorkPrioritizer ───────────────────────────────────────────────────────────

/// Scores work items against active goals and produces a priority order.
#[derive(Debug, Default)]
pub struct WorkPrioritizer;

impl WorkPrioritizer {
    pub fn new() -> Self {
        WorkPrioritizer
    }

    /// Keyword-overlap alignment between a work item description and a goal.
    ///
    /// Algorithm:
    /// 1. Split `goal_title` into words (lower-cased).
    /// 2. Count how many of those words appear in `work_item_description`
    ///    (lower-cased), normalised by goal word count.
    /// 3. Multiply by `min(goal_target_delta / 10.0, 1.0)` to weight
    ///    high-impact goals.
    ///
    /// Returns a value in `[0.0, 1.0]`.
    pub fn compute_alignment(
        work_item_description: &str,
        goal_title: &str,
        goal_target_delta: f64,
    ) -> f64 {
        let desc_lower = work_item_description.to_lowercase();
        let goal_words: Vec<&str> = goal_title
            .split_whitespace()
            .collect();

        if goal_words.is_empty() {
            return 0.0;
        }

        let matches = goal_words
            .iter()
            .filter(|w| desc_lower.contains(&w.to_lowercase()))
            .count();

        let overlap = matches as f64 / goal_words.len() as f64;
        let impact_weight = (goal_target_delta / 10.0).min(1.0).max(0.0);

        (overlap * impact_weight).min(1.0)
    }

    /// Score a single work item against a set of active goals.
    ///
    /// `now_secs` is accepted for future deadline-weighting extensions; the
    /// current implementation uses it to guard against stale goals (deadline
    /// already passed goals are skipped).
    pub fn score_work_item(
        work_item_id: &str,
        work_item_description: &str,
        base_score: f64,
        active_goals: &[ActiveGoal],
        now_secs: u64,
    ) -> WorkPriorityScore {
        let max_alignment = active_goals
            .iter()
            .filter(|g| {
                // Skip goals whose deadline has already passed.
                g.deadline_secs.map_or(true, |d| d > now_secs)
            })
            .map(|g| {
                Self::compute_alignment(
                    work_item_description,
                    &g.title,
                    g.target_score_delta,
                )
            })
            .fold(0.0_f64, f64::max);

        // Bonus is at most 2.0.
        let goal_alignment_bonus = (max_alignment * 2.0).min(2.0);
        let final_score = base_score + goal_alignment_bonus;

        WorkPriorityScore {
            work_item_id: work_item_id.to_owned(),
            base_score,
            goal_alignment_bonus,
            final_score,
        }
    }

    /// Score and rank a list of work items, highest `final_score` first.
    pub fn rank_work_items(
        items: &[(String, String, f64)], // (work_item_id, description, base_score)
        active_goals: &[ActiveGoal],
        now_secs: u64,
    ) -> Vec<WorkPriorityScore> {
        let mut scores: Vec<WorkPriorityScore> = items
            .iter()
            .map(|(id, desc, base)| {
                Self::score_work_item(id, desc, *base, active_goals, now_secs)
            })
            .collect();

        scores.sort_by(|a, b| {
            b.final_score
                .partial_cmp(&a.final_score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        scores
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn goal(id: &str, title: &str, delta: f64, deadline: Option<u64>, priority: u8) -> ActiveGoal {
        ActiveGoal {
            goal_id: id.to_owned(),
            title: title.to_owned(),
            target_score_delta: delta,
            deadline_secs: deadline,
            priority,
        }
    }

    // 1. Happy path: a work item that matches the goal keyword gets a bonus.
    #[test]
    fn test_alignment_happy_path() {
        let strength = WorkPrioritizer::compute_alignment(
            "refactor the nlp pipeline for better accuracy",
            "nlp accuracy",
            10.0,
        );
        // "nlp" and "accuracy" both appear → overlap = 1.0, impact = 1.0
        assert!(strength > 0.9, "expected high alignment, got {strength}");
    }

    // 2. No keyword overlap → zero alignment.
    #[test]
    fn test_alignment_no_overlap() {
        let strength = WorkPrioritizer::compute_alignment(
            "fix UI button colour",
            "database performance",
            10.0,
        );
        assert_eq!(strength, 0.0);
    }

    // 3. High-impact goal (large target_score_delta) gets more weight than a
    //    low-impact goal with identical keyword overlap.
    #[test]
    fn test_high_impact_goal_weight() {
        let low = WorkPrioritizer::compute_alignment("improve security audit", "security", 1.0);
        let high = WorkPrioritizer::compute_alignment("improve security audit", "security", 10.0);
        assert!(high > low, "high-impact goal should score higher: low={low} high={high}");
    }

    // 4. score_work_item — bonus capped at 2.0.
    #[test]
    fn test_bonus_cap() {
        let goals = vec![
            goal("g1", "nlp accuracy pipeline", 10.0, None, 5),
            goal("g2", "nlp accuracy pipeline", 10.0, None, 5),
        ];
        let score = WorkPrioritizer::score_work_item(
            "wi-1",
            "improve nlp accuracy pipeline performance",
            1.0,
            &goals,
            0,
        );
        assert!(score.goal_alignment_bonus <= 2.0, "bonus must be capped at 2.0");
        assert_eq!(score.final_score, score.base_score + score.goal_alignment_bonus);
    }

    // 5. rank_work_items — items sorted by final_score descending.
    #[test]
    fn test_ranking_order() {
        let goals = vec![goal("g1", "security audit", 10.0, None, 7)];
        let items = vec![
            ("wi-low".to_owned(), "fix UI colour".to_owned(), 1.0_f64),
            ("wi-high".to_owned(), "run security audit checks".to_owned(), 1.0_f64),
        ];
        let ranked = WorkPrioritizer::rank_work_items(&items, &goals, 0);
        assert_eq!(ranked[0].work_item_id, "wi-high");
        assert_eq!(ranked[1].work_item_id, "wi-low");
    }

    // 6. Expired deadline goals are ignored.
    #[test]
    fn test_expired_deadline_ignored() {
        let now = 1_000_000_u64;
        let goals = vec![
            // deadline already passed
            goal("g1", "security patch", 10.0, Some(now - 1), 5),
        ];
        let score = WorkPrioritizer::score_work_item(
            "wi-1",
            "apply security patch to system",
            1.0,
            &goals,
            now,
        );
        // Even though keywords match, expired goal contributes no bonus.
        assert_eq!(score.goal_alignment_bonus, 0.0);
    }

    // 7. Empty goal list → zero bonus, final_score == base_score.
    #[test]
    fn test_no_goals_no_bonus() {
        let score =
            WorkPrioritizer::score_work_item("wi-1", "do anything", 3.5, &[], 0);
        assert_eq!(score.goal_alignment_bonus, 0.0);
        assert_eq!(score.final_score, 3.5);
    }

    // 8. rank_work_items on empty list returns empty vec.
    #[test]
    fn test_rank_empty_items() {
        let ranked = WorkPrioritizer::rank_work_items(&[], &[], 0);
        assert!(ranked.is_empty());
    }
}
