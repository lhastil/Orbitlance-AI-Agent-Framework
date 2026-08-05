"""Branding and Integrations rules.

Both are non-blocking by design, per docs/project-configuration.md's
missing-resource table: Branding falls back to Core's neutral voice, and
Integrations degrades the affected capability. Neither justifies refusing to
activate a project, so both report at WARNING.
"""

from __future__ import annotations

from collections.abc import Iterable

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import ProjectRule, ProjectRuleContext


class BrandingContentRule(ProjectRule):
    rule_id = "branding.has_content"
    description = "branding/ contains at least one non-empty document."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.root_exists and context.project.branding.present

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        branding = context.project.branding
        if not branding.is_empty:
            return
        yield self.issue(
            code=codes.BRAND_EMPTY,
            severity=Severity.WARNING,
            message="branding/ exists but contains no usable content.",
            file=f"{context.project.root_path}/{spec.BRANDING_DIR}".replace("//", "/"),
            recommendation=(
                "Populate branding from core/templates/branding.md, or remove the "
                "folder. Either way the agent falls back to Core's default voice — "
                "an empty folder just makes that fallback less obvious."
            ),
        )


class IntegrationsCoverageRule(ProjectRule):
    rule_id = "integrations.contract_coverage"
    description = "Each of the five tool contracts is addressed or knowingly skipped."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return (
            context.project.root_exists
            and context.project.integrations.present
            and not context.project.integrations.is_empty
        )

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        integrations = context.project.integrations
        combined = "\n".join(
            doc.raw_text for doc in integrations.documents.values() if doc.exists
        ).casefold()

        for contract in spec.TOOL_CONTRACTS:
            if self._mentions(combined, contract):
                continue
            label = spec.TOOL_CONTRACT_LABELS[contract]
            yield self.issue(
                code=codes.INTEG_CONTRACT_UNCONFIGURED,
                severity=Severity.WARNING,
                message=(
                    f"Tool contract {label!r} has no provider configured in "
                    "integrations/."
                ),
                file=f"{context.project.root_path}/{spec.INTEGRATIONS_DIR}".replace(
                    "//", "/"
                ),
                section=label,
                recommendation=(
                    f"Add a '{label}' section naming the provider, or record "
                    "deliberately that this project does not need it. An "
                    "unconfigured contract degrades that capability at runtime."
                ),
            )

    @staticmethod
    def _mentions(haystack: str, contract: str) -> bool:
        needles = {
            contract.replace("_", " "),
            contract,
            f"core/tools/{contract}.md",
            spec.TOOL_CONTRACT_LABELS[contract].casefold(),
        }
        return any(needle in haystack for needle in needles)


EXTENSION_POINT_RULES: tuple[ProjectRule, ...] = (
    BrandingContentRule(),
    IntegrationsCoverageRule(),
)
