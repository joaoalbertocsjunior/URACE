"""
URACE Spec Structural Audit (§81)

Deterministic, executor-agnostic structural analysis of URACE.md.
Produces Evidence for autonomous discovery and spec self-evolution decisions.

Public API:
    audit(spec_path)       -> full report dict
    build_summary(report)  -> compact summary for injection into discovery context
    extract_spec_version(raw) -> version string
"""

from __future__ import annotations

import re
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# ── RFC 2119 verb inventory ────────────────────────────────────────────────────
RFC2119_VERBS = [
    "MUST NOT", "SHALL NOT", "SHOULD NOT", "NEED NOT",
    "MUST", "SHALL", "SHOULD", "MAY", "RECOMMENDED", "OPTIONAL",
]

_RFC2119_PATTERNS = {v: re.compile(r"\b" + re.escape(v) + r"\b") for v in RFC2119_VERBS}

# ── Canonical stem families (§81) ─────────────────────────────────────────────
# Each key is the minimum prefix that uniquely identifies the concept family
# across all morphological variants in this specification.
STEM_FAMILIES: list[str] = [
    # User-identified irreducible stems
    "justif",      # justification, justify, justified, justifiable
    "evidenc",     # evidence, evidential, evidenced
    "identif",     # identify, identification, identifier, identified
    "reproduc",    # reproduce, reproducible, reproduction
    "veloc",       # velocity
    "condit",      # condition, conditional, conditions
    "confl",       # conflict, conflate, conflation
    # URACE domain stems
    "authorit",    # authority, authoritative, authorization
    "delegat",     # delegate, delegation, delegated
    "valida",      # validate, validation, validated
    "observ",      # observe, observation, observable
    "execut",      # executor, execution, execute
    "checkpoin",   # checkpoint, checkpointed, checkpointing
    "recov",       # recover, recovery, recoverable
    "priorit",     # priority, prioritize, prioritized
    "determin",    # determine, determination, deterministic
    "classif",     # classify, classification, classified
    "reconcil",    # reconcile, reconciliation, reconciled
    "dormant",     # dormant, dormancy
    "backoff",     # backoff
    "dispatch",    # dispatch, dispatched, dispatcher
    "assessm",     # assessment, assessments
    "discover",    # discover, discovery, discovered
    "attribut",    # attribute, attribution, attributed
    "invariant",   # invariant, invariants
]

_STEM_PATTERNS = {
    stem: re.compile(r"\b" + re.escape(stem) + r"\w*", re.IGNORECASE)
    for stem in STEM_FAMILIES
}

