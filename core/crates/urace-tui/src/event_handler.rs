//! Keyboard event handling for the TUI.
//!
//! Maps crossterm key events to `AppEvent` values that callers apply to `App`.
//! This module contains no I/O — it converts key codes to domain events.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

/// High-level application events derived from raw key presses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AppEvent {
    /// User pressed q (or Ctrl-C) — application should exit.
    Quit,
    /// Tab — switch to next panel.
    NextPanel,
    /// Arrow up — move cursor up.
    CursorUp,
    /// Arrow down — move cursor down.
    CursorDown,
    /// r — request a data refresh.
    Refresh,
    /// Any other key — no-op.
    None,
}

/// Translate a crossterm `KeyEvent` into an `AppEvent`.
///
/// This function is pure: given the same key event it always returns the same result.
pub fn handle_key_event(key: KeyEvent) -> AppEvent {
    match key.code {
        // q without modifiers → quit; Ctrl-C always quits.
        KeyCode::Char('q') if key.modifiers == KeyModifiers::NONE => AppEvent::Quit,
        KeyCode::Char('c') if key.modifiers == KeyModifiers::CONTROL => AppEvent::Quit,
        // Tab → switch panel.
        KeyCode::Tab => AppEvent::NextPanel,
        // Navigation.
        KeyCode::Up   | KeyCode::Char('k') => AppEvent::CursorUp,
        KeyCode::Down | KeyCode::Char('j') => AppEvent::CursorDown,
        // r → refresh.
        KeyCode::Char('r') if key.modifiers == KeyModifiers::NONE => AppEvent::Refresh,
        _ => AppEvent::None,
    }
}

/// Apply an `AppEvent` to the mutable `App` state.
pub fn apply_event(event: AppEvent, app: &mut crate::app::App) {
    match event {
        AppEvent::Quit       => app.should_quit = true,
        AppEvent::NextPanel  => app.next_panel(),
        AppEvent::CursorUp   => app.cursor_up(),
        AppEvent::CursorDown => app.cursor_down(),
        AppEvent::Refresh    => app.status_message = "refreshing…".into(),
        AppEvent::None       => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use crate::app::App;

    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::NONE)
    }

    #[test]
    fn q_maps_to_quit() {
        assert_eq!(handle_key_event(key(KeyCode::Char('q'))), AppEvent::Quit);
    }

    #[test]
    fn tab_maps_to_next_panel() {
        assert_eq!(handle_key_event(key(KeyCode::Tab)), AppEvent::NextPanel);
    }

    #[test]
    fn up_down_navigate() {
        assert_eq!(handle_key_event(key(KeyCode::Up)),   AppEvent::CursorUp);
        assert_eq!(handle_key_event(key(KeyCode::Down)), AppEvent::CursorDown);
    }

    #[test]
    fn r_maps_to_refresh() {
        assert_eq!(handle_key_event(key(KeyCode::Char('r'))), AppEvent::Refresh);
    }

    #[test]
    fn apply_quit_sets_flag() {
        let mut app = App::new();
        apply_event(AppEvent::Quit, &mut app);
        assert!(app.should_quit);
    }
}
