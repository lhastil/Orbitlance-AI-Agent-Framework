"""Ports the Prompt Assembler depends on.

Spec rule 7 names the Token Budget Manager an internal dependency, but rule 4
does not list its output as an input and that module (Runtime Module 5) does not
exist yet. Depending on a Protocol inverts the dependency, exactly as the
Validation Layer's `ProviderRegistryPort` did for the Provider Registry.

The Token Budget Manager's own spec says its outputs are *"a Knowledge selection
and a history window, both consumed directly by Prompt Assembler — not exposed
as a standalone top-level data model"*. This port is therefore the whole of that
contract, and no `KnowledgeSelection` type is introduced.

**On the absent-collaborator default.** Omitting this port yields all Knowledge
and the full history. That is not the fail-open mistake V-1 recorded: nothing is
being claimed unverified. The Token Budget Manager's frozen responsibility is to
*"select which Knowledge sections to include (Phase 1: all of them)"*, so the
default reproduces the specified Phase 1 behaviour rather than substituting
silence for an answer. Budget arithmetic stays entirely behind this port,
because rule 3 forbids the assembler from counting tokens itself.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.conversation import ConversationContext, Turn
from runtime.models.resolved_context import ResolvedContext


@runtime_checkable
class TokenBudgetPort(Protocol):
    """The complete contract the Prompt Assembler requires of a budget manager."""

    def select_knowledge(self, context: ResolvedContext) -> tuple[str, ...]:
        """Knowledge document names to include, in the order they should appear.

        Names must be keys of `context.knowledge`. Any name the assembler cannot
        resolve is skipped rather than invented — the assembler never fabricates
        Knowledge content.
        """
        ...

    def select_history(self, conversation: ConversationContext) -> tuple[Turn, ...]:
        """The history window to include, oldest first.

        Truncation policy — oldest turn first, never mid-turn — belongs to the
        implementation, not here.
        """
        ...
