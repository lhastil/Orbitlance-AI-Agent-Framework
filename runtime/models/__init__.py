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
    ValidationIssue,
    ValidationResult,
    ValidationTarget,
)

__all__ = [
    "CoreBundle",
    "ExtensionPoint",
    "ProjectContext",
    "ProjectDocument",
    "Severity",
    "ValidationIssue",
    "ValidationResult",
    "ValidationTarget",
]
