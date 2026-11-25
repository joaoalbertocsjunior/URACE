//! k9s-style TUI dashboard for URACE.
//!
//! All render functions are pure — no side effects, no I/O.
//! State is passed in; the TUI only renders what it receives.

pub mod app;
pub mod command_dispatch;
pub mod event_handler;
pub mod ui;
pub mod vitals_collector;

pub use app::{App, Panel, SettlementEntry, SourceEntry, WorkTask};
pub use event_handler::{handle_key_event, AppEvent};
pub use ui::render;
