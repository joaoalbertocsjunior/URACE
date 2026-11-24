//! DatabaseAdapter — SELECT-only SQL queries via sqlx.
//!
//! INVARIANT: any query containing INSERT/UPDATE/DELETE/DROP/ALTER/CREATE
//! (case-insensitive) is rejected before it reaches the database engine.
//! This is a safety guard, not an optimisation — never remove it.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// Forbidden keywords that indicate a write operation.
const WRITE_KEYWORDS: &[&str] = &[
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
];

pub struct DatabaseAdapter;

impl DatabaseAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    /// Write-protection guard: reject any query that contains a forbidden keyword.
    /// Check is performed on the normalised (uppercased, whitespace-collapsed) query.
    pub fn guard_query(query: &str) -> Result<(), SourceError> {
        let upper = query.to_uppercase();
        for kw in WRITE_KEYWORDS {
            // Match whole-word boundaries by checking surrounding chars.
            let mut pos = 0;
            while let Some(idx) = upper[pos..].find(kw) {
                let abs = pos + idx;
                let before_ok = abs == 0
                    || !upper.as_bytes()[abs - 1].is_ascii_alphanumeric();
                let after_ok = abs + kw.len() >= upper.len()
                    || !upper.as_bytes()[abs + kw.len()].is_ascii_alphanumeric();
                if before_ok && after_ok {
                    return Err(SourceError::ActDenied(format!(
                        "write-protection: query contains forbidden keyword '{kw}'"
                    )));
                }
                pos = abs + 1;
            }
        }
        Ok(())
    }

    fn dsn(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("dsn")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Config("config.dsn required".into()))
    }

    fn query(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("query")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Config("config.query required".into()))
    }
}

