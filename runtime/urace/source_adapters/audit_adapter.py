"""Audit source adapter — observe the URACE audit/state audit records."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, _get_source
from . import SOURCE_REGISTRY
from .._common import now


class AuditAdapter(NullSourceAdapter):
    kind = 'audit'

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind audit requires a name')
        return {'kind': self.kind}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'last_record_count': 0,
                'last_synced_at': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        audit_records = state.get('state_audit_records', [])
        evidence = state.get('evidence', [])
        compliance = state.get('compliance_records', [])
        record = _get_source(state, source_id) or {}
        astate = record.get('adapter_state', {})
        prev_count = astate.get('last_record_count', 0)
        total = len(audit_records) + len(evidence)
        astate['last_record_count'] = total
        astate['last_synced_at'] = now()
        recent_kinds = list({e.get('kind', '') for e in evidence[-20:] if e.get('kind')})
        return {
            'synced': True,
            'audit_record_count': len(audit_records),
            'evidence_count': len(evidence),
            'compliance_record_count': len(compliance),
            'new_since_last': max(0, total - prev_count),
            'recent_evidence_kinds': recent_kinds,
        }


SOURCE_REGISTRY.register(AuditAdapter())
