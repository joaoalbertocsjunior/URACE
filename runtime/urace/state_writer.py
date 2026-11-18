"""Protocol and default implementation for state dict mutations.

The raw state dict is a 100+-key JSON blob.  Modules that mutate it
(cli_state.py, auto_goals.py, cli_cycle.py) accept a StateWriter instead
of the dict directly, making each mutation path testable in isolation
without constructing a full 100-key state.

Usage::

    from .state_writer import StateWriter, DictStateWriter

    writer: StateWriter = DictStateWriter(state)
    writer.record_executor_failure('executor', 'API error')
    writer.record_blocker('executor', 'unreachable', 'TRANSIENT')

To test a single mutation::

    state = {}
    w = DictStateWriter(state)
    w.record_blocker('scope', 'reason', 'PERSISTENT')
    assert state['blockers'][0]['scope'] == 'scope'
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StateWriter(Protocol):
    """Minimal interface for writing structured events into state."""

    def record_executor_failure(
        self,
        stage: str,
        error: str,
        systematic_threshold: int = 3,
    ) -> None:
        """Record an executor failure; set cooldown when threshold is crossed."""
        ...

    def record_blocker(
        self,
        scope: str,
        reason: str,
        classification: str = 'PERSISTENT',
        evidence_id: str | None = None,
        auto_clear_on: str | None = None,
    ) -> None:
        """Create or deduplicate a blocker entry."""
        ...

    def record_assessment_gap(
        self,
        cycle_id: str,
        dimension: str,
        reason: str,
        minimum_met: str,
        blocking: bool,
    ) -> dict:
        """Create or update an AssessmentGap record."""
        ...

    def resolve_assessment_gap(self, cycle_id: str, dimension: str) -> bool:
        """Mark a matching active AssessmentGap as resolved."""
        ...

    def append_evidence(self, evidence: dict) -> None:
        """Append one evidence record to state['evidence']."""
        ...


class DictStateWriter:
    """Wraps the live state dict and delegates to cli_state functions.

    Pass this wherever StateWriter is expected; each method call modifies
    the same dict that cli_cycle.py would mutate directly.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def record_executor_failure(
        self,
        stage: str,
        error: str,
        systematic_threshold: int = 3,
    ) -> None:
        from . import cli_state as _cs
        _cs.record_executor_failure(self._state, stage, error, systematic_threshold)

    def record_blocker(
        self,
        scope: str,
        reason: str,
        classification: str = 'PERSISTENT',
        evidence_id: str | None = None,
        auto_clear_on: str | None = None,
    ) -> None:
        from . import cli_state as _cs
        _cs.record_blocker(
            self._state, scope, reason, classification, evidence_id, auto_clear_on,
        )

    def record_assessment_gap(
        self,
        cycle_id: str,
        dimension: str,
        reason: str,
        minimum_met: str,
        blocking: bool,
    ) -> dict:
        from . import cli_state as _cs
        return _cs.record_assessment_gap(
            self._state, cycle_id, dimension, reason, minimum_met, blocking,
        )

    def resolve_assessment_gap(self, cycle_id: str, dimension: str) -> bool:
        from . import cli_state as _cs
        return _cs.resolve_assessment_gap(self._state, cycle_id, dimension)

    def append_evidence(self, evidence: dict) -> None:
        self._state.setdefault('evidence', []).append(evidence)