#[async_trait]
impl SourceAdapter for DatabaseAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["dsn", "query"],
            "properties": {
                "dsn":   {"type": "string", "description": "SQLAlchemy-style DSN: sqlite:///path, postgresql://..."},
                "query": {"type": "string", "description": "SELECT-only query"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec![]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let dsn = Self::dsn(record)?;
        let query = Self::query(record)?;

        // Guard first — even for verify.
        Self::guard_query(&query)?;

        let mut result = HashMap::new();
        // Redact credentials from DSN before including in result.
        let safe_dsn = redact_dsn(&dsn);
        result.insert("ok".into(), Value::Bool(true));
        result.insert("dsn_safe".into(), Value::String(safe_dsn));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let dsn = Self::dsn(record)?;
        let query = Self::query(record)?;

        // Write-protection guard — must pass before any DB connection is opened.
        Self::guard_query(&query)?;

        let now = Self::now();
        let source_id = record.id.clone();

        // Execute query via sqlx.  Only sqlite:// and postgres:// are supported.
        let rows = run_query(&dsn, &query).await?;

        Ok(rows
            .into_iter()
            .map(|mut row| {
                row.insert("source_id".into(), Value::String(source_id.clone()));
                row.insert(
                    "observed_at".into(),
                    Value::Number(
                        serde_json::Number::from_f64(now)
                            .unwrap_or(serde_json::Number::from(0)),
                    ),
                );
                row
            })
            .collect())
    }

    async fn act(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}

/// Execute a SELECT query and return rows as `Vec<HashMap<String, Value>>`.
///
/// Supported DSN schemes: `postgres://` / `postgresql://`.
/// SQLite is intentionally not supported in this crate to avoid a native library
/// conflict with `ldk-node` (which pulls in `rusqlite` → `libsqlite3-sys v0.25`).
async fn run_query(
    dsn: &str,
    query: &str,
) -> Result<Vec<HashMap<String, Value>>, SourceError> {
    if dsn.starts_with("postgres") || dsn.starts_with("postgresql") {
        use sqlx::postgres::PgPool;
        use sqlx::{Column, Row};
        let pool = PgPool::connect(dsn)
            .await
            .map_err(|e| SourceError::Unavailable(format!("postgres connect: {e}")))?;
        let rows = sqlx::query(query)
            .fetch_all(&pool)
            .await
            .map_err(|e| SourceError::Io(format!("query error: {e}")))?;
        let result = rows
            .iter()
            .map(|row| {
                let mut map = HashMap::new();
                for col in row.columns() {
                    let name = col.name().to_owned();
                    let val: Value = {
                        if let Ok(v) = row.try_get::<String, _>(col.ordinal()) {
                            Value::String(v)
                        } else if let Ok(v) = row.try_get::<i64, _>(col.ordinal()) {
                            json!(v)
                        } else if let Ok(v) = row.try_get::<f64, _>(col.ordinal()) {
                            json!(v)
                        } else if let Ok(v) = row.try_get::<bool, _>(col.ordinal()) {
                            json!(v)
                        } else {
                            Value::Null
                        }
                    };
                    map.insert(name, val);
                }
                map
            })
            .collect();
        pool.close().await;
        Ok(result)
    } else {
        Err(SourceError::Config(format!(
            "unsupported DSN scheme (supported: postgresql://): {dsn}"
        )))
    }
}

/// Redact the password component of a DSN for safe display.
fn redact_dsn(dsn: &str) -> String {
    // Simple heuristic: replace :<password>@ with :***@
    if let Some(at) = dsn.rfind('@') {
        if let Some(scheme_end) = dsn.find("://") {
            let authority = &dsn[scheme_end + 3..at];
            if let Some(colon) = authority.find(':') {
                let user = &authority[..colon];
                let scheme = &dsn[..scheme_end + 3];
                let rest = &dsn[at..];
                return format!("{scheme}{user}:***{rest}");
            }
        }
    }
    dsn.to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(dsn: &str, query: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("dsn".into(), Value::String(dsn.into()));
        config.insert("query".into(), Value::String(query.into()));
        SourceRecord::new("db-test", "database", config)
    }

    // --- Write-protection guard tests ---

    #[test]
    fn guard_allows_select() {
        assert!(DatabaseAdapter::guard_query("SELECT * FROM users").is_ok());
        assert!(DatabaseAdapter::guard_query("select id, name from foo where id = 1").is_ok());
    }

    #[test]
    fn guard_rejects_insert() {
        let err = DatabaseAdapter::guard_query("INSERT INTO foo VALUES (1)");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_delete() {
        let err = DatabaseAdapter::guard_query("DELETE FROM bar WHERE id = 1");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_drop() {
        let err = DatabaseAdapter::guard_query("DROP TABLE users");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_update() {
        let err = DatabaseAdapter::guard_query("UPDATE users SET name='x'");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_alter() {
        let err = DatabaseAdapter::guard_query("ALTER TABLE users ADD COLUMN x INT");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_create() {
        let err = DatabaseAdapter::guard_query("CREATE TABLE new_table (id INT)");
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn guard_rejects_case_insensitive() {
        assert!(DatabaseAdapter::guard_query("insert into x values (1)").is_err());
        assert!(DatabaseAdapter::guard_query("Insert Into x values (1)").is_err());
    }

    #[tokio::test]
    async fn sync_rejects_write_query() {
        let record = make_record("sqlite:///test.db", "INSERT INTO foo VALUES (1)");
        let adapter = DatabaseAdapter;
        let err = adapter.sync(&record, &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::ActDenied(_))), "got: {err:?}");
    }

    #[test]
    fn redact_dsn_hides_password() {
        let dsn = "postgresql://user:secret@localhost/db";
        let safe = redact_dsn(dsn);
        assert!(!safe.contains("secret"), "password not redacted: {safe}");
        assert!(safe.contains("user"), "user missing: {safe}");
    }

    #[test]
    fn missing_dsn_returns_config_error() {
        let config = HashMap::new();
        let record = SourceRecord::new("test", "database", config);
        let err = DatabaseAdapter::dsn(&record);
        assert!(matches!(err, Err(SourceError::Config(_))));
    }
}
