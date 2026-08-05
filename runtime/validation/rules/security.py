"""Security rule: no committed credentials anywhere in a project.

core/templates/integrations.md states plainly: "No credentials, API keys, or
endpoint secrets appear anywhere in this document." A committed secret is not a
style problem — it is a disclosed secret — so this reports CRITICAL and blocks
activation.

Scanning covers every project document, not just integrations/, because a
pasted key is most dangerous exactly where nobody thought to look for one.
Matched values are never echoed back in the message; doing so would copy the
secret into logs and audit trails.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from runtime.models.project_context import ProjectDocument
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import ProjectRule, ProjectRuleContext

_COMPILED: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), label) for pattern, label in spec.SECRET_PATTERNS
)


class NoCommittedSecretsRule(ProjectRule):
    rule_id = "security.no_committed_secrets"
    description = "No credential-shaped content appears in any project document."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.root_exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        for document in self._documents(context):
            if not document.exists or document.is_empty:
                continue
            for pattern, label in _COMPILED:
                match = pattern.search(document.raw_text)
                if match is None:
                    continue
                yield self.issue(
                    code=codes.SEC_SECRET_DETECTED,
                    severity=Severity.CRITICAL,
                    message=(
                        f"Possible {label} committed in {document.name!r} "
                        f"(line {self._line_of(document.raw_text, match.start())}). "
                        "The matched value is withheld from this report on purpose."
                    ),
                    file=document.relative_path,
                    field_name=label,
                    recommendation=(
                        "Remove the credential and rotate it — assume it is "
                        "compromised once committed. Store secrets in the runtime "
                        "environment's secret storage; project files record only "
                        "which provider is used, never how to authenticate."
                    ),
                )
                break  # one finding per document is enough to block

    @staticmethod
    def _documents(context: ProjectRuleContext) -> Iterable[ProjectDocument]:
        project = context.project
        for extension_point in project.extension_points:
            yield from extension_point.documents.values()
        yield project.config

    @staticmethod
    def _line_of(text: str, offset: int) -> int:
        return text.count("\n", 0, offset) + 1


SECURITY_RULES: tuple[ProjectRule, ...] = (NoCommittedSecretsRule(),)
