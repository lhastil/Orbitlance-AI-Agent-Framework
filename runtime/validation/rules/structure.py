"""Structural rules: does the project have the shape the framework requires?

Severity follows docs/project-configuration.md's missing-resource table rather
than treating every absence identically:

    Knowledge      -> ERROR   (fail closed; no safe Core default exists)
    Branding       -> WARNING (falls back to Core's neutral default voice)
    Integrations   -> WARNING (degrades that capability, agent still serves)
    Config         -> ERROR   (nothing can be selected or interpreted without it)
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue
from runtime.validation import codes
from runtime.validation import framework_spec as spec
from runtime.validation.rule import ProjectRule, ProjectRuleContext

_PROJECT_ID_RE = re.compile(spec.PROJECT_ID_PATTERN)


class ProjectRootExistsRule(ProjectRule):
    rule_id = "structure.project_root_exists"
    description = "The project directory itself exists."

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        project = context.project
        if project.root_exists:
            return
        yield self.issue(
            code=codes.STRUCT_PROJECT_ROOT_MISSING,
            severity=Severity.CRITICAL,
            message=f"Project directory {project.root_path!r} does not exist.",
            file=project.root_path or "<unknown>",
            recommendation=(
                "Create the project directory under projects/ with the four "
                "extension points (knowledge/, branding/, integrations/, config.md), "
                "using core/templates/ as the starting point."
            ),
        )


class ProjectIdNamingRule(ProjectRule):
    rule_id = "structure.project_id_naming"
    description = "project_id follows the documented lowercase_underscore convention."

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        project_id = context.project.project_id or ""
        if _PROJECT_ID_RE.match(project_id):
            return
        yield self.issue(
            code=codes.STRUCT_PROJECT_ID_INVALID,
            severity=Severity.ERROR,
            message=(
                f"Project id {project_id!r} does not match the required naming "
                "convention (lowercase letters/digits separated by single underscores)."
            ),
            file=context.project.root_path or project_id or "<unknown>",
            recommendation=(
                "Rename the project folder to lowercase with underscores and no "
                "spaces or hyphens, per docs/development-guidelines.md "
                "(e.g. 'Sunrise Dental Clinic' -> 'sunrise_dental_clinic')."
            ),
        )


class _ExtensionPointPresenceRule(ProjectRule):
    """Shared implementation for the four presence checks.

    Extracted so the four rules differ only in data, not logic — the duplication
    this avoids is the exact kind the brief prohibits.
    """

    _code: str = ""
    _severity: Severity = Severity.ERROR
    _dir_name: str = ""
    _label: str = ""
    _consequence: str = ""
    _fix: str = ""

    def _is_present(self, context: ProjectRuleContext) -> bool:
        raise NotImplementedError

    def is_applicable(self, context: ProjectRuleContext) -> bool:
        # Nothing below the root is meaningful if the root itself is missing;
        # ProjectRootExistsRule already reports that, so stay quiet here.
        return context.project.root_exists

    def evaluate(self, context: ProjectRuleContext) -> Iterable[ValidationIssue]:
        if self._is_present(context):
            return
        yield self.issue(
            code=self._code,
            severity=self._severity,
            message=(
                f"Required extension point {self._label!r} is missing. "
                f"{self._consequence}"
            ),
            file=f"{context.project.root_path}/{self._dir_name}".replace("//", "/"),
            recommendation=self._fix,
        )


class KnowledgeDirectoryRule(_ExtensionPointPresenceRule):
    rule_id = "structure.knowledge_directory"
    description = "knowledge/ exists."
    _code = codes.STRUCT_KNOWLEDGE_DIR_MISSING
    _severity = Severity.ERROR
    _dir_name = spec.KNOWLEDGE_DIR
    _label = "knowledge/"
    _consequence = (
        "Knowledge has no safe Core fallback, so the project cannot activate."
    )
    _fix = (
        "Create knowledge/ and populate all 8 documents from core/templates/. "
        "Missing Knowledge must fail closed rather than let the model invent "
        "business facts (docs/project-configuration.md, Resolution Order)."
    )

    def _is_present(self, context: ProjectRuleContext) -> bool:
        return context.project.knowledge.present


class BrandingDirectoryRule(_ExtensionPointPresenceRule):
    rule_id = "structure.branding_directory"
    description = "branding/ exists (warning only — Core default applies)."
    _code = codes.STRUCT_BRANDING_DIR_MISSING
    _severity = Severity.WARNING
    _dir_name = spec.BRANDING_DIR
    _label = "branding/"
    _consequence = "The agent will fall back to Core's neutral default voice."
    _fix = (
        "Optional. Add branding/ from core/templates/branding.md to give this "
        "project its own brand voice; otherwise Core's default voice is used."
    )

    def _is_present(self, context: ProjectRuleContext) -> bool:
        return context.project.branding.present


class IntegrationsDirectoryRule(_ExtensionPointPresenceRule):
    rule_id = "structure.integrations_directory"
    description = "integrations/ exists (warning only — capability degrades)."
    _code = codes.STRUCT_INTEGRATIONS_DIR_MISSING
    _severity = Severity.WARNING
    _dir_name = spec.INTEGRATIONS_DIR
    _label = "integrations/"
    _consequence = (
        "Every tool-backed capability will degrade; the agent will decline those "
        "actions honestly instead of performing them."
    )
    _fix = (
        "Add integrations/ from core/templates/integrations.md and configure a "
        "provider for each of the five core/tools/ contracts the project needs."
    )

    def _is_present(self, context: ProjectRuleContext) -> bool:
        return context.project.integrations.present


class ConfigFileRule(_ExtensionPointPresenceRule):
    rule_id = "structure.config_file"
    description = "config.md exists."
    _code = codes.STRUCT_CONFIG_FILE_MISSING
    _severity = Severity.ERROR
    _dir_name = spec.CONFIG_FILE
    _label = "config.md"
    _consequence = (
        "Without it nothing declares the playbook, provider, workflows or "
        "operating constraints for this project."
    )
    _fix = "Create config.md from core/templates/config.md and fill in every section."

    def _is_present(self, context: ProjectRuleContext) -> bool:
        return context.project.config.exists


STRUCTURE_RULES: tuple[ProjectRule, ...] = (
    ProjectRootExistsRule(),
    ProjectIdNamingRule(),
    KnowledgeDirectoryRule(),
    BrandingDirectoryRule(),
    IntegrationsDirectoryRule(),
    ConfigFileRule(),
)
