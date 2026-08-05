"""Validator — the Validation Layer's public entry point.

Implements the spec's interface:
    validateCore(coreBundle)   -> ValidationResult
    validateProject(projectContext) -> ValidationResult

Deliberately thin. It orchestrates; it contains no rule logic of its own. If
validation logic starts appearing here, that is the same single-responsibility
smell the spec flags for the Runtime Engine.

It also never decides activation — it only reports. `ValidationResult.valid`
gives the Runtime Engine an unambiguous signal, but acting on it is the Runtime
Engine's job.
"""

from __future__ import annotations

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectContext
from runtime.models.validation import ValidationResult, ValidationTarget
from runtime.validation.pipeline import ValidationPipeline
from runtime.validation.ports import NullProviderRegistry, ProviderRegistryPort
from runtime.validation.registry import RuleRegistry
from runtime.validation.rule import CoreRuleContext, ProjectRuleContext
from runtime.validation.rules import default_core_rules, default_project_rules


class Validator:
    """Validates Core bundles and Project contexts.

    Collaborators are injected so tests can supply narrow rule sets and so the
    real Provider Registry can replace the null one without touching this class.
    """

    def __init__(
        self,
        *,
        project_pipeline: ValidationPipeline | None = None,
        core_pipeline: ValidationPipeline | None = None,
        provider_registry: ProviderRegistryPort | None = None,
    ) -> None:
        self._project_pipeline = project_pipeline or ValidationPipeline(
            RuleRegistry(default_project_rules())
        )
        self._core_pipeline = core_pipeline or ValidationPipeline(
            RuleRegistry(default_core_rules())
        )
        self._provider_registry = provider_registry or NullProviderRegistry()

    # -- public interface (spec) -------------------------------------------
    def validate_project(
        self, project: ProjectContext, core: CoreBundle | None = None
    ) -> ValidationResult:
        """Validate one project. `core` is optional for authoring-time (CI) runs.

        Rules needing Core (template compliance, playbook existence) skip
        themselves when it is absent rather than guessing.
        """
        context = ProjectRuleContext(
            project=project,
            core=core,
            provider_registry=self._provider_registry,
        )
        issues = self._project_pipeline.run(context)
        return ValidationResult.build(
            target=ValidationTarget.PROJECT,
            subject_id=project.project_id or "<unknown project>",
            issues=issues,
        )

    def validate_core(self, core: CoreBundle) -> ValidationResult:
        """Validate the Core bundle's structural completeness and integrity."""
        issues = self._core_pipeline.run(CoreRuleContext(core=core))
        return ValidationResult.build(
            target=ValidationTarget.CORE,
            subject_id="core",
            issues=issues,
        )

    # -- spec-named aliases -------------------------------------------------
    # The spec writes these in camelCase; Python callers get snake_case above.
    validateProject = validate_project  # noqa: N815
    validateCore = validate_core  # noqa: N815

    @property
    def project_rule_count(self) -> int:
        return len(self._project_pipeline.registry)

    @property
    def core_rule_count(self) -> int:
        return len(self._core_pipeline.registry)
