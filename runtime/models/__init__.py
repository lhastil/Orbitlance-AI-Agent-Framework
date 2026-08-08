"""Shared runtime data models from docs/runtime-specification.md.

These live outside any single module because several modules exchange them.
Each model names its owning module in its docstring; ownership is a discipline
the frozen spec defines, not something the package layout can enforce.
"""

from runtime.models.conversation import (
    ConversationContext,
    Turn,
    TurnRole,
    WorkflowState,
)
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_config import LlmProviderSelection, ProjectConfig
from runtime.models.project_context import (
    ExtensionPoint,
    ProjectContext,
    ProjectDocument,
)
from runtime.models.prompt_bundle import (
    ASSEMBLY_ORDER,
    PromptBundle,
    PromptSection,
    PromptSlot,
)
from runtime.models.resolved_context import (
    ExtensionPointName,
    ResolutionAction,
    ResolutionDecision,
    ResolvedConfig,
    ResolvedContext,
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
    "ASSEMBLY_ORDER",
    "ConversationContext",
    "CoreBundle",
    "ExtensionPoint",
    "ExtensionPointName",
    "LlmProviderSelection",
    "ProjectConfig",
    "ProjectContext",
    "ProjectDocument",
    "PromptBundle",
    "PromptSection",
    "PromptSlot",
    "ResolutionAction",
    "ResolutionDecision",
    "ResolvedConfig",
    "ResolvedContext",
    "RuleExecution",
    "RuleOutcome",
    "Severity",
    "SkipReason",
    "Turn",
    "TurnRole",
    "ValidationCoverage",
    "ValidationIssue",
    "ValidationResult",
    "ValidationTarget",
    "WorkflowState",
]
