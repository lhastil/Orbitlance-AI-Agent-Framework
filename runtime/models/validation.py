"""ValidationIssue and ValidationResult.

Implements the `ValidationResult` data model from docs/runtime-specification.md.
The spec lists issue fields as {field, file, severity, message}; this adds
`code`, `section` and `recommendation` so every issue is deterministic and
actionable. That is a superset of the specified model, not a change to it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from runtime.models.severity import Severity


class ValidationTarget(str, Enum):
    """What was validated. Recorded on the result for observability."""

    CORE = "core"
    PROJECT = "project"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single, specific validation finding.

    Every field except `section`/`field_name` is mandatory: the spec forbids
    generic "validation failed" output, so an issue must always say what broke,
    where, and what to do about it.
    """

    code: str
    severity: Severity
    message: str
    file: str
    recommendation: str
    section: str | None = None
    field_name: str | None = None

    def __post_init__(self) -> None:
        for name in ("code", "message", "file", "recommendation"):
            if not str(getattr(self, name) or "").strip():
                raise ValueError(
                    f"ValidationIssue.{name} must be non-empty "
                    f"(code={self.code!r}) — generic issues are not permitted."
                )

    @property
    def location(self) -> str:
        """Human-readable location, e.g. 'config.md > LLM Provider'."""
        parts = [self.file]
        if self.section:
            parts.append(self.section)
        if self.field_name:
            parts.append(self.field_name)
        return " > ".join(parts)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.file,
            "section": self.section,
            "field": self.field_name,
            "recommendation": self.recommendation,
        }

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.code} {self.location}: {self.message}"


def _sort_key(issue: ValidationIssue) -> tuple[int, str, str, str]:
    """Deterministic ordering: severity first, then stable text fields.

    Determinism matters — CI diffs and audit logs must not churn because two
    equally-severe issues swapped places between runs.
    """
    return (issue.severity.rank, issue.code, issue.file, issue.section or "")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of validating Core or a Project.

    A result reporting problems is a *successful* run of the validator — the
    spec is explicit that reporting invalidity is normal output, not failure.
    """

    target: ValidationTarget
    subject_id: str
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    validated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    @classmethod
    def build(
        cls,
        target: ValidationTarget,
        subject_id: str,
        issues: Iterable[ValidationIssue],
    ) -> ValidationResult:
        return cls(
            target=target,
            subject_id=subject_id,
            issues=tuple(sorted(issues, key=_sort_key)),
        )

    @property
    def valid(self) -> bool:
        """Fail closed: valid only when nothing blocking was found."""
        return not any(i.severity.blocks_activation() for i in self.issues)

    @property
    def blocking_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity.blocks_activation())

    def of_severity(self, severity: Severity) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is severity)

    def codes(self) -> tuple[str, ...]:
        return tuple(i.code for i in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target.value,
            "subject_id": self.subject_id,
            "valid": self.valid,
            "validated_at": self.validated_at.isoformat(),
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary(self) -> str:
        if not self.issues:
            return f"{self.subject_id}: valid (no issues)"
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        breakdown = ", ".join(f"{n} {sev}" for sev, n in sorted(counts.items()))
        verdict = "VALID" if self.valid else "INVALID"
        return f"{self.subject_id}: {verdict} ({breakdown})"

    def render(self) -> str:
        """Full multi-line report, suitable for CI output."""
        lines: list[str] = [self.summary()]
        for issue in self.issues:
            lines.append(f"  {issue}")
            lines.append(f"      -> {issue.recommendation}")
        return "\n".join(lines)


def merge(results: Sequence[ValidationResult]) -> tuple[ValidationIssue, ...]:
    """Flatten issues from several results, preserving deterministic order."""
    collected: list[ValidationIssue] = []
    for result in results:
        collected.extend(result.issues)
    return tuple(sorted(collected, key=_sort_key))