# ── Semantic gap patterns ──────────────────────────────────────────────────────
# (pattern, gap_type, gap_reason, interpretations)
_SEMANTIC_GAP_PATTERNS: list[tuple[re.Pattern, str, str, list[str]]] = [
    (
        re.compile(r"\b(appropriate|appropriately)\b", re.IGNORECASE),
        "vague_quantifier",
        "No criteria given for what constitutes 'appropriate'; measurability absent.",
        ["Adequate for the context (undefined)", "Meeting an implicit standard (undefined)"],
    ),
    (
        re.compile(r"\b(reasonable|reasonably)\b", re.IGNORECASE),
        "vague_quantifier",
        "'Reasonable' is unmeasurable without a reference standard.",
        ["Within normal bounds (undefined)", "Not excessive (undefined)"],
    ),
    (
        re.compile(r"\b(sufficient|sufficiently)\b", re.IGNORECASE),
        "vague_quantifier",
        "Threshold for 'sufficient' not defined; depends on evaluator judgment.",
        ["Exceeds a minimum threshold (undefined)", "Satisfies an implicit bar (undefined)"],
    ),
    (
        re.compile(r"\b(adequate|adequately)\b", re.IGNORECASE),
        "vague_quantifier",
        "No specification of what makes something adequate.",
        ["Meeting minimum requirements (undefined)", "Judged satisfactory by an unspecified actor"],
    ),
    (
        re.compile(r"\b(as needed|as required|where applicable|where relevant|when appropriate|when necessary)\b", re.IGNORECASE),
        "underspecified_condition",
        "Condition trigger left undefined — no observable criteria for rule activation.",
        ["Determined by implementation", "Determined by context (unspecified)", "Discretionary"],
    ),
    (
        re.compile(r"\bwhere possible\b", re.IGNORECASE),
        "underspecified_condition",
        "'Where possible' imposes no obligation — the condition is self-defeating for normative rules.",
        ["Only when implementation allows (no obligation)", "Best-effort (unbound)"],
    ),
    (
        re.compile(r"\b(significantly|substantially|considerably|materially)\b", re.IGNORECASE),
        "comparative_without_reference",
        "Comparative adverb without a reference anchor — magnitude is undefined.",
        ["Large relative change (no baseline)", "Meeting an implicit threshold (undefined)"],
    ),
    (
        re.compile(r"\b(proportionate|proportionally|proportional)\b", re.IGNORECASE),
        "vague_quantifier",
        "'Proportionate' implies a ratio but numerator and denominator are unspecified.",
        ["Scaled to impact (scale function undefined)", "Calibrated by judgment (no formula)"],
    ),
    (
        re.compile(r"\b(?:MUST|SHALL|SHOULD) be (?:configured|handled|provided|managed|maintained|tracked|stored|resolved|verified)\b", re.IGNORECASE),
        "undefined_agent",
        "Passive-voice normative rule — the responsible actor is implicit, not stated.",
        ["URACE itself", "The executor", "The operator/deployer", "An external system"],
    ),
    (
        re.compile(r"\bshould consider\b", re.IGNORECASE),
        "non_prescriptive_normative",
        "'Should consider' is advisory, not prescriptive — no observable outcome is mandated.",
        ["Evaluate but not necessarily act", "Implement if judged worthwhile"],
    ),
    (
        re.compile(r"\bcapable of\b", re.IGNORECASE),
        "underspecified_capability",
        "'Capable of' without a measurable test criterion — testability unclear.",
        ["Demonstrates at least once (minimal)", "Reliably in all cases (maximal)"],
    ),
]

# ── Zero-gap canonical entities ────────────────────────────────────────────────
_ZERO_GAP_ENTITIES: list[tuple[str, str, str]] = [
    ("URACE", r"\bURACE\b", "system_name"),
    ("MUST", r"\bMUST\b", "rfc2119_verb"),
    ("MUST NOT", r"\bMUST NOT\b", "rfc2119_verb"),
    ("SHOULD", r"\bSHOULD\b", "rfc2119_verb"),
    ("MAY", r"\bMAY\b", "rfc2119_verb"),
    ("Executor", r"\bExecutor\b", "urace_primitive"),
    ("Objective", r"\bObjective\b", "urace_primitive"),
    ("Plan", r"\bPlan\b", "urace_primitive"),
    ("Operation", r"\bOperation\b", "urace_primitive"),
    ("Checkpoint", r"\bCheckpoint\b", "urace_primitive"),
    ("Evidence", r"\bEvidence\b", "urace_primitive"),
    ("Authority", r"\bAuthority\b", "urace_primitive"),
    ("Intent", r"\bIntent\b", "urace_primitive"),
    ("Trigger", r"\bTrigger\b", "urace_primitive"),
    ("Product", r"\bProduct\b", "urace_primitive"),
    ("ACTIVE", r"\bACTIVE\b", "lifecycle_state"),
    ("DORMANT", r"\bDORMANT\b", "lifecycle_state"),
    ("BLOCKED", r"\bBLOCKED\b", "lifecycle_state"),
    ("§N cross-reference", r"§\d+", "section_ref"),
]
_ZERO_GAP_COMPILED = [(k, re.compile(p), t) for k, p, t in _ZERO_GAP_ENTITIES]

# ── Utilities ──────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def extract_spec_version(raw: str) -> str:
    m = re.search(r"Specification version:\s*(\S+)", raw)
    if not m:
        return "unknown"
    return m.group(1).rstrip("*")


