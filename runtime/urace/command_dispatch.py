"""Command dataclass and CommandHandler Protocol for the CLI dispatch layer.

cli_cycle.py's cycle() currently receives a raw argparse namespace and
branches on hundreds of fields with direct state mutations.  Introducing
a typed Command and a CommandHandler Protocol:

1. Makes each sub-command independently testable (pass a Command, get a result).
2. Separates parsing (cli_parser.py) from execution (command_dispatch.py).
3. Enables command queuing, replay, and audit without touching cycle().

Usage::

    from .command_dispatch import Command, CommandResult, CommandHandler

    class StatusHandler:
        def handle(self, command: Command) -> CommandResult:
            return CommandResult(success=True, output={'status': 'ok'})

    handler: CommandHandler = StatusHandler()
    result = handler.handle(Command(name='status', args={}, config={}, state={}))

Wire into cli_cycle.py::

    from .command_dispatch import route_command
    result = route_command(command_name, args_dict, config, state)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class Command:
    """Typed representation of one CLI invocation."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    json_mode: bool = False


@dataclass
class CommandResult:
    """Structured result from handling one Command."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    exit_code: int = 0


@runtime_checkable
class CommandHandler(Protocol):
    """Interface for handling a single typed Command."""

    def handle(self, command: Command) -> CommandResult:
        """Execute command and return a structured result.

        Must not raise — catch all exceptions and return CommandResult(success=False).
        """
        ...


def args_to_command(
    name: str,
    args: Any,
    config: dict[str, Any],
    state: dict[str, Any],
    *,
    json_mode: bool = False,
) -> Command:
    """Convert argparse Namespace (or plain dict) to a typed Command."""
    args_dict: dict[str, Any]
    if hasattr(args, '__dict__'):
        args_dict = vars(args)
    elif isinstance(args, dict):
        args_dict = args
    else:
        args_dict = {}
    return Command(
        name=name,
        args=args_dict,
        config=config,
        state=state,
        json_mode=json_mode,
    )
