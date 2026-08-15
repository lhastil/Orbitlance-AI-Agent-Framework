"""Runtime Module 4 — Prompt Assembler.

Public surface:

    PromptAssembler(core, *, token_budget=None)
        .assemble(resolved_context, workflow_state, conversation_context)
            -> PromptBundle

`assemble` matches the frozen Public Interface exactly. `CoreBundle` and the
Token Budget port are collaborators, not parameters — see the module docstring
in `prompt_assembler` for why the specification implies that split.
"""

from runtime.assembler.errors import (
    AssemblerError,
    PlaybookLeakError,
    UnknownWorkflowError,
)
from runtime.assembler.ports import TokenBudgetPort
from runtime.assembler.prompt_assembler import PromptAssembler
from runtime.models.budget import BudgetRequest, BudgetSelection, SectionRef
from runtime.models.prompt_bundle import (
    ASSEMBLY_ORDER,
    PromptBundle,
    PromptSection,
    PromptSlot,
)

__all__ = [
    "ASSEMBLY_ORDER",
    "BudgetRequest",
    "BudgetSelection",
    "SectionRef",
    "AssemblerError",
    "PlaybookLeakError",
    "PromptAssembler",
    "PromptBundle",
    "PromptSection",
    "PromptSlot",
    "TokenBudgetPort",
    "UnknownWorkflowError",
]