def _parse_sections(raw_lines: list[str]) -> list[dict]:
    sections = []
    current: dict | None = None
    pat = re.compile(r"^# (\d+)\. (.+)$")
    for i, line in enumerate(raw_lines, start=1):
        m = pat.match(line.rstrip())
        if m:
            if current is not None:
                current["line_end"] = i - 1
                current["raw_text"] = "".join(raw_lines[current["line_start"] - 1 : i - 1])
                sections.append(current)
            current = {"id": int(m.group(1)), "title": m.group(2).strip(), "line_start": i, "line_end": None, "raw_text": ""}
    if current is not None:
        current["line_end"] = len(raw_lines)
        current["raw_text"] = "".join(raw_lines[current["line_start"] - 1 :])
        sections.append(current)
    return sections


def _count_rfc2119(prose: str) -> dict[str, int]:
    return {v: len(pat.findall(prose)) for v, pat in _RFC2119_PATTERNS.items()}


def _count_stems(prose: str) -> dict[str, dict]:
    result = {}
    for stem, pat in _STEM_PATTERNS.items():
        matches = pat.findall(prose)
        result[stem] = {"count": len(matches), "variants": sorted({m.lower() for m in matches})}
    return result


def _find_semantic_gaps(prose: str) -> list[dict]:
    gaps = []
    seen: set[str] = set()
    for pat, gap_type, reason, interpretations in _SEMANTIC_GAP_PATTERNS:
        for m in pat.finditer(prose):
            key = gap_type + ":" + m.group(0).lower()
            if key in seen:
                continue
            seen.add(key)
            start = max(0, m.start() - 40)
            end = min(len(prose), m.end() + 40)
            context = "…" + prose[start:end].replace("\n", " ").strip() + "…"
            gaps.append({"span": m.group(0), "context": context, "gap_type": gap_type,
                         "gap_reason": reason, "possible_interpretations": interpretations})
    return gaps


def _find_zero_gap(prose: str) -> list[dict]:
    found = []
    seen: set[str] = set()
    for key, pat, entity_type in _ZERO_GAP_COMPILED:
        if pat.search(prose) and key not in seen:
            seen.add(key)
            found.append({"canonical_key": key, "exact_span": pat.search(prose).group(0), "entity_type": entity_type})
    return found


def _ambiguity_score(gaps: list[dict], rfc2119: dict[str, int]) -> str:
    normative = sum(rfc2119.get(v, 0) for v in ("MUST", "MUST NOT", "SHALL", "SHALL NOT"))
    if normative == 0:
        return "n/a"
    density = len(gaps) / max(normative, 1)
    if density >= 1.5 or len(gaps) >= 6:
        return "high"
    if density >= 0.5 or len(gaps) >= 3:
        return "medium"
    return "low"


