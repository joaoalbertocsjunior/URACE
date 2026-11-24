//! Pure render functions using ratatui widgets.
//!
//! All functions in this module are pure: they take `&App` and a mutable
//! ratatui `Frame`, and produce no side effects beyond writing to the frame.

use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Cell, List, ListItem, ListState, Paragraph, Row, Table},
};

use crate::app::{App, Panel};

/// Render the full TUI layout into `frame`.
///
/// Layout (top-to-bottom):
///   - Title bar (1 line)
///   - Main area: left column (Sources + Work Queue) | right column (Settlement + Logs)
///   - Status bar (1 line)
pub fn render(frame: &mut Frame, app: &App) {
    let area = frame.area();

    // Outer: title bar / body / status bar
    let outer = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1), // title
            Constraint::Min(0),    // body
            Constraint::Length(1), // status bar
        ])
        .split(area);

    render_title(frame, app, outer[0]);
    render_body(frame, app, outer[1]);
    render_status(frame, app, outer[2]);
}

// ── title bar ────────────────────────────────────────────────────────────────

fn render_title(frame: &mut Frame, app: &App, area: Rect) {
    let title = Paragraph::new(Line::from(vec![
        Span::styled(
            format!(" URACE {} ", app.version),
            Style::default()
                .fg(Color::White)
                .bg(Color::Blue)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            format!(" lifecycle: {} ", app.lifecycle),
            Style::default().fg(Color::Cyan).bg(Color::Blue),
        ),
    ]));
    frame.render_widget(title, area);
}

// ── body (four panels in a 2×2 grid) ────────────────────────────────────────

fn render_body(frame: &mut Frame, app: &App, area: Rect) {
    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(area);

    let left = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(columns[0]);

    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(columns[1]);

    render_sources(frame, app, left[0]);
    render_work_queue(frame, app, left[1]);
    render_settlement(frame, app, right[0]);
    render_logs(frame, app, right[1]);
}

// ── Sources panel ────────────────────────────────────────────────────────────

fn render_sources(frame: &mut Frame, app: &App, area: Rect) {
    let focused = app.active_panel == Panel::Sources;
    let block = panel_block("Sources", focused);

    let header = Row::new(["Name", "Kind", "Status", "Last Sync"].map(|h| {
        Cell::from(h).style(Style::default().add_modifier(Modifier::BOLD))
    }))
    .bottom_margin(1);

    let rows: Vec<Row> = app
        .sources
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let style = if focused && i == app.cursor {
                Style::default().fg(Color::Black).bg(Color::Cyan)
            } else {
                Style::default()
            };
            let status_color = match s.status.as_str() {
                "ok" | "synced"  => Color::Green,
                "error" | "fail" => Color::Red,
                _                => Color::Yellow,
            };
            Row::new([
                Cell::from(s.name.clone()),
                Cell::from(s.kind.clone()),
                Cell::from(s.status.clone()).style(Style::default().fg(status_color)),
                Cell::from(s.last_sync.clone().unwrap_or_default()),
            ])
            .style(style)
        })
        .collect();

    let table = Table::new(
        rows,
        [
            Constraint::Percentage(30),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(30),
        ],
    )
    .header(header)
    .block(block);

    frame.render_widget(table, area);
}

// ── Work Queue panel ─────────────────────────────────────────────────────────

fn render_work_queue(frame: &mut Frame, app: &App, area: Rect) {
    let focused = app.active_panel == Panel::WorkQueue;
    let block = panel_block("Work Queue", focused);

    let items: Vec<ListItem> = app
        .work_queue
        .iter()
        .enumerate()
        .map(|(i, task)| {
            let style = if focused && i == app.cursor {
                Style::default().fg(Color::Black).bg(Color::Cyan)
            } else {
                Style::default()
            };
            let status_color = match task.status.as_str() {
                "active" | "running" => Color::Green,
                "failed"             => Color::Red,
                "pending"            => Color::Yellow,
                _                    => Color::White,
            };
            ListItem::new(Line::from(vec![
                Span::styled(
                    format!("[{}] ", task.status),
                    Style::default().fg(status_color),
                ),
                Span::raw(task.description.clone()),
            ]))
            .style(style)
        })
        .collect();

    let mut state = ListState::default();
    if focused && !app.work_queue.is_empty() {
        state.select(Some(app.cursor.min(app.work_queue.len().saturating_sub(1))));
    }

    let list = List::new(items).block(block);
    frame.render_stateful_widget(list, area, &mut state);
}

