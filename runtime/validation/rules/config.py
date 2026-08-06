"""Config rules.

Implements the config-facing checks the spec assigns to this layer:
  * required sections present
  * declared industry playbook(s) actually exist in Core
  * enabled workflows are among the canonical six
  * an LLM provider is declared
  * that provider is registered in the Provider Registry
  * Operating Constraints are additive only and never relax a Core guardrail

**This module does not parse Markdown.** It reads typed fields from
`ProjectContext.config_data`, produced once by the Project Loader (ADR 0004).
Every regex, section index and label extractor that previously lived here has
been deleted. If a check needs something config.md contains but `ProjectConfig`
does not expose, extend the Loader -- never parse here.

The division of knowledge is deliberate and is not duplication:
  * the Loader knows how to *recognise* a heading (parsing vocabulary);
  * this module knows which sections are *required* and which values are
    *acceptable* (policy).
Those are different facts about the framework and live with their owners.
"""

from __future__ import annotations

from collections.abc import Iterable

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import Collaborator, ProjectRule, ProjectRuleContext


def _is_placeholder(text: str | None) -> bool:
    """Whether a declared value is really a value.

    Judging this is validation, not parsing: the Loader reports what the
    document says, and this layer decides whether that counts.
    """
    if text is None:
        return True
    stripped = text.strip().casefold()
    if not stripped:
        return True
    return any(marker in stripped for marker in spec.PLACEHOLDER_MARKERS)


def _declared_provider(context: ProjectRuleContext) -> str | None:
    """The declared primary provider, or None if absent or a placeholder."""
    primary = context.project.config_data.llm_provider.primary
    return None if _is_placeholder(primary) else primary


class ConfigSectionsRule(ProjectRule):
    rule_id = "config.required_sections"
    description = "config.md declares every section the Config template requires."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        declared = context.project.config_data.declared_sections

        for required in spec.REQUIRED_CONFIG_SECTIONS:
            if required in declared:
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

        for name in context.project.config_data.active_playbooks:
            if _is_placeholder(name) or core.has_playbook(name):
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


class ConfigWorkflowsRule(ProjectRule):
    rule_id = "config.workflows_known"
    description = "Enabled workflows are among the canonical six."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return (
            context.project.config.exists
            and context.project.config_data.declares("Enabled Workflows")
        )

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        config = context.project.config
        declared = context.project.config_data.enabled_workflows

        meaningful = [w for w in declared if not _is_placeholder(w)]
        if not meaningful:
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

        for workflow in meaningful:
            if self._resolve(workflow) is not None:
                continue
            yield self.issue(
                code=codes.CONF_WORKFLOW_UNKNOWN,
                severity=Severity.ERROR,
                message=(
                    f"config.md enables workflow {workflow!r}, which is not one of "
                    "the six workflows defined in core/workflows/."
                ),
                file=config.relative_path,
                section="Enabled Workflows",
                field_name=workflow,
                recommendation=(
                    "Use one of: "
                    + ", ".join(spec.CANONICAL_WORKFLOWS)
                    + ". Note that Lead Qualification is a prompt module, not a "
                    "workflow."
                ),
            )

    @staticmethod
    def _resolve(declared: str) -> str | None:
        """Resolve a declared label to a canonical workflow id, or None.

        Resolution lives here rather than in the Loader because it requires the
        framework's canonical workflow list -- policy knowledge, not parsing.
        """
        key = declared.strip().casefold().replace("-", " ")
        if key in spec.WORKFLOW_ALIASES:
            return spec.WORKFLOW_ALIASES[key]
        underscored = key.replace(" ", "_")
        return underscored if underscored in spec.CANONICAL_WORKFLOWS else None


class ConfigProviderDeclaredRule(ProjectRule):
    """Answerable from the loaded config alone -- needs no collaborator."""

    rule_id = "config.llm_provider_declared"
    description = "A primary LLM provider is declared and is not a placeholder."

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return (
            context.project.config.exists
            and context.project.config_data.declares("LLM Provider")
        )

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        if _declared_provider(context) is not None:
            return
        yield self.issue(
            code=codes.CONF_PROVIDER_NOT_DECLARED,
            severity=Severity.ERROR,
            message=(
                "config.md does not declare a primary LLM provider (the field is "
                "absent or still a placeholder)."
            ),
            file=context.project.config.relative_path,
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
        return _declared_provider(context) is not None

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        registry = context.provider_registry
        assert registry is not None  # guaranteed by required_collaborators

        primary = _declared_provider(context)
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
            file=context.project.config.relative_path,
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
        constraints = context.project.config_data.operating_constraints
        if _is_placeholder(constraints):
            return  # empty constraints are explicitly valid

        haystack = constraints.casefold()
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
                file=context.project.config.relative_path,
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
