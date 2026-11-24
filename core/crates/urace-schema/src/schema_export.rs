//! Schema exporter — serializes type schemas to JSON for external tooling.
//!
//! Rust port of `schema_export.py`. Provides structured access to all
//! registered schemas and feature bundle metadata.

use serde::{Deserialize, Serialize};
use serde_json::Value;

// ── Schema record types ───────────────────────────────────────────────────────

/// A single exported output schema record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputSchema {
    pub command: String,
    pub schema_version: String,
    pub stable_since: String,
    pub fields: Vec<FieldSpec>,
}

/// A field within an output schema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldSpec {
    pub name: String,
    #[serde(rename = "type")]
    pub type_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub required: bool,
}

/// A registered feature bundle record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureBundle {
    pub name: String,
    pub construct_ids: Vec<String>,
    pub description: String,
    pub spec_version: String,
    pub source: String,
}

/// The full export payload (matches the Python `export_all()` structure).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaExport {
    pub schema_version: String,
    pub output_schemas: Vec<OutputSchema>,
    pub feature_bundles: Vec<FeatureBundle>,
}

// ── SchemaExporter ────────────────────────────────────────────────────────────

/// Collects and serializes schema registrations for external tooling.
///
/// Callers register schemas via `register_output_schema` and
/// `register_feature_bundle`, then call `export()` or `export_json()`.
#[derive(Debug, Default, Clone)]
pub struct SchemaExporter {
    output_schemas: Vec<OutputSchema>,
    feature_bundles: Vec<FeatureBundle>,
}

impl SchemaExporter {
    pub fn new() -> Self {
        Self::default()
    }

    /// Register an output schema (e.g. from a CLI command).
    pub fn register_output_schema(&mut self, schema: OutputSchema) {
        // Replace existing entry with the same command name.
        if let Some(pos) = self.output_schemas.iter().position(|s| s.command == schema.command) {
            self.output_schemas[pos] = schema;
        } else {
            self.output_schemas.push(schema);
        }
    }

    /// Register a feature bundle.
    pub fn register_feature_bundle(&mut self, bundle: FeatureBundle) {
        if let Some(pos) = self.feature_bundles.iter().position(|b| b.name == bundle.name) {
            self.feature_bundles[pos] = bundle;
        } else {
            self.feature_bundles.push(bundle);
        }
    }

    /// Export all schemas as a structured `SchemaExport`.
    pub fn export(&self) -> SchemaExport {
        let mut schemas = self.output_schemas.clone();
        schemas.sort_by(|a, b| a.command.cmp(&b.command));
        let mut bundles = self.feature_bundles.clone();
        bundles.sort_by(|a, b| a.name.cmp(&b.name));
        SchemaExport {
            schema_version: "1.0".into(),
            output_schemas: schemas,
            feature_bundles: bundles,
        }
    }

    /// Export all schemas as a JSON `Value`.
    pub fn export_json(&self) -> Value {
        serde_json::to_value(self.export()).unwrap_or(Value::Null)
    }

    /// Export only output schemas.
    pub fn export_output_schemas(&self) -> Value {
        let mut schemas = self.output_schemas.clone();
        schemas.sort_by(|a, b| a.command.cmp(&b.command));
        serde_json::json!({
            "schema_version": "1.0",
            "schemas": schemas,
            "total": schemas.len(),
        })
    }

    /// Export only feature bundles.
    pub fn export_feature_bundles(&self) -> Value {
        let mut bundles = self.feature_bundles.clone();
        bundles.sort_by(|a, b| a.name.cmp(&b.name));
        serde_json::json!({
            "schema_version": "1.0",
            "bundles": bundles,
            "total": bundles.len(),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_schema(command: &str) -> OutputSchema {
        OutputSchema {
            command: command.into(),
            schema_version: "1".into(),
            stable_since: "0.1.0".into(),
            fields: vec![FieldSpec {
                name: "status".into(),
                type_name: "string".into(),
                description: Some("current status".into()),
                required: true,
            }],
        }
    }

    #[test]
    fn register_and_export() {
        let mut exporter = SchemaExporter::new();
        exporter.register_output_schema(sample_schema("status"));
        exporter.register_output_schema(sample_schema("check"));

        let export = exporter.export();
        assert_eq!(export.schema_version, "1.0");
        assert_eq!(export.output_schemas.len(), 2);
        // sorted by command name
        assert_eq!(export.output_schemas[0].command, "check");
    }

    #[test]
    fn export_json_is_object() {
        let mut exporter = SchemaExporter::new();
        exporter.register_output_schema(sample_schema("status"));
        let json = exporter.export_json();
        assert!(json.is_object());
        assert_eq!(json["schema_version"], "1.0");
    }

    #[test]
    fn deduplicates_on_re_register() {
        let mut exporter = SchemaExporter::new();
        exporter.register_output_schema(sample_schema("status"));
        exporter.register_output_schema(sample_schema("status")); // duplicate
        assert_eq!(exporter.export().output_schemas.len(), 1);
    }

    #[test]
    fn feature_bundle_round_trip() {
        let mut exporter = SchemaExporter::new();
        exporter.register_feature_bundle(FeatureBundle {
            name: "bundle-a".into(),
            construct_ids: vec!["c1".into()],
            description: "test bundle".into(),
            spec_version: "1.0".into(),
            source: "test".into(),
        });
        let export = exporter.export();
        assert_eq!(export.feature_bundles.len(), 1);
        assert_eq!(export.feature_bundles[0].name, "bundle-a");
    }
}
