"""ValidationPipeline — runs every rule in a registry against one context.

The pipeline is the module's defence against its own single documented failure
mode: "the only true failure is the validator itself crashing on malformed
input it should have handled gracefully — this must never happen."

So a rule that raises does not abort the run and does not vanish silently. It
is converted into an ENGINE001 issue at ERROR severity, meaning a crashed rule
fails the project closed rather than accidentally passing it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation.registry import RuleRegistry
from runtime.validation.rule import ValidationRule

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Executes rules and collects their issues."""

    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> RuleRegistry:
        return self._registry

    def run(self, context: object) -> tuple[ValidationIssue, ...]:
        collected: list[ValidationIssue] = []
        for rule in self._registry:
            collected.extend(self._run_rule(rule, context))
        return tuple(collected)

    def _run_rule(
        self, rule: ValidationRule, context: object
    ) -> Sequence[ValidationIssue]:
        try:
            if not rule.is_applicable(context):
                return ()
            return tuple(rule.evaluate(context))
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all
            # Never let one defective rule take down validation, and never let
            # it pass silently either.
            logger.exception("Validation rule %s raised", rule.rule_id)
            return (
                ValidationIssue(
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
                ),
            )
