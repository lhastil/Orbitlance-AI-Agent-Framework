"""Config rules.

Implements the config-facing checks the spec assigns to this layer:
  * required sections present
  * declared industry playbook(s) actually exist in Core
  * enabled workflows are among the canonical six
  * the first-turn workflow is enabled, and enabled workflows' published
    routing targets are reported when not enabled (WR-3)
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

from runtime.models.project_context import ProjectDocument
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


def _workflow_stem(name: str) -> str:
    """A workflow label or Core file name in the Resolver's comparison form.

    Mirrors the Resolver's `_stem` exactly (`discovery.md` -> `discovery`,
    `CRM Sync` -> `crm_sync`). The Validation Layer may not import the Resolver
    (§13.7), so the rule is restated here; tests/test_vocabulary_alignment.py
    keeps the two equal.
    """
    text = name.strip().casefold()
    if text.endswith(".md"):
        text = text[:-3]
    return text.replace("-", "_").replace(" ", "_")


def _enabled_workflows(context: ProjectRuleContext) -> frozenset[str]:
    """The workflows the Resolver will enable for this project (WR-3).

    Exactly the Resolver's semantics, not `ConfigWorkflowsRule`'s: nothing
    declared enables every Core workflow; anything declared enables only the
    labels that name a Core workflow, so a placeholder-only or unknown-only list
    enables none. Core `Dependencies` enable nothing.
    """
    core = context.core
    assert core is not None  # guaranteed by required_collaborators
    available = frozenset(_workflow_stem(name) for name in core.workflows)
    declared = context.project.config_data.enabled_workflows
    if not declared:
        return available
    return frozenset(
        stem for stem in (_workflow_stem(label) for label in declared) if stem in available
    )


def _published_routing_targets(document: ProjectDocument | None) -> tuple[str, ...]:
    """The workflows a Core workflow document publishes routing phrases for.

    Addressed exactly as the Workflow Router reads them: each third-level
    heading after a "Routing Phrases" section names a target, and counts only
    if a `- ` phrase sits under it. The heading text is the target, so no
    workflow name is written here.
    """
    if document is None:
        return ()
    section_key = spec.ROUTING_PHRASES_SECTION.casefold()
    targets: list[str] = []
    in_routing_section = False
    for section in document.sections:
        if section.heading_level <= 2:
            in_routing_section = section.normalised_heading == section_key
            continue
        if not in_routing_section or section.heading_level != 3:
            continue
        if any(
            (stripped := line.strip()).startswith("- ") and len(stripped) > 2
            for line in section.body.splitlines()
        ):
            targets.append(section.heading_text.strip())
    return tuple(dict.fromkeys(targets))


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


class ConfigFirstTurnWorkflowRule(ProjectRule):
    """WR-3: a project must enable the workflow every conversation starts in."""

    rule_id = "config.first_turn_workflow_enabled"
    description = "The first-turn workflow is enabled."
    required_collaborators = frozenset({Collaborator.CORE_BUNDLE})

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        first = spec.FIRST_TURN_WORKFLOW
        if first in _enabled_workflows(context):
            return
        yield self.issue(
            code=codes.CONF_FIRST_TURN_WORKFLOW_NOT_ENABLED,
            severity=Severity.ERROR,
            message=(
                f"config.md does not enable {first!r}, the workflow every "
                "conversation starts in. The Runtime Engine would refuse to commit "
                "it, so no conversation could enter a workflow."
            ),
            file=context.project.config.relative_path,
            section="Enabled Workflows",
            field_name=first,
            recommendation=(
                f"Enable {first!r} under '## Enabled Workflows'. Every other "
                "workflow remains optional."
            ),
        )


class ConfigRoutingTargetsRule(ProjectRule):
    """WR-3: announce, at activation, the transitions the runtime will refuse.

    A WARNING, not an ERROR: the project still activates, and the Runtime Engine
    refuses each such transition, keeping the conversation where it is.
    """

    rule_id = "config.routing_targets_enabled"
    description = "Every routing target an enabled workflow publishes is enabled."
    required_collaborators = frozenset({Collaborator.CORE_BUNDLE})

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        core = context.core
        assert core is not None  # guaranteed by required_collaborators
        enabled = _enabled_workflows(context)
        for workflow in sorted(enabled):
            document = core.workflows.get(f"{workflow}.md")
            for target in _published_routing_targets(document):
                if target in enabled:
                    continue
                yield self.issue(
                    code=codes.CONF_ROUTING_TARGET_NOT_ENABLED,
                    severity=Severity.WARNING,
                    message=(
                        f"Enabled workflow {workflow!r} publishes routing phrases "
                        f"for {target!r}, which this project does not enable. The "
                        "Runtime Engine will refuse that transition and keep the "
                        f"conversation in {workflow!r}."
                    ),
                    file=context.project.config.relative_path,
                    section="Enabled Workflows",
                    field_name=target,
                    recommendation=(
                        f"Enable {target!r} if conversations should be able to move "
                        f"there from {workflow!r}; otherwise no action is needed."
                    ),
                )


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
    ConfigFirstTurnWorkflowRule(),
    ConfigRoutingTargetsRule(),
    ConfigProviderDeclaredRule(),
    ConfigProviderRegisteredRule(),
    ConfigOperatingConstraintsRule(),
)