def _analyse_section(sec: dict) -> dict:
    raw = sec["raw_text"]
    prose = _strip_fences(raw)
    rfc2119 = _count_rfc2119(prose)
    stems = _count_stems(prose)
    gaps = _find_semantic_gaps(prose)
    zero_gap = _find_zero_gap(prose)
    normative_total = sum(rfc2119.get(v, 0) for v in ("MUST", "MUST NOT", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT"))
    return {
        "section_id": sec["id"],
        "title": sec["title"],
        "line_start": sec["line_start"],
        "line_end": sec["line_end"],
        "fence_count": len(re.findall(r"```", raw)),
        "rfc2119_verbs": rfc2119,
        "normative_rule_count": normative_total,
        "stem_hits": {s: v["count"] for s, v in stems.items() if v["count"] > 0},
        "zero_gap_concepts": zero_gap,
        "semantic_gaps": gaps,
        "section_ambiguity_score": _ambiguity_score(gaps, rfc2119),
    }


def _aggregate_stems(sections_raw: list[dict], prose_all: str) -> dict:
    result = {}
    for stem, pat in _STEM_PATTERNS.items():
        matches = pat.findall(prose_all)
        per_section = {}
        for sec in sections_raw:
            sec_matches = pat.findall(_strip_fences(sec["raw_text"]))
            if sec_matches:
                per_section[f"§{sec['id']}"] = len(sec_matches)
        result[stem] = {
            "stem": stem,
            "global_count": len(matches),
            "variants_found": sorted({m.lower() for m in matches}),
            "per_section": per_section,
            "top_sections": sorted(per_section.items(), key=lambda x: -x[1])[:5],
        }
    return result


def _global_summary(analysed: list[dict]) -> dict:
    totals: dict[str, int] = defaultdict(int)
    for sec in analysed:
        for verb, count in sec["rfc2119_verbs"].items():
            totals[verb] += count
    by_ambiguity: dict[str, list] = {}
    gap_density = []
    for sec in analysed:
        score = sec["section_ambiguity_score"]
        by_ambiguity.setdefault(score, []).append(f"§{sec['section_id']} {sec['title']}")
        gap_density.append({"section": f"§{sec['section_id']}", "title": sec["title"],
                            "gap_count": len(sec["semantic_gaps"]), "normative_rule_count": sec["normative_rule_count"]})
    total_fences = sum(s["fence_count"] for s in analysed)
    return {
        "total_sections": len(analysed),
        "total_fences": total_fences,
        "fence_parity_even": (total_fences % 2 == 0),
        "rfc2119_totals": dict(totals),
        "normative_density_per_section": round(
            sum(s["normative_rule_count"] for s in analysed) / max(len(analysed), 1), 2
        ),
        "sections_by_ambiguity_score": by_ambiguity,
        "top_gap_density_sections": sorted(gap_density, key=lambda x: -x["gap_count"])[:10],
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def audit(spec_path: Path) -> dict:
    """Run the full structural audit; return the report dict (no file I/O)."""
    raw = spec_path.read_text(encoding="utf-8")
    raw_lines = raw.splitlines(keepends=True)
    prose_all = _strip_fences(raw)
    sections_raw = _parse_sections(raw_lines)
    analysed = [_analyse_section(s) for s in sections_raw]
    summary = _global_summary(analysed)
    return {
        "metadata": {
            "source_file": str(spec_path),
            "spec_version": extract_spec_version(raw),
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "total_lines": len(raw_lines),
            "section_count": len(analysed),
        },
        "stem_families": _aggregate_stems(sections_raw, prose_all),
        "per_section": analysed,
        "global_summary": summary,
    }


def build_summary(report: dict) -> dict:
    """Compact summary suitable for injection into the discovery Executor prompt."""
    gs = report["global_summary"]
    ambig = gs["sections_by_ambiguity_score"]
    return {
        "spec_version": report["metadata"]["spec_version"],
        "section_count": report["metadata"]["section_count"],
        "fence_parity_even": gs["fence_parity_even"],
        "rfc2119_totals": gs["rfc2119_totals"],
        "high_ambiguity_sections": ambig.get("high", []),
        "medium_ambiguity_sections": ambig.get("medium", []),
        "top_gap_sections": gs["top_gap_density_sections"][:5],
        "normative_density_per_section": gs["normative_density_per_section"],
    }


# ── Optional dev CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    spec = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[3] / "URACE.md"
    out  = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parents[3] / "urace" / "generated" / "reports" / "spec_audit.json"
    if not spec.exists():
        print(f"ERROR: spec not found at {spec}", file=sys.stderr); sys.exit(1)
    report = audit(spec)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = build_summary(report)
    print(f"Audit complete → {out}")
    print(f"  Spec version       : {report['metadata']['spec_version']}")
    print(f"  Sections           : {report['metadata']['section_count']}")
    print(f"  Fence parity (even): {report['global_summary']['fence_parity_even']}")
    totals = report["global_summary"]["rfc2119_totals"]
    for verb in ("MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY"):
        print(f"  {verb:20s}: {totals.get(verb, 0)}")
    for score in ("high", "medium"):
        secs = summary.get(f"{score}_ambiguity_sections", [])
        if secs:
            print(f"  {score.capitalize()}-ambiguity §§  : {secs}")
