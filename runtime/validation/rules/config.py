"""Config rules.

Implements the config-facing checks the spec assigns to this layer:
  * required sections present
  * declared industry playbook(s) actually exist in Core
  * enabled workflows are among the canonical six
  * declared LLM provider is present and registered (Provider Registry)
  * Operating Constraints are additive only and never relax a Core guardrail
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from runtime.models.core_bundle import playbook_key
from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.ports import is_authoritative
from runtime.validation.rule import ProjectRule, ProjectRuleContext

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


def _section_body(sections: Mapping[str, str], title: str) -> str | None:
    """Fetch a section body, tolerating documented title variants.

    Prefix matching in both directions lets 'Active Industry Playbook' match a
    heading written as 'Active Industry Playbook(s)' without maintaining a
    synonym table for every heading in the framework.
    """
    needle = title.casefold()
    for key, value in sections.items():
        if key.startswith(needle) or needle.startswith(key):
            return value
    return None


# --- rules -----------------------------------------------------------------
class ConfigSectionsRule(ProjectRule):
    rule_id = "config.required_sections"
    description = "config.md declares every section the Config template requires."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        for required in spec.REQUIRED_CONFIG_SECTIONS:
            if _section_body(config.sections, required) is not None:
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

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return (
            context.project.config.exists
            and context.core is not None
            and bool(context.core.playbook_names)
        )

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        core = context.core
        assert core is not None  # guarded by is_applicable
        config = context.project.config

        body = _section_body(config.sections, "Active Industry Playbook")
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
                    "selection. Selecting a playbook is a reference only — it is "
                    "never copied into Knowledge."
                ),
            )

    @staticmethod
    def _named_playbooks(body: str) -> tuple[str, ...]:
        candidates: list[str] = [
            token
            for token in _CODE_TOKEN_RE.findall(body)
            if "industry_playbooks/" in token or token.strip().casefold().endswith(".md")
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
        body = _section_body(config.sections, "Enabled Workflows")
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
                    + ". Note that Lead Qualification is a prompt module, not a workflow."
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


class ConfigProviderRule(ProjectRule):
    rule_id = "config.llm_provider"
    description = "An LLM provider is declared and registered."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        body = _section_body(config.sections, "LLM Provider")
        if body is None:
            return  # missing section already reported

        primary = self._primary(body)
        if primary is None:
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
                    "Set the Primary provider and Model in config.md. A project "
                    "cannot activate without a provider the Provider Registry can "
                    "resolve."
                ),
            )
            return

        registry = context.provider_registry
        if registry is None or registry.is_registered(primary):
            return

        authoritative = is_authoritative(registry)
        suffix = (
            ""
            if authoritative
            else " (No authoritative Provider Registry is wired in yet, so this is "
            "reported as a warning rather than a blocker.)"
        )
        yield self.issue(
            code=codes.CONF_PROVIDER_NOT_REGISTERED,
            severity=Severity.ERROR if authoritative else Severity.WARNING,
            message=(
                f"Declared LLM provider {primary!r} is not registered in the "
                f"Provider Registry.{suffix}"
            ),
            file=config.relative_path,
            section="LLM Provider",
            field_name=primary,
            recommendation=(
                "Register the provider adapter, or change config.md to a registered "
                "provider. Known providers: "
                + (", ".join(sorted(registry.registered_providers())) or "none")
            ),
        )

    @staticmethod
    def _primary(body: str) -> str | None:
        for item in _LIST_ITEM_RE.findall(body):
            match = _BOLD_LABEL_RE.match(item.strip())
            if not match:
                continue
            label = _strip_markdown(match.group(1))
            if label.casefold().startswith("primary"):
                value = _strip_markdown(match.group(2))
                return None if _is_placeholder(value) else value
        return None


class ConfigOperatingConstraintsRule(ProjectRule):
    rule_id = "config.operating_constraints_additive"
    description = "Operating Constraints only add restrictions; never relax Core."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        body = _section_body(config.sections, "Operating Constraints")
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
                    "Operating Constraints are additive only — they may narrow what "
                    "the agent does but may never weaken core/guardrails/. Remove or "
                    "rewrite this constraint so it adds a restriction instead."
                ),
            )


CONFIG_RULES: tuple[ProjectRule, ...] = (
    ConfigSectionsRule(),
    ConfigPlaybookRule(),
    ConfigWorkflowsRule(),
    ConfigProviderRule(),
    ConfigOperatingConstraintsRule(),
)
