"""Knowledge rules: presence, non-emptiness, and unfilled-placeholder detection.

What this module deliberately does NOT do is enforce section-by-section
equality between a project's knowledge document and its Core template. See
KnowledgeTemplateAvailableRule's docstring for the reasoning: the frozen
framework defines the superset rule between two *Core* files (template and
knowledge contract), not between a template and a project's filled-in document,
and enforcing the latter both invents a rule and misfires badly on real data.

Everything checked here is objective: does the document exist, does it contain
anything, and is that content still template boilerplate.
"""

from __future__ import annotations

from collections.abc import Iterable

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import ProjectRule, ProjectRuleContext


def _is_placeholder(text: str) -> bool:
    stripped = text.strip().casefold()
    if not stripped:
        return True
    return any(marker in stripped for marker in spec.PLACEHOLDER_MARKERS)


class KnowledgeDocumentsPresentRule(ProjectRule):
    rule_id = "knowledge.documents_present"
    description = "All 8 required knowledge documents exist and are non-empty."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.knowledge.present

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        knowledge = context.project.knowledge
        base = f"{context.project.root_path}/{spec.KNOWLEDGE_DIR}".replace("//", "/")

        for required in spec.REQUIRED_KNOWLEDGE_DOCUMENTS:
            document = knowledge.document(required)
            if document is None or not document.exists:
                yield self.issue(
                    code=codes.KNOW_DOCUMENT_MISSING,
                    severity=Severity.ERROR,
                    message=f"Required knowledge document {required!r} is missing.",
                    file=f"{base}/{required}",
                    recommendation=(
                        f"Create {required} from core/templates/"
                        f"{spec.KNOWLEDGE_TEMPLATE_BY_DOCUMENT.get(required, required)} "
                        "and fill in the business's real information."
                    ),
                )
            elif document.is_empty:
                yield self.issue(
                    code=codes.KNOW_DOCUMENT_EMPTY,
                    severity=Severity.ERROR,
                    message=f"Knowledge document {required!r} exists but is empty.",
                    file=document.relative_path or f"{base}/{required}",
                    recommendation=(
                        "Populate the document. An empty knowledge file is treated "
                        "as missing knowledge and fails closed."
                    ),
                )


class KnowledgeTemplateAvailableRule(ProjectRule):
    """Reports when a knowledge document has no template to be checked against.

    Deliberately NOT a strict section-equality check.

    docs/architecture.md defines the superset rule as Template >= Knowledge
    *contract* — a relationship between two Core files. It defines no contract
    requiring a project's filled-in document to reproduce every template
    heading, and enforcing one would invent an architectural rule.

    It would also be wrong in practice: knowledge templates are per-entry
    worksheets (one service, one FAQ entry), while a real project document
    holds a collection and restructures accordingly. Verified empirically —
    strict matching produced 155 false errors against a valid, hand-authored
    project. Document *content* is a human review concern; this layer verifies
    presence, non-emptiness and absence of placeholders, which are objective.
    """

    rule_id = "knowledge.template_available"
    description = "Each knowledge document has a corresponding Core template."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return (
            context.project.knowledge.present
            and context.core is not None
            and bool(context.core.templates)
        )

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        core = context.core
        assert core is not None  # guarded by is_applicable

        for doc_name, template_name in spec.KNOWLEDGE_TEMPLATE_BY_DOCUMENT.items():
            document = context.project.knowledge.document(doc_name)
            if document is None or not document.exists or document.is_empty:
                continue  # already reported by KnowledgeDocumentsPresentRule

            template = core.template(template_name)
            if template is not None and template.exists:
                continue

            yield self.issue(
                code=codes.KNOW_TEMPLATE_UNAVAILABLE,
                severity=Severity.WARNING,
                message=(
                    f"Core template {template_name!r} is unavailable, so authoring "
                    f"guidance for {doc_name!r} cannot be resolved."
                ),
                file=document.relative_path,
                recommendation=(
                    f"Ensure core/templates/{template_name} exists and loads. "
                    "Without it, whoever maintains this document has no worksheet "
                    "to work from."
                ),
            )


class KnowledgePlaceholderRule(ProjectRule):
    rule_id = "knowledge.no_unresolved_placeholders"
    description = "Knowledge sections contain real content, not template placeholders."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.knowledge.present

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        for doc_name in spec.REQUIRED_KNOWLEDGE_DOCUMENTS:
            document = context.project.knowledge.document(doc_name)
            if document is None or not document.exists or document.is_empty:
                continue
            if not _is_placeholder(document.raw_text):
                continue
            yield self.issue(
                code=codes.KNOW_SECTION_PLACEHOLDER,
                severity=Severity.ERROR,
                message=(
                    f"Knowledge document {doc_name!r} still contains only "
                    "unfilled template placeholders."
                ),
                file=document.relative_path,
                recommendation=(
                    "Replace the placeholder text with the business's real "
                    "information. Placeholder knowledge is indistinguishable from "
                    "missing knowledge at runtime and fails closed."
                ),
            )


KNOWLEDGE_RULES: tuple[ProjectRule, ...] = (
    KnowledgeDocumentsPresentRule(),
    KnowledgeTemplateAvailableRule(),
    KnowledgePlaceholderRule(),
)
