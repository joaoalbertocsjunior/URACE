//! Exports URACE qualified capabilities as SKILL.md format for Agent Skills compatibility.
//!
//! Invariants:
//! - Only capabilities with `score > 0` are exported (mint-eligible by definition).
//! - No I/O is performed here — callers are responsible for reading/writing files.

use serde_json::Value;

/// A single exportable skill derived from a qualification record.
pub struct SkillExport {
    pub name: String,
    pub description: String,
    pub qualification_threshold: f64,
    pub evaluators: Vec<String>,
    pub invocation: String,
    /// Rendered SKILL.md content for this skill.
    pub skill_md: String,
}

impl SkillExport {
    /// Generate SKILL.md content for a qualified capability.
    pub fn to_skill_md(&self) -> String {
        format!(
            "# SKILL.md\n\n## Name\n{}\n\n## Description\n{}\n\n## Qualification\n- Requires qualification score >= {}\n- Evaluated by: {}\n\n## Invocation\n{}\n\n## Authority\nAll write operations require §62z `AutonomouslyAuthorized` outcome.\n",
            self.name,
            self.description,
            self.qualification_threshold,
            if self.evaluators.is_empty() {
                "(none recorded)".to_string()
            } else {
                self.evaluators.join(", ")
            },
            self.invocation,
        )
    }
}

/// Export all qualified capabilities from a slice of qualification record JSON values.
///
/// Only records with `score > 0` are included (mint-eligible capabilities only).
pub fn export_skills(qualification_records: &[Value]) -> Vec<SkillExport> {
    qualification_records
        .iter()
        .filter_map(|record| {
            let name = record.get("capability")?.as_str()?.to_string();
            let score = record.get("score")?.as_f64()?;
            if score <= 0.0 {
                return None; // only export positive-scored capabilities
            }
            let description = record
                .get("description")
                .and_then(|d| d.as_str())
                .unwrap_or("URACE qualified capability")
                .to_string();
            let evaluators: Vec<String> = record
                .get("evaluators")
                .and_then(|e| e.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect()
                })
                .unwrap_or_default();
            let invocation = format!(
                "Call via URACE MCP server tool `{}` at 127.0.0.1:7701",
                name
            );
            let mut export = SkillExport {
                name,
                description,
                qualification_threshold: score,
                evaluators,
                invocation,
                skill_md: String::new(),
            };
            export.skill_md = export.to_skill_md();
            Some(export)
        })
        .collect()
}

/// Render a combined SKILL.md document from multiple skill exports.
///
/// The document lists all qualified skills with their invocation paths.
pub fn render_combined_skill_md(skills: &[SkillExport]) -> String {
    if skills.is_empty() {
        return "# SKILL.md\n\nNo qualified capabilities found.\n\n## Authority\nAll write operations require §62z `AutonomouslyAuthorized` outcome.\n".to_string();
    }

    let mut out = String::from("# SKILL.md\n\n");
    out.push_str("## URACE Qualified Capabilities\n\n");
    out.push_str(&format!(
        "Generated from {} qualification record(s).\n\n",
        skills.len()
    ));

    for skill in skills {
        out.push_str(&format!("### {}\n\n", skill.name));
        out.push_str(&format!("**Description:** {}\n\n", skill.description));
        out.push_str(&format!(
            "**Qualification threshold:** {}\n\n",
            skill.qualification_threshold
        ));
        if !skill.evaluators.is_empty() {
            out.push_str(&format!(
                "**Evaluators:** {}\n\n",
                skill.evaluators.join(", ")
            ));
        }
        out.push_str(&format!("**Invocation:** {}\n\n", skill.invocation));
        out.push_str("---\n\n");
    }

    out.push_str("## Authority\n\nAll write operations require §62z `AutonomouslyAuthorized` outcome.\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn export_skills_filters_zero_score() {
        let records = vec![
            json!({"capability": "planning", "score": 1.0, "description": "Planning skill"}),
            json!({"capability": "review", "score": 0.0}),
            json!({"capability": "coding", "score": -1.0}),
        ];
        let exports = export_skills(&records);
        assert_eq!(exports.len(), 1);
        assert_eq!(exports[0].name, "planning");
    }

    #[test]
    fn export_skills_captures_evaluators() {
        let records = vec![json!({
            "capability": "testing",
            "score": 0.8,
            "evaluators": ["peer-a", "peer-b"]
        })];
        let exports = export_skills(&records);
        assert_eq!(exports[0].evaluators, vec!["peer-a", "peer-b"]);
    }

    #[test]
    fn to_skill_md_contains_name() {
        let export = SkillExport {
            name: "my_skill".into(),
            description: "A test skill".into(),
            qualification_threshold: 0.75,
            evaluators: vec!["p1".into()],
            invocation: "Call via URACE MCP server".into(),
            skill_md: String::new(),
        };
        let md = export.to_skill_md();
        assert!(md.contains("my_skill"));
        assert!(md.contains("0.75"));
        assert!(md.contains("§62z"));
    }

    #[test]
    fn render_combined_skill_md_empty() {
        let md = render_combined_skill_md(&[]);
        assert!(md.contains("No qualified capabilities found"));
        assert!(md.contains("§62z"));
    }

    #[test]
    fn render_combined_skill_md_with_skills() {
        let records = vec![json!({
            "capability": "audit",
            "score": 1.5,
            "description": "Audit capability",
            "evaluators": ["p1"]
        })];
        let skills = export_skills(&records);
        let md = render_combined_skill_md(&skills);
        assert!(md.contains("audit"));
        assert!(md.contains("1.5"));
    }
}
