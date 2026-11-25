pub mod auth;
pub mod routes;
pub mod state_reader;

use anyhow::Result;
use axum::Router;
use std::{net::SocketAddr, path::PathBuf, sync::Arc};
use tower_http::services::ServeDir;
use minijinja::Environment;

#[derive(Clone)]
pub struct AppState {
    pub token: String,
    pub root: PathBuf,
    pub env: Arc<Environment<'static>>,
}

pub async fn serve(root: PathBuf, port: u16, bind: &str, token: String) -> Result<()> {
    let env = Arc::new(build_env());
    let state = AppState { token, root, env };

    let static_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("static");

    let app = Router::new()
        // page routes
        .route("/", axum::routing::get(routes::pages::index))
        .route("/shell", axum::routing::get(routes::pages::shell))
        .route("/config", axum::routing::get(routes::pages::config))
        .route("/vitals", axum::routing::get(routes::pages::vitals))
        .route("/wallet", axum::routing::get(routes::pages::wallet))
        .route("/cycle", axum::routing::get(routes::pages::cycle))
        .route("/goals", axum::routing::get(routes::pages::goals))
        .route("/inbox", axum::routing::get(routes::pages::inbox))
        .route("/audit", axum::routing::get(routes::pages::audit))
        .route("/compliance", axum::routing::get(routes::pages::compliance))
        .route("/rules", axum::routing::get(routes::pages::rules))
        .route("/github", axum::routing::get(routes::pages::github))
        .route("/exchange", axum::routing::get(routes::pages::exchange))
        .route("/products", axum::routing::get(routes::pages::products))
        .route("/fleet", axum::routing::get(routes::pages::fleet))
        .route("/portfolio", axum::routing::get(routes::pages::portfolio))
        .route("/sources", axum::routing::get(routes::pages::sources))
        // api routes
        .nest("/api/vitals", routes::vitals::router())
        .nest("/api/goals", routes::goals::router())
        .nest("/api/sources", routes::sources::router())
        .nest("/api/audit", routes::audit::router())
        .nest("/api/cycle", routes::cycle::router())
        .nest("/api/inbox", routes::inbox::router())
        .nest("/api/daemon", routes::daemon::router())
        .nest("/api/config", routes::config::router())
        .nest("/api/compliance", routes::compliance::router())
        .nest("/api/rules", routes::rules::router())
        .nest("/api/github", routes::github::router())
        .nest("/api/exchange", routes::exchange::router())
        .nest("/api/products", routes::products::router())
        .nest("/api/fleet", routes::fleet::router())
        .nest("/api/portfolio", routes::portfolio::router())
        .nest("/api/logs", routes::logs::router())
        .nest("/api/metrics", routes::metrics::router())
        .nest("/api/skills", routes::skills::router())
        .nest("/api/shell", routes::shell::router())
        // static files
        .nest_service("/static", ServeDir::new(static_dir))
        .with_state(state);

    let addr: SocketAddr = format!("{bind}:{port}").parse()?;
    tracing::info!("urace web UI listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn build_env() -> Environment<'static> {
    let mut env = Environment::new();
    env.add_template("base.html", include_str!("../templates/base.html")).unwrap();
    env.add_template("shell.html", include_str!("../templates/shell.html")).unwrap();
    env.add_template("config.html", include_str!("../templates/config.html")).unwrap();
    env.add_template("vitals.html", include_str!("../templates/vitals.html")).unwrap();
    env.add_template("wallet.html", include_str!("../templates/wallet.html")).unwrap();
    env.add_template("cycle.html", include_str!("../templates/cycle.html")).unwrap();
    env.add_template("cycle_state.html", include_str!("../templates/cycle_state.html")).unwrap();
    env.add_template("daemon_bar.html", include_str!("../templates/daemon_bar.html")).unwrap();
    env.add_template("goals.html", include_str!("../templates/goals.html")).unwrap();
    env.add_template("inbox.html", include_str!("../templates/inbox.html")).unwrap();
    env.add_template("audit.html", include_str!("../templates/audit.html")).unwrap();
    env.add_template("compliance.html", include_str!("../templates/compliance.html")).unwrap();
    env.add_template("rules.html", include_str!("../templates/rules.html")).unwrap();
    env.add_template("github.html", include_str!("../templates/github.html")).unwrap();
    env.add_template("exchange.html", include_str!("../templates/exchange.html")).unwrap();
    env.add_template("products.html", include_str!("../templates/products.html")).unwrap();
    env.add_template("fleet.html", include_str!("../templates/fleet.html")).unwrap();
    env.add_template("portfolio.html", include_str!("../templates/portfolio.html")).unwrap();
    env.add_template("sources.html", include_str!("../templates/sources.html")).unwrap();
    env
}
