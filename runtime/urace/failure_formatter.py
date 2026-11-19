"""Bounded unittest/pytest failure output formatter.

Extracted from executor.py to separate the parsing/compression logic
from the execution layer. Single responsibility: given raw test output,
return a bounded diagnostic string safe for embedding in audit records.
"""
from __future__ import annotations

import re

_DEFAULT_LIMIT = 6000


def format_failure_output(output: str, limit: int = _DEFAULT_LIMIT) -> str:
    """Return a bounded diagnostic string from raw test output.

    Extracts FAIL/ERROR headings, test summary, and verdict.
    When output exceeds limit, compresses intelligently:
    1. Truncates traces while preserving all failure headers.
    2. If still over limit, omits middle failures with count.
    3. Distributes allowance evenly across failures.
    """
    lines = output.splitlines()
    headings = [i for i, line in enumerate(lines)
                if re.fullmatch(r"(?:FAIL|ERROR): \S+ \([^\n]+\)", line)]
    if not headings:
        return output[-2000:]
    summary_index = next((i for i in range(headings[0] + 1, len(lines))
                          if re.fullmatch(r"Ran \d+ tests? in .+", lines[i])), None)
    summary = []
    end = len(lines) if summary_index is None else summary_index
    if summary_index is not None:
        summary.append(lines[summary_index])
        verdict = next((line for line in lines[summary_index + 1:]
                        if re.fullmatch(r"(?:FAILED|OK)(?:\s+\(.+\))?", line)), None)
        if verdict:
            summary.append(verdict)
    headings = [i for i in headings if i < end]
    blocks = []
    for position, start in enumerate(headings):
        stop = headings[position + 1] if position + 1 < len(headings) else end
        while stop > start and re.fullmatch(r"[=-]{20,}", lines[stop - 1]):
            stop -= 1
        blocks.append(lines[start:stop])
    separator = "\n" + "=" * 70 + "\n"
    parts = ["\n".join(block) for block in blocks]
    if summary:
        parts.append("\n".join(summary))
    detail = separator.join(parts)
    if len(detail) <= limit:
        return detail
    marker = "[trace context truncated]"
    labels = [block[0] for block in blocks]
    summary_text = "\n".join(summary)
    fixed = [label + "\n" + marker for label in labels]
    fixed_size = len(separator.join(fixed + ([summary_text] if summary else [])))
    if fixed_size > limit:
        # A bounded message cannot contain arbitrarily many complete names.
        # Report omissions explicitly rather than silently losing middle failures.
        summary_text = summary_text[-500:]
        kept, size = [], 0
        for label in labels:
            if size + len(label) + 1 > limit - len(summary_text) - 128:
                break
            kept.append(label)
            size += len(label) + 1
        return "\n".join(kept + [f"[{len(labels) - len(kept)} failure headers omitted; diagnostic limit]", summary_text])[:limit]
    allowance = max(0, limit - fixed_size - 2 * len(blocks)) // len(blocks)
    compact = []
    for label, block in zip(labels, blocks, strict=False):
        trace = "\n".join(block[1:])
        if len(trace) > allowance:
            prefix = allowance * 2 // 3
            trace = trace[:prefix] + "\n" + marker + "\n" + trace[-(allowance - prefix):] if allowance else marker
        compact.append(label + ("\n" + trace if trace else ""))
    return separator.join(compact + ([summary_text] if summary else []))[:limit]
