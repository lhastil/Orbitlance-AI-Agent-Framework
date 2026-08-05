"""Config rules.

Implements the config-facing checks the spec assigns to this layer:
  * required sections present
  * declared industry playbook(s) actually exist in Core
  * enabled workflows are among the canonical six
  * an LLM provider is declared
  * that provider is registered in the Provider Registry
  * Operating Constraints are additive only and never relax a Core guardrail

Section resolution is exact (see ConfigSectionIndex). Provider checks are split
into two rules because they have different collaborator needs: "is a provider
declared?" is answerable from config.md alone, while "is it registered?" needs
the Provider Registry. Splitting them means the first still runs, and reports
honestly, when no registry is available.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from runtime.models.core_bundle import playbook_key
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import Collaborator, ProjectRule, ProjectRuleContext

_LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*\S)\s*$", re.MULTILINE)
_CODE_TOKEN_RE = re.compile(r"`([^`]+)`")
_BOLD_LABEL_RE = re.compile(r"\*\*(.+?)\*\*\s*:?\s*(.*)")


# --- shared helpers --------------------------------------------------------
def _is_placeholder(text: str) -> bool:
    stripped = text.strip().casefold()
    if not stripped:
        return True
    return any(marker in stripped for marker in spec.PLACEHOLDER_MARKERS)


def _strip_markdown(value: str) -> str:
    return value.replace("*", "").replace("`", "").strip(" .:-\t")


class ConfigSectionIndex:
    """Resolves a config document's headings to canonical section names.

    Resolution is an exact lookup through the framework's documented alias
    table. There is no prefix, substring or fuzzy matching: a heading either is
    a known spelling of a required section or it is not one at all. That makes
    the mapping deterministic and auditable -- adding a tolerated spelling is a
    visible edit to framework_spec.CONFIG_SECTION_ALIASES.

    Built once per rule invocation from the already-parsed section map, so no
    rule re-scans the document.
    """

    __slots__ = ("_by_canonical",)

    def __init__(self, sections: Mapping[str, str]) -> None:
        resolved: dict[str, str] = {}
        for heading, body in sections.items():
            canonical = spec.canonical_config_section(heading)
            # First occurrence wins, so a duplicated heading cannot silently
            # replace the body an earlier rule already reasoned about.
            if canonical is not None and canonical not in resolved:
                resolved[canonical] = body
        self._by_canonical = resolved

    def declares(self, canonical_section: str) -> bool:
        return canonical_section in self._by_canonical

    def body(self, canonical_section: str) -> str | None:
        return self._by_canonical.get(canonical_section)


# --- rules -----------------------------------------------------------------
class ConfigSectionsRule(ProjectRule):
    rule_id = "config.required_sections"
    description = "config.md declares every section the Config template requires."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        index = ConfigSectionIndex(config.sections)
        for required in spec.REQUIRED_CONFIG_SECTIONS:
            if index.declares(required):
                continue
            yield self.issue(
                code=codes.CONF_SECTION_MISSING,
                severity=Severity.ERROR,
                message=f"config.md is missing the {required!r} section.",
                file=config.relative_path,
                section=required,
                recommendation=(
                    f"Add a '## {required}' section to config.md, following "
                    "core/templates/config.md."
                ),
            )


class ConfigPlaybookRule(ProjectRule):
    rule_id = "config.playbook_exists"
    description = "Every industry playbook named in config.md exists in Core."
    required_collaborators = frozenset({Collaborator.CORE_BUNDLE})

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        core = context.core
        assert core is not None  # guaranteed by required_collaborators
        config = context.project.config

        body = ConfigSectionIndex(config.sections).body("Active Industry Playbook")
        if body is None or _is_placeholder(body):
            return  # selecting no playbook is a valid configuration

        for name in self._named_playbooks(body):
            if core.has_playbook(name):
                continue
            known = ", ".join(sorted(core.playbook_names)) or "none loaded"
            yield self.issue(
                code=codes.CONF_PLAYBOOK_UNKNOWN,
                severity=Severity.ERROR,
                message=(
                    f"config.md selects industry playbook {name!r}, which does not "
                    "exist in core/industry_playbooks/."
                ),
                file=config.relative_path,
                section="Active Industry Playbook",
                field_name=name,
                recommendation=(
                    f"Use one of the available playbooks ({known}), or remove the "
                    "selection. Selecting a playbook is a reference only -- it is "
                    "never copied into Knowledge."
                ),
            )

    @staticmethod
    def _named_playbooks(body: str) -> tuple[str, ...]:
        candidates: list[str] = [
            token
            for token in _CODE_TOKEN_RE.findall(body)
            if "industry_playbooks/" in token
            or token.strip().casefold().endswith(".md")
        ]
        if not candidates:
            for item in _LIST_ITEM_RE.findall(body):
                cleaned = _strip_markdown(item)
                if cleaned and not _is_placeholder(cleaned):
                    candidates.append(cleaned.split()[0])

        seen: set[str] = set()
        unique: list[str] = []
        for candidate in candidates:
            key = playbook_key(candidate)
            if key and key not in seen:
                seen.add(key)
                unique.append(candidate)
        return tuple(unique)


class ConfigWorkflowsRule(ProjectRule):
    rule_id = "config.workflows_known"
    description = "Enabled workflows are among the canonical six."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        body = ConfigSectionIndex(config.sections).body("Enabled Workflows")
        if body is None:
            return  # missing section already reported by ConfigSectionsRule

        if _is_placeholder(body):
            yield self.issue(
                code=codes.CONF_NO_WORKFLOWS_ENABLED,
                severity=Severity.WARNING,
                message="config.md does not enable any workflow yet.",
                file=config.relative_path,
                section="Enabled Workflows",
                recommendation=(
                    "List which of the six workflows this project uses "
                    f"({', '.join(spec.CANONICAL_WORKFLOWS)}) and note how each is "
                    "interpreted for this business."
                ),
            )
            return

        for declared in self._declared_workflows(body):
            if self._resolve(declared) is not None:
                continue
            yield self.issue(
                code=codes.CONF_WORKFLOW_UNKNOWN,
                severity=Severity.ERROR,
                message=(
                    f"config.md enables workflow {declared!r}, which is not one of "
                    "the six workflows defined in core/workflows/."
                ),
                file=config.relative_path,
                section="Enabled Workflows",
                field_name=declared,
                recommendation=(
                    "Use one of: "
                    + ", ".join(spec.CANONICAL_WORKFLOWS)
                    + ". Note that Lead Qualification is a prompt module, not a "
                    "workflow."
                ),
            )

    @staticmethod
    def _declared_workflows(body: str) -> tuple[str, ...]:
        found: list[str] = []
        for item in _LIST_ITEM_RE.findall(body):
            text = item.strip()
            match = _BOLD_LABEL_RE.match(text)
            label = (
                match.group(1)
                if match
                else re.split(r"—|--| - ", text, maxsplit=1)[0]
            )
            cleaned = _strip_markdown(label)
            if cleaned and not cleaned.casefold().startswith("not enabled"):
                found.append(cleaned)
        return tuple(found)

    @staticmethod
    def _resolve(declared: str) -> str | None:
        key = declared.strip().casefold().replace("-", " ")
        if key in spec.WORKFLOW_ALIASES:
            return spec.WORKFLOW_ALIASES[key]
        underscored = key.replace(" ", "_")
        return underscored if underscored in spec.CANONICAL_WORKFLOWS else None


def _declared_primary_provider(config_sections: Mapping[str, str]) -> str | None:
    """Extract the declared primary provider, or None if absent/placeholder.

    Shared by the two provider rules so the extraction lives in exactly one
    place; a change to how the field is written cannot make the two rules
    disagree about what was declared.
    """
    body = ConfigSectionIndex(config_sections).body("LLM Provider")
    if body is None:
        return None
    for item in _LIST_ITEM_RE.findall(body):
        match = _BOLD_LABEL_RE.match(item.strip())
        if not match:
            continue
        if _strip_markdown(match.group(1)).casefold().startswith("primary"):
            value = _strip_markdown(match.group(2))
            return None if _is_placeholder(value) else value
    return None


class ConfigProviderDeclaredRule(ProjectRule):
    """Answerable from config.md alone -- needs no collaborator."""

    rule_id = "config.llm_provider_declared"
    description = "A primary LLM provider is declared and is not a placeholder."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists and ConfigSectionIndex(
            context.project.config.sections
        ).declares("LLM Provider")

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        if _declared_primary_provider(config.sections) is not None:
            return
        yield self.issue(
            code=codes.CONF_PROVIDER_NOT_DECLARED,
            severity=Severity.ERROR,
            message=(
                "config.md does not declare a primary LLM provider (the field is "
                "absent or still a placeholder)."
            ),
            file=config.relative_path,
            section="LLM Provider",
            field_name="Primary",
            recommendation=(
                "Set the Primary provider and Model in config.md. A project cannot "
                "activate without a provider the Provider Registry can resolve."
            ),
        )


class ConfigProviderRegisteredRule(ProjectRule):
    """Requires the Provider Registry.

    When no registry is supplied this rule is skipped and recorded as a
    coverage gap, so the result reports PARTIAL rather than claiming the
    provider was checked. It never downgrades a real failure to a warning.
    """

    rule_id = "config.llm_provider_registered"
    description = "The declared LLM provider is registered in the Provider Registry."
    required_collaborators = frozenset({Collaborator.PROVIDER_REGISTRY})

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        if not context.project.config.exists:
            return False
        # Nothing to resolve if no provider was declared; that is
        # ConfigProviderDeclaredRule's finding, not a second report here.
        return _declared_primary_provider(context.project.config.sections) is not None

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        registry = context.provider_registry
        assert registry is not None  # guaranteed by required_collaborators
        config = context.project.config

        primary = _declared_primary_provider(config.sections)
        assert primary is not None  # guaranteed by is_applicable

        if registry.is_registered(primary):
            return

        known = ", ".join(sorted(registry.registered_providers())) or "none"
        yield self.issue(
            code=codes.CONF_PROVIDER_NOT_REGISTERED,
            severity=Severity.ERROR,
            message=(
                f"Declared LLM provider {primary!r} is not registered in the "
                "Provider Registry."
            ),
            file=config.relative_path,
            section="LLM Provider",
            field_name=primary,
            recommendation=(
                "Register the provider adapter, or change config.md to a "
                f"registered provider. Known providers: {known}"
            ),
        )


class ConfigOperatingConstraintsRule(ProjectRule):
    rule_id = "config.operating_constraints_additive"
    description = "Operating Constraints only add restrictions; never relax Core."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        body = ConfigSectionIndex(config.sections).body("Operating Constraints")
        if body is None or _is_placeholder(body):
            return  # empty constraints are explicitly valid

        haystack = body.casefold()
        for phrase in spec.RELAXING_PHRASES:
            if phrase not in haystack:
                continue
            yield self.issue(
                code=codes.CONF_CONSTRAINT_RELAXES_CORE,
                severity=Severity.CRITICAL,
                message=(
                    "An Operating Constraint appears to relax or override a Core "
                    f"guardrail (matched phrase: {phrase!r})."
                ),
                file=config.relative_path,
                section="Operating Constraints",
                field_name=phrase,
                recommendation=(
                    "Operating Constraints are additive only -- they may narrow "
                    "what the agent does but may never weaken core/guardrails/. "
                    "Remove or rewrite this constraint so it adds a restriction."
                ),
            )


CONFIG_RULES: tuple[ProjectRule, ...] = (
    ConfigSectionsRule(),
    ConfigPlaybookRule(),
    ConfigWorkflowsRule(),
    ConfigProviderDeclaredRule(),
    ConfigProviderRegisteredRule(),
    ConfigOperatingConstraintsRule(),
)
