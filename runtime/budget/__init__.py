"""Runtime Module 5 — Token Budget Manager.

Public surface:

    TokenBudgetManager(tokenizer=..., capabilities=...)
        .select(request) -> BudgetSelection

The manager satisfies the Prompt Assembler's `TokenBudgetPort` structurally, so
neither module imports the other: the seam types live in `runtime/models/`, and
the direction stays Prompt Assembler -> Token Budget Manager.
"""

from runtime.budget.errors import (
    BudgetError,
    BudgetInvariantError,
    FixedOverheadExceedsWindowError,
    KnowledgeDoesNotFitError,
    ProviderCapabilityError,
    ReservedContentExceedsWindowError,
    TokenizerError,
)
from runtime.budget.manager import TokenBudgetManager
from runtime.budget.ports import (
    ProviderCapabilities,
    ProviderCapabilityPort,
    TokenizerPort,
)

__all__ = [
    "BudgetError",
    "BudgetInvariantError",
    "FixedOverheadExceedsWindowError",
    "KnowledgeDoesNotFitError",
    "ProviderCapabilities",
    "ProviderCapabilityError",
    "ProviderCapabilityPort",
    "ReservedContentExceedsWindowError",
    "TokenBudgetManager",
    "TokenizerError",
    "TokenizerPort",
]
