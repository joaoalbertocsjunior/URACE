"""Feature matcher — scores how well a feature atom fits a product profile.

Layer 1 (strict):  interface_sha384 or acceptance_sha384 exact match → 1.0
Layer 2 (heuristic): keyword overlap between feature capability and product capability,
                     weighted by config feature_matching section.

Returns a MatchResult dict:
  {score: float[0,1], layer: int, reasons: list[str], borrowable: bool}

borrowable = True when score >= borrow_threshold (default 0.5) AND
             feature is in an 'active' lifecycle state.

Config section feature_matching:
  layer1_strict:          bool (default True)  — block non-matching on layer1 signal
  layer2_cap_weight:      int (×100 fraction)  — capability keyword weight (default 60)
  layer2_lang_weight:     int (×100 fraction)  — language overlap weight (default 30)
  layer2_loc_weight:      int (×100 fraction)  — loc-range proximity weight (default 10)
  borrow_threshold:       float (default 0.5)
"""
from __future__ import annotations

import re
from typing import Any


_STOPWORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'is', 'in', 'of', 'to', 'for', 'with',
    'that', 'this', 'it', 'on', 'as', 'by', 'at', 'be', 'are', 'was', 'has',
})

_LANG_EXT_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.java': 'java', '.go': 'go', '.rb': 'ruby', '.rs': 'rust',
    '.c': 'c', '.cpp': 'cpp', '.cs': 'csharp', '.sh': 'shell',
}


def _keywords(text: str) -> frozenset[str]:
    tokens = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*', text.lower())
    return frozenset(t for t in tokens if t not in _STOPWORDS and len(t) > 2)


def _lang_set(profile: dict) -> frozenset[str]:
    langs = []
    for ext in profile.get('codebase_languages', []):
        lang = _LANG_EXT_MAP.get(ext, ext.lstrip('.'))
        langs.append(lang.lower())
    return frozenset(langs)


def _capability_mentions_lang(cap: str, langs: frozenset[str]) -> bool:
    cap_lower = cap.lower()
    return any(lang in cap_lower for lang in langs)


def _layer2_score(profile: dict, descriptor: dict, cfg: dict) -> tuple[float, list[str]]:
    cap_w  = cfg.get('layer2_cap_weight',  60) / 100.0
    lang_w = cfg.get('layer2_lang_weight', 30) / 100.0
    loc_w  = cfg.get('layer2_loc_weight',  10) / 100.0

    reasons: list[str] = []
    score = 0.0

    # Capability keyword overlap
    prod_cap = profile.get('capability', '')
    feat_cap = descriptor.get('capability', '')
    if prod_cap and feat_cap:
        pk = _keywords(prod_cap)
        fk = _keywords(feat_cap)
        if pk and fk:
            overlap = len(pk & fk) / max(len(pk), len(fk))
            score += overlap * cap_w
            if overlap > 0:
                reasons.append(f'capability overlap={overlap:.2f}')

    # Language hint in feature capability
    prod_langs = _lang_set(profile)
    if prod_langs and feat_cap:
        if _capability_mentions_lang(feat_cap, prod_langs):
            score += lang_w
            reasons.append('language hint in feature capability')

    # LOC range proximity (features for very large codebases penalised on small products)
    prod_loc = profile.get('codebase_loc') or 0
    if prod_loc and loc_w:
        # Simple proximity: no penalty when feature has no loc annotation
        metrics = descriptor.get('complexity_metrics', {})
        feat_loc = metrics.get('loc') if isinstance(metrics, dict) else None
        if isinstance(feat_loc, (int, float)) and feat_loc > 0:
            ratio = min(prod_loc, feat_loc) / max(prod_loc, feat_loc)
            score += ratio * loc_w
            reasons.append(f'loc proximity={ratio:.2f}')
        else:
            score += loc_w * 0.5  # neutral if no annotation

    return min(score, 1.0), reasons


def match(profile: dict, feature_atom: dict, config: dict | None = None) -> dict:
    """Score *feature_atom* against *profile*.

    *feature_atom* is the full atom dict from Catalog.state()['atoms'][key].
    *profile* is from product_profile.load(state).
    Returns a MatchResult dict.
    """
    cfg = (config or {}).get('feature_matching', {})
    layer1_strict = cfg.get('layer1_strict', True)
    borrow_threshold = float(cfg.get('borrow_threshold', 0.5))

    descriptor = feature_atom.get('descriptor', {})
    lifecycle = feature_atom.get('lifecycle', 'active')
    reasons: list[str] = []

    # Layer 1 — exact hash signal
    prod_iface = profile.get('interface_sha384', '')
    feat_iface = descriptor.get('interface_sha384', '')
    prod_acc   = profile.get('acceptance_sha384', '')
    feat_acc   = descriptor.get('acceptance_sha384', '')

    layer1_hit = False
    if prod_iface and feat_iface and prod_iface == feat_iface:
        layer1_hit = True
        reasons.append('interface_sha384 exact match')
    elif prod_acc and feat_acc and prod_acc == feat_acc:
        layer1_hit = True
        reasons.append('acceptance_sha384 exact match')

    if layer1_hit:
        return {
            'score': 1.0,
            'layer': 1,
            'reasons': reasons,
            'lifecycle': lifecycle,
            'borrowable': lifecycle == 'active',
        }

    if layer1_strict and (prod_iface or prod_acc):
        # Profile has hash hints but no match — definite mismatch
        return {'score': 0.0, 'layer': 1, 'reasons': ['layer1 strict: no hash match'], 'lifecycle': lifecycle, 'borrowable': False}

    # Layer 2 — heuristic
    score, l2_reasons = _layer2_score(profile, descriptor, cfg)
    reasons.extend(l2_reasons)
    return {
        'score': round(score, 4),
        'layer': 2,
        'reasons': reasons,
        'lifecycle': lifecycle,
        'borrowable': lifecycle == 'active' and score >= borrow_threshold,
    }


def rank(profile: dict, atoms: dict[str, dict], config: dict | None = None, limit: int = 10) -> list[dict]:
    """Rank *atoms* dict by match score; return top *limit* entries."""
    scored = []
    for key, atom in atoms.items():
        result = match(profile, atom, config)
        if result['score'] > 0:
            scored.append({'atom': key, **result})
    scored.sort(key=lambda r: -r['score'])
    return scored[:limit]
