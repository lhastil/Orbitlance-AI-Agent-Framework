"""Severity levels for validation issues.

Ordering matters: `blocking()` decides whether a project may activate.
Only ERROR and CRITICAL block. WARNING and INFO are reported but do not
prevent activation — this mirrors the per-extension-point resolution table
in docs/project-configuration.md, where a missing Branding degrades
gracefully but missing Knowledge must fail closed.
"""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    """How serious a validation issue is."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Numeric rank, highest severity first. Used for deterministic sorting."""
        return _RANKS[self]

    def blocks_activation(self) -> bool:
        """True when an issue of this severity must prevent a project going live.

        The Validation Layer never decides activation itself (that is the Runtime
        Engine's job per the spec) — this only classifies the issue so the
        Runtime Engine has an unambiguous signal to act on.
        """
        return self in _BLOCKING


_RANKS: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.ERROR: 1,
    Severity.WARNING: 2,
    Severity.INFO: 3,
}

_BLOCKING: frozenset[Severity] = frozenset({Severity.CRITICAL, Severity.ERROR})
