"""ValidationPipeline -- runs every rule in a registry against one context.

Returns both the issues found and a per-rule execution record. The record is
what makes "skipped" distinguishable from "passed": without it, a rule that
never ran and a rule that found nothing are byte-identical in the output, and
the Runtime Engine cannot tell a conclusive verdict from a partial one.

The pipeline is also the module's defence against its own single documented
failure mode: "the only true failure is the validator itself crashing on
malformed input it should have handled gracefully -- this must never happen."
A rule that raises becomes an ENGINE001 issue at ERROR severity *and* a FAILED
execution, so it both fails the project closed and reduces reported coverage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from runtime.models.severity import Severity
from runtime.models.validation import (
    RuleExecution,
    RuleOutcome,
    SkipReason,
    ValidationIssue,
)
from runtime.validation import codes
from runtime.validation.registry import RuleRegistry
from runtime.validation.rule import Collaborator, RuleContext, ValidationRule

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineRun:
    """Everything one pass over the registry produced."""

    issues: tuple[ValidationIssue, ...]
    executions: tuple[RuleExecution, ...]


class ValidationPipeline:
    """Executes rules and collects their issues and execution records."""

    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> RuleRegistry:
        return self._registry

    def run(self, context: RuleContext) -> PipelineRun:
        issues: list[ValidationIssue] = []
        executions: list[RuleExecution] = []
        available = context.available_collaborators()

        for rule in self._registry:
            rule_issues, execution = self._run_rule(rule, context, available)
            issues.extend(rule_issues)
            executions.append(execution)

        return PipelineRun(issues=tuple(issues), executions=tuple(executions))

    def _run_rule(
        self,
        rule: ValidationRule,
        context: RuleContext,
        available: frozenset[Collaborator],
    ) -> tuple[tuple[ValidationIssue, ...], RuleExecution]:
        missing = rule.required_collaborators - available
        if missing:
            names = ", ".join(sorted(c.description for c in missing))
            return (), RuleExecution(
                rule_id=rule.rule_id,
                outcome=RuleOutcome.SKIPPED,
                skip_reason=SkipReason.COLLABORATOR_UNAVAILABLE,
                detail=f"requires {names}",
            )

        try:
            if not rule.is_applicable(context):
                return (), RuleExecution(
                    rule_id=rule.rule_id,
                    outcome=RuleOutcome.SKIPPED,
                    skip_reason=SkipReason.PRECONDITION_ABSENT,
                    detail="the data this rule inspects is absent and reported elsewhere",
                )
            return tuple(rule.evaluate(context)), RuleExecution(
                rule_id=rule.rule_id, outcome=RuleOutcome.EXECUTED
            )
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all
            # Never let one defective rule take down validation, and never let
            # it pass silently either.
            logger.exception("Validation rule %s raised", rule.rule_id)
            issue = ValidationIssue(
                code=codes.ENGINE_RULE_CRASHED,
                severity=Severity.ERROR,
                message=(
                    f"Validation rule {rule.rule_id!r} failed to execute: "
                    f"{type(exc).__name__}: {exc}"
                ),
                file="<validator>",
                section=rule.rule_id,
                recommendation=(
                    "This is a defect in the validator, not necessarily in the "
                    "project. Treat the project as unvalidated until the rule is "
                    "fixed; do not activate it on the strength of the remaining "
                    "rules alone."
                ),
            )
            return (issue,), RuleExecution(
                rule_id=rule.rule_id,
                outcome=RuleOutcome.FAILED,
                detail=f"{type(exc).__name__}: {exc}",
            )
