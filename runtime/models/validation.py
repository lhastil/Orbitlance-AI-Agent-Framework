"""ValidationIssue, RuleExecution and ValidationResult.

Implements the `ValidationResult` data model from docs/runtime-specification.md.
The spec lists issue fields as {field, file, severity, message}; this adds
`code`, `section` and `recommendation` so every issue is deterministic and
actionable. That is a superset of the specified model, not a change to it.

Beyond issues, a result records **which rules actually ran**. A rule that was
skipped must never be indistinguishable from a rule that passed, because the
Runtime Engine gates activation on this object and needs to know whether the
verdict is conclusive or merely "nothing was found among the checks we managed
to run".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from runtime.models.severity import Severity


class ValidationTarget(str, Enum):
    """What was validated. Recorded on the result for observability."""

    CORE = "core"
    PROJECT = "project"


class ValidationCoverage(str, Enum):
    """Whether every rule that should have run actually ran."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class RuleOutcome(str, Enum):
    """What happened to one rule during a run."""

    EXECUTED = "executed"
    SKIPPED = "skipped"
    FAILED = "failed"


class SkipReason(str, Enum):
    """Why a rule did not run.

    The distinction is load-bearing, not cosmetic:

    PRECONDITION_ABSENT
        The data this rule inspects is not present, and its absence is already
        reported as a blocking issue by another rule. Nothing went unchecked --
        there was nothing to check. Coverage stays COMPLETE.

    COLLABORATOR_UNAVAILABLE
        A collaborator the rule needs (CoreBundle, Provider Registry) was not
        supplied, so the rule's question is genuinely unanswered. This is a real
        gap in what was verified. Coverage drops to PARTIAL.
    """

    PRECONDITION_ABSENT = "precondition_absent"
    COLLABORATOR_UNAVAILABLE = "collaborator_unavailable"


@dataclass(frozen=True, slots=True)
class RuleExecution:
    """Record of one rule's participation in a run."""

    rule_id: str
    outcome: RuleOutcome
    skip_reason: SkipReason | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.outcome is RuleOutcome.SKIPPED and self.skip_reason is None:
            raise ValueError(
                f"Rule {self.rule_id!r} was skipped without a reason. A skip must "
                "always be explainable, otherwise coverage cannot be trusted."
            )
        if self.outcome is not RuleOutcome.SKIPPED and self.skip_reason is not None:
            raise ValueError(
                f"Rule {self.rule_id!r} has a skip_reason but outcome "
                f"{self.outcome.value!r}."
            )

    @property
    def reduces_coverage(self) -> bool:
        """Whether this execution leaves a question genuinely unanswered."""
        if self.outcome is RuleOutcome.FAILED:
            return True
        return self.skip_reason is SkipReason.COLLABORATOR_UNAVAILABLE

    def to_dict(self) -> dict[str, str | None]:
        return {
            "rule_id": self.rule_id,
            "outcome": self.outcome.value,
            "skip_reason": self.skip_reason.value if self.skip_reason else None,
            "detail": self.detail or None,
        }


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
                    f"(code={self.code!r}) -- generic issues are not permitted."
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


def _issue_sort_key(issue: ValidationIssue) -> tuple[int, str, str, str]:
    """Deterministic ordering: severity first, then stable text fields.

    Determinism matters -- CI diffs and audit logs must not churn because two
    equally-severe issues swapped places between runs.
    """
    return (issue.severity.rank, issue.code, issue.file, issue.section or "")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of validating Core or a Project.

    A result reporting problems is a *successful* run of the validator -- the
    spec is explicit that reporting invalidity is normal output, not failure.
    """

    target: ValidationTarget
    subject_id: str
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    executions: tuple[RuleExecution, ...] = field(default_factory=tuple)
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def build(
        cls,
        target: ValidationTarget,
        subject_id: str,
        issues: Iterable[ValidationIssue],
        executions: Iterable[RuleExecution] = (),
    ) -> ValidationResult:
        return cls(
            target=target,
            subject_id=subject_id,
            issues=tuple(sorted(issues, key=_issue_sort_key)),
            executions=tuple(executions),
        )

    # -- verdict -----------------------------------------------------------
    @property
    def has_blocking_issues(self) -> bool:
        """Whether any ERROR/CRITICAL issue was found."""
        return any(i.severity.blocks_activation() for i in self.issues)

    @property
    def coverage(self) -> ValidationCoverage:
        """Whether every rule that should have run actually ran."""
        if any(e.reduces_coverage for e in self.executions):
            return ValidationCoverage.PARTIAL
        return ValidationCoverage.COMPLETE

    @property
    def valid(self) -> bool:
        """Fail-closed verdict: nothing blocking found AND everything was checked.

        Deliberately conjunctive. `valid` is the property callers reach for by
        default, so the default must be the safe one: a project whose provider
        was never verified is not "valid", it is unverified. Callers wanting the
        narrower question can ask `has_blocking_issues` explicitly.
        """
        return (
            not self.has_blocking_issues
            and self.coverage is ValidationCoverage.COMPLETE
        )

    # -- detail ------------------------------------------------------------
    @property
    def blocking_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity.blocks_activation())

    @property
    def skipped(self) -> tuple[RuleExecution, ...]:
        return tuple(e for e in self.executions if e.outcome is RuleOutcome.SKIPPED)

    @property
    def coverage_gaps(self) -> tuple[RuleExecution, ...]:
        """Executions that left a question genuinely unanswered."""
        return tuple(e for e in self.executions if e.reduces_coverage)

    def of_severity(self, severity: Severity) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is severity)

    def codes(self) -> tuple[str, ...]:
        return tuple(i.code for i in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target.value,
            "subject_id": self.subject_id,
            "valid": self.valid,
            "has_blocking_issues": self.has_blocking_issues,
            "coverage": self.coverage.value,
            "validated_at": self.validated_at.isoformat(),
            "issues": [i.to_dict() for i in self.issues],
            "executions": [e.to_dict() for e in self.executions],
        }

    def summary(self) -> str:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        breakdown = ", ".join(f"{n} {sev}" for sev, n in sorted(counts.items()))
        verdict = "VALID" if self.valid else "INVALID"
        parts = [f"{self.subject_id}: {verdict}", f"coverage={self.coverage.value}"]
        if breakdown:
            parts.append(breakdown)
        return " | ".join(parts)

    def render(self) -> str:
        """Full multi-line report, suitable for CI output."""
        lines: list[str] = [self.summary()]
        for issue in self.issues:
            lines.append(f"  {issue}")
            lines.append(f"      -> {issue.recommendation}")
        for gap in self.coverage_gaps:
            lines.append(f"  [COVERAGE] {gap.rule_id} did not run: {gap.detail}")
        return "\n".join(lines)
