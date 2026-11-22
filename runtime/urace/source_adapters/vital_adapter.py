"""Vital source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class VitalAdapter(NullSourceAdapter):
    kind = 'vital'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--numerator', default=None)
        subparser.add_argument('--denominator', default=None)
        subparser.add_argument('--window', default=None)
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        num = getattr(args, 'numerator', None) or ''
        if not name:
            raise ValueError('source add --kind vital requires a name')
        if not num:
            raise ValueError('source add --kind vital requires --numerator')
        return {'kind': self.kind, 'numerator': num,
                'denominator': getattr(args, 'denominator', None),
                'window': getattr(args, 'window', None)}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        from .._common import now
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'numerator': kwargs.get('numerator', ''),
                'denominator': kwargs.get('denominator'),
                'window': kwargs.get('window'),
                'last_value': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from ._base import _get_source, _set_source
        record = _get_source(state, source_id) or {}
        astate = record.get('adapter_state', {})
        numerator = astate.get('numerator', '')
        denominator = astate.get('denominator')
        # Look up current metric values from progress_profiles
        profiles = state.get('progress_profiles', [])
        measures = profiles[0].get('measures', {}) if profiles else {}
        num_val = measures.get(numerator, {}).get('current') if numerator else None
        den_val = measures.get(denominator, {}).get('current') if denominator else None
        ratio = None
        if num_val is not None and den_val and float(den_val) != 0:
            ratio = round(float(num_val) / float(den_val), 4)
        astate['last_value'] = ratio if ratio is not None else num_val
        _set_source(state, source_id, record)
        return {
            'synced': True,
            'numerator': numerator,
            'numerator_value': num_val,
            'denominator': denominator,
            'denominator_value': den_val,
            'ratio': ratio,
        }


SOURCE_REGISTRY.register(VitalAdapter())