// ── Settlement panel ─────────────────────────────────────────────────────────

fn render_settlement(frame: &mut Frame, app: &App, area: Rect) {
    let focused = app.active_panel == Panel::Settlement;
    let block = panel_block("Settlement", focused);

    let header = Row::new(["ID", "Amount", "Status", "Settled At"].map(|h| {
        Cell::from(h).style(Style::default().add_modifier(Modifier::BOLD))
    }))
    .bottom_margin(1);

    let rows: Vec<Row> = app
        .settlements
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let style = if focused && i == app.cursor {
                Style::default().fg(Color::Black).bg(Color::Cyan)
            } else {
                Default::default()
            };
            let status_color = match s.status.as_str() {
                "confirmed" | "ok" => Color::Green,
                "failed"           => Color::Red,
                _                  => Color::Yellow,
            };
            Row::new([
                Cell::from(s.id.clone()),
                Cell::from(s.amount.clone()),
                Cell::from(s.status.clone()).style(Style::default().fg(status_color)),
                Cell::from(s.settled_at.clone()),
            ])
            .style(style)
        })
        .collect();

    let table = Table::new(
        rows,
        [
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(40),
        ],
    )
    .header(header)
    .block(block);

    frame.render_widget(table, area);
}

// ── Log panel ────────────────────────────────────────────────────────────────

fn render_logs(frame: &mut Frame, app: &App, area: Rect) {
    let focused = app.active_panel == Panel::Logs;
    let block = panel_block("Logs", focused);

    // Show the last N lines that fit in the panel (approximate).
    let inner_height = area.height.saturating_sub(2) as usize; // subtract borders
    let start = app.log_lines.len().saturating_sub(inner_height);

    let items: Vec<ListItem> = app.log_lines[start..]
        .iter()
        .enumerate()
        .map(|(i, line)| {
            let abs_i = start + i;
            let style = if focused && abs_i == app.cursor {
                Style::default().fg(Color::Black).bg(Color::Cyan)
            } else {
                Style::default()
            };
            ListItem::new(Span::raw(line.clone())).style(style)
        })
        .collect();

    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

// ── Status bar ───────────────────────────────────────────────────────────────

fn render_status(frame: &mut Frame, app: &App, area: Rect) {
    let hint = if app.status_message.is_empty() {
        "q: quit  tab: next panel  ↑/↓: navigate  r: refresh".to_owned()
    } else {
        app.status_message.clone()
    };

    let para = Paragraph::new(hint).style(
        Style::default()
            .fg(Color::White)
            .bg(Color::Blue),
    );
    frame.render_widget(para, area);
}

// ── Helpers ──────────────────────────────────────────────────────────────────

fn panel_block(title: &str, focused: bool) -> Block<'_> {
    let border_style = if focused {
        Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::DarkGray)
    };
    Block::default()
        .title(title)
        .borders(Borders::ALL)
        .border_style(border_style)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::App;
    use ratatui::{backend::TestBackend, Terminal};

    fn make_terminal(w: u16, h: u16) -> Terminal<TestBackend> {
        Terminal::new(TestBackend::new(w, h)).unwrap()
    }

    #[test]
    fn render_empty_app_does_not_panic() {
        let mut terminal = make_terminal(80, 24);
        let app = App::new();
        terminal
            .draw(|frame| render(frame, &app))
            .expect("render should not panic");
    }

    #[test]
    fn render_with_data_does_not_panic() {
        let mut terminal = make_terminal(120, 40);
        let mut app = App::new();
        app.sources.push(crate::app::SourceEntry {
            name: "github-main".into(),
            kind: "github".into(),
            status: "ok".into(),
            last_sync: Some("2026-11-24T10:00:00".into()),
        });
        app.work_queue.push(crate::app::WorkTask {
            id: "wt-001".into(),
            description: "improve docs".into(),
            status: "pending".into(),
            started_at: None,
        });
        terminal
            .draw(|frame| render(frame, &app))
            .expect("render should not panic");
    }
}
