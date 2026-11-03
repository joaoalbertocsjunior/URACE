"""pytest session fixture: ensure a minimal config.json exists at CONFIG_PATH before any test runs."""
import json
import sys
from pathlib import Path

from urace._common import CONFIG_PATH, ROOT

try:
    import pytest
    _PYTEST_AVAILABLE = True
except ImportError:
    _PYTEST_AVAILABLE = False

# Pre-import trial modules into sys.modules so they survive any test's temporary
# sys.path patches (e.g. patch.object(sys, 'path', [...])). Without this,
# runtime_trial's top-level `import runtime_evaluation` can fail when sys.path
# has been replaced with a patched list that doesn't include the trial directory.
_TRIAL_DIR = str(Path(__file__).resolve().parents[2] / "trial")
if _TRIAL_DIR not in sys.path:
    sys.path.insert(0, _TRIAL_DIR)
if Path(_TRIAL_DIR).is_dir():
    try:
        import runtime_cycle           # noqa: F401
        import runtime_dashboard       # noqa: F401
        import runtime_evaluation      # noqa: F401
        import runtime_proposal        # noqa: F401
        import runtime_qualification   # noqa: F401
        import runtime_regression_guard  # noqa: F401
        import runtime_snapshot        # noqa: F401
        import runtime_trial           # noqa: F401
    except ImportError:
        pass

_MINIMAL_CONFIG = {
    "analytics_export": {"include_xlsx": False, "mode": "ON_CHECKPOINT", "output": "generated/reports/latest"},
    "authority": {
        "delegated": ["assessment", "objectives", "priority", "plans", "measurement", "validation"],
        "provenance": "CI bootstrap",
        "reserved": ["change retained purpose", "weaken normative invariants", "publish externally", "spend money"],
        "source": "repository owner",
    },
    "auto_goals": {"enabled": False, "replenish_backlog": True},
    "change_explanations": {},
    "constraints": {},
    "default_metrics": [],
    "efficiency": {},
    "evaluation_system": {
        "weights": {
            "productive_call_yield": 1.0,
            "execution_acceptance": 1.5,
            "regression_safety": 2.0,
            "goal_completion": 1.0,
        },
        "minimum_evidence_units": 5,
    },
    "execution_workflow": {},
    "executor": {
        "allowed_files_by_scope": {"runtime": []},
        "availability_probe_interval_seconds": 60,
        "available_probe_interval_seconds": 30,
        "capacity_fallback_seconds": 300,
        "capacity_retry_delay_ms": 500,
        "capacity_retry_mode": "linear",
        "command": None,
        "context_hints": [],
        "disabled_features": [],
        "discovery_interval_seconds": 300,
        "discovery_yield_exhausted_threshold": 3,
        "enabled": False,
        "healthcheck_timeout_seconds": 10,
        "kind": "subprocess",
        "max_discovery_interval_seconds": 3600,
        "max_executor_calls_per_24h": None,
        "max_executor_calls_per_30d": None,
        "max_executor_result_bytes": 1048576,
        "max_prompt_external_observations": 20,
        "max_prompt_reasoning_entries": 50,
        "max_unavailable_probe_interval_seconds": 600,
        "model": None,
        "progress_heartbeat_seconds": 30,
        "providers": [],
        "routing_balance_window_seconds": 86400,
        "routing_efficiency_tolerance_ratio": 0.15,
        "routing_max_elapsed_seconds": 3600,
        "routing_suitability_tolerance": 0.1,
        "sandbox_bwrap_directory": None,
        "timeout_seconds": 300,
        "trigger_dedupe_seconds": 60,
        "triggered_discovery_cooldown_seconds": 60,
        "validation_timeout_seconds": 60,
    },
    "external_metrics": {},
    "github": {},
    "intent": {"purpose": "CI bootstrap product", "retained": ["purpose", "authority boundaries"]},
    "operator_patterns": [],
    "p2p": {},
    "product": "ci-test-product",
    "product_files": ["URACE.md", "README.md"],
    "product_type": "generic",
    "product_types": ["generic"],
    "product_registry": [],
    "project": {},
    "resource_product_id": None,
    "resources": {},
    "runtime_workflow": {},
    "scope_priority": {
        "max_weight_step_per_revision": 0.25,
        "mode": "DYNAMIC_BOUNDED",
        "version": "dynamic-scope-priority-v1",
        "scopes": {
            "product_guidance": {"artifacts": ["README.md"], "base_weight": 1.0, "execution_scopes": ["documentation"], "label": "Product guidance", "max_weight": 3.0, "min_weight": 0.5},
            "authoritative_specification": {"artifacts": ["URACE.md"], "base_weight": 1.0, "execution_scopes": ["documentation"], "label": "Authoritative specification", "max_weight": 3.0, "min_weight": 0.5},
            "runtime_implementation": {"artifacts": ["urace/runtime/urace/cli.py"], "base_weight": 0.9, "execution_scopes": ["runtime", "rebootstrap"], "label": "Runtime correctness", "max_weight": 3.0, "min_weight": 0.5},
            "measurement_system": {"artifacts": ["urace/runtime/urace/config.json"], "base_weight": 0.8, "execution_scopes": ["metrics"], "label": "Metrics and evaluation", "max_weight": 3.0, "min_weight": 0.5},
        },
    },
    "self_evolution_policy": {"mode": "NECESSARY_ONLY", "source": "CI", "provenance": "CI bootstrap"},
    "specification_workflow": {},
    "state_path": str(CONFIG_PATH.parent.parent / "state" / "state.json"),
}


def pytest_configure(config):
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(_MINIMAL_CONFIG, indent=2), encoding="utf-8")


def _ensure_product_files_at_root():
    """Create minimal product file stubs at ROOT when missing.

    In CI the repo is checked out to urace/ so ROOT (parent of SYSTEM_ROOT)
    is the workspace root where URACE.md / README.md don't exist.  Several
    tests expect ROOT/"URACE.md" to be readable (onboarding gate checks).
    """
    _urace = ROOT / "URACE.md"
    _readme = ROOT / "README.md"
    created = []
    if not _urace.exists():
        _real = ROOT / "urace" / "URACE.md"
        if _real.exists():
            _urace.write_text(_real.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            _urace.write_text(
                "# URACE\nPrimary invariant:\n# 79. Bootstrap Execution Requirements\n"
                "# 80. Final Invariant\n" + "MUST remain valid.\n" * 50,
                encoding="utf-8",
            )
        created.append(_urace)
    if not _readme.exists():
        _real = ROOT / "urace" / "README.md"
        if _real.exists():
            _readme.write_text(_real.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            _readme.write_text(
                "# URACE\n## Get Running\n## Use It\n## Stay Safe and Recover\n"
                + "Valid guidance.\n" * 50,
                encoding="utf-8",
            )
        created.append(_readme)
    yield
    for path in created:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


if _PYTEST_AVAILABLE:
    _ensure_product_files_at_root = pytest.fixture(scope="session", autouse=True)(
        _ensure_product_files_at_root
    )


if __name__ == "__main__":
    pytest_configure(None)
