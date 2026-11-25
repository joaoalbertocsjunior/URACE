//! Protocol for selecting the next objective to pursue.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// The result of a goal selection pass.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelectedGoal {
    /// Stable identifier for this goal.
    pub id: String,
    /// Human-readable title.
    pub title: String,
    /// Arbitrary goal metadata preserved from the config entry.
    pub extra: HashMap<String, serde_json::Value>,
}

/// Trait for selecting the next objective.
pub trait GoalSelector: Send + Sync {
    /// Return the chosen goal, or `None` when nothing is pending.
    ///
    /// Implementations may record selection metadata in `state`.
    fn select(
        &self,
        config: &serde_json::Value,
        state: &mut serde_json::Value,
    ) -> Option<SelectedGoal>;
}

/// Default selector: picks the first goal from `config["goals"]` whose
/// `status` field is `"pending"` (or absent).
pub struct DefaultGoalSelector;

impl GoalSelector for DefaultGoalSelector {
    fn select(
        &self,
        config: &serde_json::Value,
        state: &mut serde_json::Value,
    ) -> Option<SelectedGoal> {
        let goals = config.get("goals")?.as_array()?;
        for entry in goals {
            let status = entry
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("pending");
            if status == "pending" {
                let id = entry.get("id")?.as_str()?.to_owned();
                let title = entry
                    .get("title")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_owned();
                let extra: HashMap<String, serde_json::Value> = entry
                    .as_object()
                    .map(|m| {
                        m.iter()
                            .filter(|(k, _)| k.as_str() != "id" && k.as_str() != "title")
                            .map(|(k, v)| (k.clone(), v.clone()))
                            .collect()
                    })
                    .unwrap_or_default();

                // Record the selection in state so callers can observe it.
                if let Some(obj) = state.as_object_mut() {
                    obj.insert(
                        "current_objective".to_owned(),
                        serde_json::Value::String(id.clone()),
                    );
                }

                return Some(SelectedGoal { id, title, extra });
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn selector() -> DefaultGoalSelector {
        DefaultGoalSelector
    }

    #[test]
    fn returns_first_pending_goal() {
        let config = json!({"goals": [{"id": "g1", "title": "First", "status": "pending"}]});
        let mut state = json!({});
        let result = selector().select(&config, &mut state).unwrap();
        assert_eq!(result.id, "g1");
        assert_eq!(result.title, "First");
    }

    #[test]
    fn skips_non_pending() {
        let config = json!({"goals": [
            {"id": "g1", "title": "Done", "status": "complete"},
            {"id": "g2", "title": "Next", "status": "pending"}
        ]});
        let mut state = json!({});
        let result = selector().select(&config, &mut state).unwrap();
        assert_eq!(result.id, "g2");
    }

    #[test]
    fn returns_none_when_all_complete() {
        let config = json!({"goals": [{"id": "g1", "status": "complete"}]});
        let mut state = json!({});
        assert!(selector().select(&config, &mut state).is_none());
    }

    #[test]
    fn records_selection_in_state() {
        let config = json!({"goals": [{"id": "goal-42", "title": "T", "status": "pending"}]});
        let mut state = json!({});
        selector().select(&config, &mut state);
        assert_eq!(state["current_objective"], "goal-42");
    }

    #[test]
    fn no_goals_key_returns_none() {
        let config = json!({});
        let mut state = json!({});
        assert!(selector().select(&config, &mut state).is_none());
    }
}
