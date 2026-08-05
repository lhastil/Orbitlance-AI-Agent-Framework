"""Validation Layer — docs/runtime-specification.md module 13.

Verifies structural and content-level correctness of Core and Project data
before it is used, at authoring time (CI) and at activation time (runtime).

Fails closed: any ERROR or CRITICAL issue makes ValidationResult.valid False,
and the Runtime Engine must refuse to activate such a project.
"""

from runtime.validation.pipeline import ValidationPipeline
from runtime.validation.ports import NullProviderRegistry, ProviderRegistryPort
from runtime.validation.registry import DuplicateRuleError, RuleRegistry
from runtime.validation.rule import (
    CoreRule,
    CoreRuleContext,
    ProjectRule,
    ProjectRuleContext,
    ValidationRule,
)
from runtime.validation.rules import default_core_rules, default_project_rules
from runtime.validation.validator import Validator

__all__ = [
    "CoreRule",
    "CoreRuleContext",
    "DuplicateRuleError",
    "NullProviderRegistry",
    "ProjectRule",
    "ProjectRuleContext",
    "ProviderRegistryPort",
    "RuleRegistry",
    "ValidationPipeline",
    "ValidationRule",
    "Validator",
    "default_core_rules",
    "default_project_rules",
]
