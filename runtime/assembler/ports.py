"""Ports the Prompt Assembler depends on.

Spec rule 7 names the Token Budget Manager an internal dependency, but rule 4
does not list its output as an input and that module (Runtime Module 5) does not
exist yet. Depending on a Protocol inverts the dependency, exactly as the
Validation Layer's `ProviderRegistryPort` did for the Provider Registry.

The Token Budget Manager's own spec says its outputs are *"a Knowledge selection
and a history window, both consumed directly by Prompt Assembler — not exposed
as a standalone top-level data model"*. This port is therefore the whole of that
contract.

**One call, not two.** An earlier revision exposed `select_knowledge` and
`select_history` separately. Knowledge has priority over history, so the history
budget is whatever Knowledge leaves — which means a two-call port forces the
implementation to carry the remaining budget between calls as hidden state. A
single call keeps the budget manager stateless.

**On the absent-collaborator default.** Omitting this port selects every
Knowledge section and the full history. That is not the fail-open mistake V-1
recorded: nothing is claimed unverified. The Token Budget Manager's frozen
responsibility is to *"select which Knowledge sections to include (Phase 1: all
of them)"*, so the default reproduces the specified Phase 1 behaviour. Budget
arithmetic and token counting stay entirely behind this port, because rule 3
forbids the assembler from counting tokens itself.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.budget import BudgetRequest, BudgetSelection


@runtime_checkable
class TokenBudgetPort(Protocol):
    """The complete contract the Prompt Assembler requires of a budget manager."""

    def select(self, request: BudgetRequest) -> BudgetSelection:
        """Choose the Knowledge sections and history turns that fit.

        `request.fixed_sections` holds the **already-rendered** fixed content, so
        the implementation counts exactly what will be sent rather than modelling
        how the assembler formats it. It must never reconstruct that formatting.

        Knowledge is returned as `(document name, ordinal)` references. Ordinal
        identity is required: headings repeat, so a heading cannot address a
        section. Any reference the assembler cannot resolve is skipped rather
        than invented — the assembler never fabricates Knowledge.

        Phase 1 policy is full Knowledge or fail closed: an implementation that
        cannot fit every section must raise rather than return a subset. Partial
        selection awaits an authoritative retrieval mechanism.
        """
        ...
