//! Page route handlers — one per HTML page.
//! Each handler renders its template with `active` and `token` context variables.

use crate::AppState;
use axum::{
    extract::State,
    response::Html,
};
use minijinja::context;

fn render(state: &AppState, template: &str, active: &str) -> Html<String> {
    let tmpl = match state.env.get_template(template) {
        Ok(t) => t,
        Err(e) => return Html(format!("<!-- template error: {e} -->")),
    };
    let html = tmpl
        .render(context! { active => active, token => state.token })
        .unwrap_or_else(|e| format!("<!-- render error: {e} -->"));
    Html(html)
}

pub async fn index(State(s): State<AppState>) -> Html<String> {
    render(&s, "index.html", "index")
}

pub async fn shell(State(s): State<AppState>) -> Html<String> {
    render(&s, "shell.html", "shell")
}

pub async fn config(State(s): State<AppState>) -> Html<String> {
    render(&s, "config.html", "config")
}

pub async fn vitals(State(s): State<AppState>) -> Html<String> {
    render(&s, "vitals.html", "vitals")
}

pub async fn wallet(State(s): State<AppState>) -> Html<String> {
    render(&s, "wallet.html", "wallet")
}

pub async fn cycle(State(s): State<AppState>) -> Html<String> {
    render(&s, "cycle.html", "cycle")
}

pub async fn goals(State(s): State<AppState>) -> Html<String> {
    render(&s, "goals.html", "goals")
}

pub async fn inbox(State(s): State<AppState>) -> Html<String> {
    render(&s, "inbox.html", "inbox")
}

pub async fn audit(State(s): State<AppState>) -> Html<String> {
    render(&s, "audit.html", "audit")
}

pub async fn compliance(State(s): State<AppState>) -> Html<String> {
    render(&s, "compliance.html", "compliance")
}

pub async fn rules(State(s): State<AppState>) -> Html<String> {
    render(&s, "rules.html", "rules")
}

pub async fn github(State(s): State<AppState>) -> Html<String> {
    render(&s, "github.html", "github")
}

pub async fn exchange(State(s): State<AppState>) -> Html<String> {
    render(&s, "exchange.html", "exchange")
}

pub async fn products(State(s): State<AppState>) -> Html<String> {
    render(&s, "products.html", "products")
}

pub async fn fleet(State(s): State<AppState>) -> Html<String> {
    render(&s, "fleet.html", "fleet")
}

pub async fn portfolio(State(s): State<AppState>) -> Html<String> {
    render(&s, "portfolio.html", "portfolio")
}

pub async fn sources(State(s): State<AppState>) -> Html<String> {
    render(&s, "sources.html", "sources")
}
