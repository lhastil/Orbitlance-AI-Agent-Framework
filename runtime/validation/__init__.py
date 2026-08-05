"""Validation Layer -- docs/runtime-specification.md module 13.

Verifies structural and content-level correctness of Core and Project data
before it is used, at authoring time (CI) and at activation time (runtime).

Fails closed in two senses:
  * any ERROR/CRITICAL issue makes ValidationResult.valid False; and
  * incomplete coverage (a rule that could not run) also makes it False,
    so "never checked" is never mistaken for "checked and fine".
"""

from runtime.validation.pipeline import PipelineRun, ValidationPipeline
from runtime.validation.ports import ProviderRegistryPort
from runtime.validation.registry import DuplicateRuleError, RuleRegistry
from runtime.validation.rule import (
    Collaborator,
    CoreRule,
    CoreRuleContext,
    ProjectRule,
    ProjectRuleContext,
    RuleContext,
    ValidationRule,
)
from runtime.validation.rules import default_core_rules, default_project_rules
from runtime.validation.validator import Validator

__all__ = [
    "Collaborator",
    "CoreRule",
    "CoreRuleContext",
    "DuplicateRuleError",
    "PipelineRun",
    "ProjectRule",
    "ProjectRuleContext",
    "ProviderRegistryPort",
    "RuleContext",
    "RuleRegistry",
    "ValidationPipeline",
    "ValidationRule",
    "Validator",
    "default_core_rules",
    "default_project_rules",
]
