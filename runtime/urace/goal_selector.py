"""Protocol for objective/goal selection.

auto_goals.select() both reads and mutates state directly, making it hard
to test without full state construction.  GoalSelector separates the
computation (which goal to pick) from the application (mutating state).

Usage::

    from .goal_selector import GoalSelector, DefaultGoalSelector

    selector: GoalSelector = DefaultGoalSelector()
    result = selector.select(config, state)
    if result:
        print(f"Selected goal: {result['id']}")

To test selection logic without state side-effects, pass a mock::

    class FixedGoalSelector:
        def select(self, config, state):
            return {'id': 'test-goal', 'title': 'Fixed test goal', ...}

    selector = FixedGoalSelector()
    assert isinstance(selector, GoalSelector)   # True at runtime
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GoalSelector(Protocol):
    """Interface for selecting the next objective to pursue."""

    def select(
        self,
        config: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return the chosen objective dict, or None if nothing is pending.

        Implementations may mutate state to record selection metadata
        (e.g. auto_goal_status, current_objective).  Callers must treat
        a non-None return as the authoritative next goal.
        """
        ...


class DefaultGoalSelector:
    """Delegates to auto_goals.select() — the production implementation."""

    def select(
        self,
        config: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        from . import auto_goals
        return auto_goals.select(config, state)


# Singleton — import directly when no custom selector is needed.
DEFAULT_GOAL_SELECTOR: DefaultGoalSelector = DefaultGoalSelector()
