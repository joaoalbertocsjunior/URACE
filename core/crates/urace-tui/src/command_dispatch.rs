//! Inline command dispatch for the TUI command bar.
//!
//! Mirrors the Python `route_input()` function in `tui.py`.
//! All functions in this module are pure (no I/O, no side effects).

/// A high-level TUI command parsed from a user-typed string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TuiCommand {
    // ── Navigation ────────────────────────────────────────────────────────────
    /// Switch to the named tab / panel.
    SwitchTab(String),
    /// Exit the TUI.
    Quit,
    /// Trigger a live data refresh.
    Refresh,

    // ── State queries (safe, read-only) ───────────────────────────────────────
    /// Show the vitals / diagnostic score panel.
    ShowVitals,
    /// Show the goals / objectives panel.
    ShowGoals,
    /// Show the audit / event log panel.
    ShowAudit,
    /// Show the sources panel.
    ShowSources,

    // ── Help ──────────────────────────────────────────────────────────────────
    /// Display the help text.
    Help,

    // ── Fallthrough ───────────────────────────────────────────────────────────
    /// Input that did not match any known command.
    Unknown(String),
}

/// Parse a user-typed command string into a [`TuiCommand`].
///
/// Matching is case-sensitive and whitespace-normalised.
/// Mirrors the Python `route_input()` behaviour documented in `tui.py`.
pub fn parse_command(input: &str) -> TuiCommand {
    let trimmed = input.trim();
    let parts: Vec<&str> = trimmed.split_whitespace().collect();

    match parts.as_slice() {
        // ── quit ──────────────────────────────────────────────────────────────
        ["q"] | ["quit"] | ["exit"] => TuiCommand::Quit,

        // ── refresh ───────────────────────────────────────────────────────────
        ["r"] | ["refresh"] => TuiCommand::Refresh,

        // ── vitals ────────────────────────────────────────────────────────────
        ["vitals"] | ["v"] => TuiCommand::ShowVitals,

        // ── goals ─────────────────────────────────────────────────────────────
        ["goals"] | ["g"] => TuiCommand::ShowGoals,

        // ── audit ─────────────────────────────────────────────────────────────
        ["audit"] | ["a"] => TuiCommand::ShowAudit,

        // ── sources ───────────────────────────────────────────────────────────
        ["sources"] | ["s"] => TuiCommand::ShowSources,

        // ── help ──────────────────────────────────────────────────────────────
        ["help"] | ["h"] | ["?"] => TuiCommand::Help,

        // ── tab switch ────────────────────────────────────────────────────────
        ["tab", name] => TuiCommand::SwitchTab((*name).to_string()),

        // ── unknown / NLP fallthrough ─────────────────────────────────────────
        _ => TuiCommand::Unknown(trimmed.to_string()),
    }
}

/// Help text shown in the TUI command bar when the user types `help` or `?`.
pub fn help_text() -> &'static str {
    "Commands: vitals(v) goals(g) audit(a) sources(s) tab <name> refresh(r) quit(q) help(?)"
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── quit variants ─────────────────────────────────────────────────────────

    #[test]
    fn quit_short() {
        assert_eq!(parse_command("q"), TuiCommand::Quit);
    }

    #[test]
    fn quit_long() {
        assert_eq!(parse_command("quit"), TuiCommand::Quit);
    }

    #[test]
    fn exit_maps_to_quit() {
        assert_eq!(parse_command("exit"), TuiCommand::Quit);
    }

    // ── refresh ───────────────────────────────────────────────────────────────

    #[test]
    fn refresh_short() {
        assert_eq!(parse_command("r"), TuiCommand::Refresh);
    }

    #[test]
    fn refresh_long() {
        assert_eq!(parse_command("refresh"), TuiCommand::Refresh);
    }

    // ── vitals ────────────────────────────────────────────────────────────────

    #[test]
    fn vitals_short() {
        assert_eq!(parse_command("v"), TuiCommand::ShowVitals);
    }

    #[test]
    fn vitals_long() {
        assert_eq!(parse_command("vitals"), TuiCommand::ShowVitals);
    }

    // ── goals ─────────────────────────────────────────────────────────────────

    #[test]
    fn goals_short() {
        assert_eq!(parse_command("g"), TuiCommand::ShowGoals);
    }

    #[test]
    fn goals_long() {
        assert_eq!(parse_command("goals"), TuiCommand::ShowGoals);
    }

    // ── audit ─────────────────────────────────────────────────────────────────

    #[test]
    fn audit_short() {
        assert_eq!(parse_command("a"), TuiCommand::ShowAudit);
    }

    #[test]
    fn audit_long() {
        assert_eq!(parse_command("audit"), TuiCommand::ShowAudit);
    }

    // ── sources ───────────────────────────────────────────────────────────────

    #[test]
    fn sources_short() {
        assert_eq!(parse_command("s"), TuiCommand::ShowSources);
    }

    #[test]
    fn sources_long() {
        assert_eq!(parse_command("sources"), TuiCommand::ShowSources);
    }

    // ── help ──────────────────────────────────────────────────────────────────

    #[test]
    fn help_long() {
        assert_eq!(parse_command("help"), TuiCommand::Help);
    }

    #[test]
    fn help_short_h() {
        assert_eq!(parse_command("h"), TuiCommand::Help);
    }

    #[test]
    fn help_question_mark() {
        assert_eq!(parse_command("?"), TuiCommand::Help);
    }

    // ── tab switch ────────────────────────────────────────────────────────────

    #[test]
    fn tab_switch() {
        assert_eq!(
            parse_command("tab sources"),
            TuiCommand::SwitchTab("sources".to_string())
        );
    }

    #[test]
    fn tab_switch_arbitrary_name() {
        assert_eq!(
            parse_command("tab logs"),
            TuiCommand::SwitchTab("logs".to_string())
        );
    }

    // ── unknown ───────────────────────────────────────────────────────────────

    #[test]
    fn unknown_string_preserved() {
        assert_eq!(
            parse_command("unknown xyz"),
            TuiCommand::Unknown("unknown xyz".to_string())
        );
    }

    #[test]
    fn empty_input_is_unknown() {
        // An empty string doesn't match any command.
        assert_eq!(
            parse_command(""),
            TuiCommand::Unknown("".to_string())
        );
    }

    #[test]
    fn leading_trailing_whitespace_stripped() {
        assert_eq!(parse_command("  quit  "), TuiCommand::Quit);
    }

    // ── help text is non-empty ────────────────────────────────────────────────

    #[test]
    fn help_text_not_empty() {
        assert!(!help_text().is_empty());
    }
}
