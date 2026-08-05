"""Core rules — structural completeness and integrity of `core/`.

Two of these are defence-in-depth against defects the framework has already
suffered once:

  CORE005  playbook content leaking into the CoreBundle. Playbooks are
           reference-only; the spec calls their presence in a CoreBundle a
           Core Loader defect, so this catches a Loader bug, not a data one.

  CORE006  client-specific content inside Core. This is the hardcoded-SLA class
           of bug found in the original architecture review ("the Orbitlance
           team will contact you within 24 hours" baked into a shared prompt).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from runtime.models.project_context import ProjectDocument
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import CoreRule, CoreRuleContext

_CLIENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), label) for pattern, label in spec.CLIENT_SPECIFIC_PATTERNS
)


class _RequiredCoreFilesRule(CoreRule):
    """Shared implementation of the four 'required files exist' checks."""

    _code: str = ""
    _group_label: str = ""
    _required: tuple[str, ...] = ()

    def _group(self, core: CoreRuleContext) -> dict[str, ProjectDocument]:
        raise NotImplementedError

    def evaluate(self, context: CoreRuleContext) -> Iterable[ValidationIssue]:
        present = self._group(context)
        for required in self._required:
            document = present.get(required)
            if document is not None and document.exists and not document.is_empty:
                continue
            state = "missing" if document is None or not document.exists else "empty"
            yield self.issue(
                code=self._code,
                severity=Severity.CRITICAL,
                message=(
                    f"Required Core {self._group_label} {required!r} is {state}."
                ),
                file=f"core/{self._group_label}/{required}",
                recommendation=(
                    f"Restore {required}. Core is frozen and shared by every "
                    "project — the runtime must not start without it."
                ),
            )


class CorePromptsRule(_RequiredCoreFilesRule):
    rule_id = "core.prompts_present"
    description = "All ten Core prompt modules are present."
    _code = codes.CORE_PROMPT_MISSING
    _group_label = "prompts"
    _required = spec.REQUIRED_PROMPTS

    def _group(self, core: CoreRuleContext) -> dict[str, ProjectDocument]:
        return dict(core.core.prompts)


class CoreGuardrailsRule(_RequiredCoreFilesRule):
    rule_id = "core.guardrails_present"
    description = "The complete Guardrails Bundle is present."
    _code = codes.CORE_GUARDRAIL_MISSING
    _group_label = "guardrails"
    _required = spec.GUARDRAIL_BUNDLE

    def _group(self, core: CoreRuleContext) -> dict[str, ProjectDocument]:
        return dict(core.core.guardrails)


class CoreWorkflowsRule(_RequiredCoreFilesRule):
    rule_id = "core.workflows_present"
    description = "All six canonical workflows are present."
    _code = codes.CORE_WORKFLOW_MISSING
    _group_label = "workflows"
    _required = tuple(f"{name}.md" for name in spec.CANONICAL_WORKFLOWS)

    def _group(self, core: CoreRuleContext) -> dict[str, ProjectDocument]:
        return dict(core.core.workflows)


class CoreToolContractsRule(_RequiredCoreFilesRule):
    rule_id = "core.tool_contracts_present"
    description = "All five tool contracts are present."
    _code = codes.CORE_TOOL_CONTRACT_MISSING
    _group_label = "tools"
    _required = tuple(f"{name}.md" for name in spec.TOOL_CONTRACTS)

    def _group(self, core: CoreRuleContext) -> dict[str, ProjectDocument]:
        return dict(core.core.tool_contracts)


class NoPlaybookContentInCoreBundleRule(CoreRule):
    rule_id = "core.no_playbook_content"
    description = "The CoreBundle carries playbook names only, never their content."

    def evaluate(self, context: CoreRuleContext) -> Iterable[ValidationIssue]:
        core = context.core
        for document in core.all_documents:
            path = (document.relative_path or "").replace("\\", "/")
            if "industry_playbooks/" not in path:
                continue
            yield self.issue(
                code=codes.CORE_PLAYBOOK_CONTENT_LEAKED,
                severity=Severity.CRITICAL,
                message=(
                    f"Industry playbook content ({document.name!r}) is present inside "
                    "the CoreBundle. Playbooks are reference-only and must never be "
                    "loaded at runtime."
                ),
                file=path or document.name,
                recommendation=(
                    "Fix the Core Loader so it excludes core/industry_playbooks/ from "
                    "the CoreBundle. Playbooks guide the human authoring Knowledge "
                    "and Operating Constraints; they are never prompt input."
                ),
            )


class NoClientSpecificContentInCoreRule(CoreRule):
    rule_id = "core.no_client_specific_content"
    description = "Core files contain no client-specific values (SLA, contact, price)."

    def evaluate(self, context: CoreRuleContext) -> Iterable[ValidationIssue]:
        for document in context.core.all_documents:
            if not document.exists or document.is_empty:
                continue
            if document.name in spec.CLIENT_PATTERN_EXEMPT_FILES:
                continue
            for pattern, label in _CLIENT_PATTERNS:
                match = pattern.search(document.raw_text)
                if match is None:
                    continue
                yield self.issue(
                    code=codes.CORE_CLIENT_SPECIFIC_CONTENT,
                    severity=Severity.ERROR,
                    message=(
                        f"Core file {document.name!r} contains a {label}: "
                        f"{match.group(0).strip()!r}. Core is shared by every client "
                        "and must stay client-agnostic."
                    ),
                    file=document.relative_path or document.name,
                    field_name=label,
                    recommendation=(
                        "Move the value into the project's Knowledge (e.g. Contact "
                        "or Pricing) and reference it as a placeholder from Core, as "
                        "was done for {{business_name}} / {{expected_response_time}}."
                    ),
                )
                break


CORE_RULES: tuple[CoreRule, ...] = (
    CorePromptsRule(),
    CoreGuardrailsRule(),
    CoreWorkflowsRule(),
    CoreToolContractsRule(),
    NoPlaybookContentInCoreBundleRule(),
    NoClientSpecificContentInCoreRule(),
)
