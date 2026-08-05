"""Shared runtime data models from docs/runtime-specification.md.

These live outside any single module because several modules exchange them.
Each model names its owning module in its docstring; ownership is a discipline
the frozen spec defines, not something the package layout can enforce.
"""

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import (
    ExtensionPoint,
    ProjectContext,
    ProjectDocument,
)
from runtime.models.severity import Severity
from runtime.models.validation import (
    RuleExecution,
    RuleOutcome,
    SkipReason,
    ValidationCoverage,
    ValidationIssue,
    ValidationResult,
    ValidationTarget,
)

__all__ = [
    "CoreBundle",
    "ExtensionPoint",
    "ProjectContext",
    "ProjectDocument",
    "RuleExecution",
    "RuleOutcome",
    "Severity",
    "SkipReason",
    "ValidationCoverage",
    "ValidationIssue",
    "ValidationResult",
    "ValidationTarget",
]
