//! Workflow state machine — Pending → Running → Completed/Failed/Cancelled.
//!
//! Ported from `workflow_state.py`. Transitions are validated; illegal moves
//! return `WorkflowError::InvalidTransition`.

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum WorkflowError {
    #[error("invalid state transition from {from:?} to {to:?}")]
    InvalidTransition {
        from: WorkflowState,
        to: WorkflowState,
    },
    #[error("workflow {id} not found")]
    NotFound { id: String },
}

/// Workflow execution states.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkflowState {
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
}

impl WorkflowState {
    /// True if this is a terminal state (no further transitions allowed).
    pub fn is_terminal(self) -> bool {
        matches!(
            self,
            WorkflowState::Completed | WorkflowState::Failed | WorkflowState::Cancelled
        )
    }

    /// Returns `Ok(next_state)` if the transition is valid, else `Err`.
    pub fn transition(self, next: WorkflowState) -> Result<WorkflowState, WorkflowError> {
        use WorkflowState::*;
        let allowed = match self {
            Pending => matches!(next, Running | Cancelled),
            Running => matches!(next, Completed | Failed | Cancelled),
            Completed | Failed | Cancelled => false,
        };
        if allowed {
            Ok(next)
        } else {
            Err(WorkflowError::InvalidTransition {
                from: self,
                to: next,
            })
        }
    }
}

/// A named transition event with a timestamp.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowTransition {
    pub from: WorkflowState,
    pub to: WorkflowState,
    pub at_unix: f64,
    pub note: Option<String>,
}

/// A single workflow execution record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowRecord {
    pub id: String,
    pub name: String,
    pub state: WorkflowState,
    pub created_at: f64,
    pub updated_at: f64,
    pub transitions: Vec<WorkflowTransition>,
}

impl WorkflowRecord {
    pub fn new(name: impl Into<String>) -> Self {
        let now = now_unix();
        WorkflowRecord {
            id: Uuid::new_v4().to_string(),
            name: name.into(),
            state: WorkflowState::Pending,
            created_at: now,
            updated_at: now,
            transitions: vec![],
        }
    }

    /// Attempt a transition; returns the new record on success.
    pub fn transition(
        mut self,
        next: WorkflowState,
        note: Option<String>,
    ) -> Result<Self, WorkflowError> {
        let new_state = self.state.transition(next)?;
        let now = now_unix();
        self.transitions.push(WorkflowTransition {
            from: self.state,
            to: new_state,
            at_unix: now,
            note,
        });
        self.state = new_state;
        self.updated_at = now;
        Ok(self)
    }
}

fn now_unix() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_transitions() {
        let r = WorkflowRecord::new("job-1");
        assert_eq!(r.state, WorkflowState::Pending);
        let r = r.transition(WorkflowState::Running, None).unwrap();
        assert_eq!(r.state, WorkflowState::Running);
        let r = r
            .transition(WorkflowState::Completed, Some("done".into()))
            .unwrap();
        assert_eq!(r.state, WorkflowState::Completed);
        assert!(r.state.is_terminal());
    }

    #[test]
    fn invalid_transition_terminal() {
        let r = WorkflowRecord::new("job-2")
            .transition(WorkflowState::Running, None)
            .unwrap()
            .transition(WorkflowState::Completed, None)
            .unwrap();
        let err = r.transition(WorkflowState::Running, None).unwrap_err();
        assert!(matches!(err, WorkflowError::InvalidTransition { .. }));
    }

    #[test]
    fn skip_running_blocked() {
        let r = WorkflowRecord::new("job-3");
        let err = r.transition(WorkflowState::Completed, None).unwrap_err();
        assert!(matches!(err, WorkflowError::InvalidTransition { .. }));
    }

    #[test]
    fn cancel_from_pending() {
        let r = WorkflowRecord::new("job-4");
        let r = r.transition(WorkflowState::Cancelled, None).unwrap();
        assert_eq!(r.state, WorkflowState::Cancelled);
    }

    #[test]
    fn transition_history_recorded() {
        let r = WorkflowRecord::new("job-5")
            .transition(WorkflowState::Running, None)
            .unwrap()
            .transition(WorkflowState::Failed, Some("oops".into()))
            .unwrap();
        assert_eq!(r.transitions.len(), 2);
        assert_eq!(r.transitions[1].note.as_deref(), Some("oops"));
    }
}
