
---

## Phases 1–10 (2026-11-21)

Delivered as 13 sequential commits on main; tag `phases/1-10-complete`.

| Phase | File(s) | What it does |
|-------|---------|--------------|
| 1A | `logging_config.py`, `config_schema.py` | Rotating file handler, event-bus wiring, per-component log config |
| 1B | `mime_policy.py` | Three-tier MIME system; NEVER_ALLOWED set; removes text/* catch-all |
| 1C | `source_adapters/` | SourceAdapter Protocol, SOURCE_REGISTRY, NullSourceAdapter + 8 adapter stubs |
| 2A/2B/2D | `credit_ledger.py` | Non-tamperable complexity score from signed descriptor; REPRICE_OBSERVED anchor |
| 2C | `feature_catalog.py` | scan_similar (non-blocking); outcome_fingerprint hard-block at qualify() |
| 3A-3E | `source_adapters/` | 8 new adapters: folder, shell, environment, codebase, testsuite, webhook, database, p2p_catalog |
| 4A-4D | `executor_capabilities.py` | SKILL_VOCABULARY, probe(), suggest_skills_for_goal(), register_skill_artifact() |
| 5A-5E | `product_profile.py`, `feature_matcher.py`, `feature_catalog.py` | Product profile, feature matching, repricing hookup, trial-first borrow |
| 6A-6E | `web/routes/logs.py`, `skills.py`, `sources.py` | /api/logs, /api/skills, /api/sources endpoints |
| 7A-7F | `config_access.py`, `audit_kinds.py`, `_common.py`, `source_adapters/_base.py` | Typed config accessors, audit kind constants, state migration, protocol verifier |
| 8A-8H | `cli_emit.py` | traces dual-write; trace_records backward compat |
| 9A-9D | `version.py`, `cli/__init__.py` | Protocol version constants; 3 new doctor checks |
| 10A-10C | `tests/test_phase_modules.py` | 30 new tests; test_logging_config _CONFIGURED isolation fix |
