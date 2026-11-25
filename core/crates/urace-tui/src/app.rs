//! TUI application state.
//!
//! `App` is a plain data struct — no I/O, no async calls.
//! All fields are set by the caller before each render pass.

use std::path::Path;
use serde::{Deserialize, Serialize};

use crate::command_dispatch::{self, TuiCommand};
use crate::vitals_collector::{self, LiveVitals};

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

    // ── vitals ──────────────────────────────────────────────────────────────

    /// Live vitals collected from state files on the last refresh.
    pub vitals: LiveVitals,

    // ── inline command bar ───────────────────────────────────────────────────

    /// Text the user is currently typing in the command bar.
    pub command_input: String,

    /// One-line feedback from the last dispatched command (shown in status bar).
    pub command_result: Option<String>,
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

    /// Refresh [`LiveVitals`] by reading state files under `root`.
    ///
    /// Also syncs `self.lifecycle` from the freshly collected vitals so the
    /// title bar always reflects the current state without a separate read.
    pub fn refresh_vitals(&mut self, root: &Path) {
        self.vitals = vitals_collector::collect(root);
        // Keep the existing top-level `lifecycle` field in sync.
        self.lifecycle = self.vitals.lifecycle_state.clone();
    }

    /// Parse and dispatch an inline command typed in the command bar.
    ///
    /// Updates `self.active_panel`, `self.should_quit`, and
    /// `self.command_result` as appropriate.  Navigation commands that name an
    /// unknown panel are silently ignored (no panic).
    pub fn dispatch_command(&mut self, cmd: &str) {
        let parsed = command_dispatch::parse_command(cmd);
        match parsed {
            TuiCommand::Quit => {
                self.should_quit = true;
                self.command_result = Some("quit".into());
            }
            TuiCommand::Refresh => {
                // Caller is responsible for calling `refresh_vitals`; here we
                // just set a status message so the UI knows what happened.
                self.command_result = Some("refreshing…".into());
            }
            TuiCommand::ShowVitals => {
                // No dedicated Vitals panel yet — show the status message so
                // the user gets feedback, and future callers can wire up a
                // panel switch here.
                self.command_result = Some("vitals — see vitals field".into());
            }
            TuiCommand::ShowGoals => {
                self.command_result = Some("goals — see work_queue panel".into());
            }
            TuiCommand::ShowAudit => {
                self.active_panel = Panel::Logs;
                self.cursor = 0;
                self.command_result = Some("switched to Logs panel".into());
            }
            TuiCommand::ShowSources => {
                self.active_panel = Panel::Sources;
                self.cursor = 0;
                self.command_result = Some("switched to Sources panel".into());
            }
            TuiCommand::SwitchTab(ref name) => {
                let panel = match name.to_lowercase().as_str() {
                    "sources"    => Some(Panel::Sources),
                    "workqueue" | "work_queue" | "work queue" | "queue" => {
                        Some(Panel::WorkQueue)
                    }
                    "settlement" => Some(Panel::Settlement),
                    "logs"       => Some(Panel::Logs),
                    _            => None,
                };
                if let Some(p) = panel {
                    self.active_panel = p;
                    self.cursor = 0;
                    self.command_result = Some(format!("switched to {}", p.title()));
                } else {
                    self.command_result =
                        Some(format!("unknown tab: {name}"));
                }
            }
            TuiCommand::Help => {
                self.command_result = Some(command_dispatch::help_text().into());
            }
            TuiCommand::Unknown(ref text) => {
                if text.is_empty() {
                    self.command_result = None;
                } else {
                    self.command_result =
                        Some(format!("unknown command: {text}"));
                }
            }
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
