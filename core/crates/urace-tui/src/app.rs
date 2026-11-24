//! TUI application state.
//!
//! `App` is a plain data struct — no I/O, no async calls.
//! All fields are set by the caller before each render pass.

use serde::{Deserialize, Serialize};

/// Which panel currently has keyboard focus.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum Panel {
    #[default]
    Sources,
    WorkQueue,
    Settlement,
    Logs,
}

impl Panel {
    /// Cycle to the next panel (tab key).
    pub fn next(self) -> Self {
        match self {
            Panel::Sources    => Panel::WorkQueue,
            Panel::WorkQueue  => Panel::Settlement,
            Panel::Settlement => Panel::Logs,
            Panel::Logs       => Panel::Sources,
        }
    }

    pub fn title(self) -> &'static str {
        match self {
            Panel::Sources    => "Sources",
            Panel::WorkQueue  => "Work Queue",
            Panel::Settlement => "Settlement",
            Panel::Logs       => "Logs",
        }
    }
}

/// A registered source and its current sync status.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SourceEntry {
    pub name: String,
    pub kind: String,
    pub status: String,
    pub last_sync: Option<String>,
}

/// A pending or active work task.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct WorkTask {
    pub id: String,
    pub description: String,
    pub status: String,
    pub started_at: Option<String>,
}

/// A recent settlement result.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SettlementEntry {
    pub id: String,
    pub amount: String,
    pub status: String,
    pub settled_at: String,
}

/// Full TUI application state.
///
/// Callers populate this before each render call.
/// The TUI never modifies any external state.
#[derive(Debug, Clone, Default)]
pub struct App {
    /// Currently focused panel.
    pub active_panel: Panel,

    /// Current cursor position within the focused panel's list.
    pub cursor: usize,

    /// Whether the application should quit on the next event loop iteration.
    pub should_quit: bool,

    // ── panel data ──────────────────────────────────────────────────────────

    /// Registered sources with sync status.
    pub sources: Vec<SourceEntry>,

    /// Pending and active work tasks.
    pub work_queue: Vec<WorkTask>,

    /// Recent settlement results.
    pub settlements: Vec<SettlementEntry>,

    /// Last N log lines for the log panel.
    pub log_lines: Vec<String>,

    // ── status bar ──────────────────────────────────────────────────────────

    /// Short status message shown in the status bar (e.g. "refreshed").
    pub status_message: String,

    /// Runtime lifecycle state from the daemon.
    pub lifecycle: String,

    /// URACE runtime version string.
    pub version: String,
}

impl App {
    /// Create a new `App` with default (empty) state.
    pub fn new() -> Self {
        Self {
            version: "dev".into(),
            lifecycle: "UNKNOWN".into(),
            ..Default::default()
        }
    }

    /// Return the number of items in the currently focused panel.
    pub fn current_len(&self) -> usize {
        match self.active_panel {
            Panel::Sources    => self.sources.len(),
            Panel::WorkQueue  => self.work_queue.len(),
            Panel::Settlement => self.settlements.len(),
            Panel::Logs       => self.log_lines.len(),
        }
    }

    /// Move cursor up by one, saturating at 0.
    pub fn cursor_up(&mut self) {
        self.cursor = self.cursor.saturating_sub(1);
    }

    /// Move cursor down by one, clamped to the list length.
    pub fn cursor_down(&mut self) {
        let max = self.current_len().saturating_sub(1);
        if self.cursor < max {
            self.cursor += 1;
        }
    }

    /// Switch to the next panel and reset cursor.
    pub fn next_panel(&mut self) {
        self.active_panel = self.active_panel.next();
        self.cursor = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_new_does_not_panic() {
        let app = App::new();
        assert_eq!(app.active_panel, Panel::Sources);
        assert!(!app.should_quit);
    }

    #[test]
    fn panel_cycle() {
        assert_eq!(Panel::Sources.next(), Panel::WorkQueue);
        assert_eq!(Panel::WorkQueue.next(), Panel::Settlement);
        assert_eq!(Panel::Settlement.next(), Panel::Logs);
        assert_eq!(Panel::Logs.next(), Panel::Sources);
    }

    #[test]
    fn cursor_does_not_overflow_empty() {
        let mut app = App::new();
        app.cursor_down(); // empty list — should stay at 0
        assert_eq!(app.cursor, 0);
        app.cursor_up();
        assert_eq!(app.cursor, 0);
    }
}
