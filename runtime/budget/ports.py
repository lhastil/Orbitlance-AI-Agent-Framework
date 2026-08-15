"""Ports the Token Budget Manager depends on.

Two facts about the world reach this module, and both arrive through a Protocol
rather than a concrete dependency: how many tokens a string costs, and how much
room the target provider has. Neither the tokenizer library nor the provider is
named here, so the module stays provider-independent and testable with doubles.

This follows the pattern already established twice in the runtime —
`ProviderRegistryPort` for the Validation Layer, `TokenBudgetPort` for the
Prompt Assembler — where a module declares what it needs of a collaborator that
does not exist yet.

`ProviderCapabilities` is the shared model in `runtime/models/`, not a type
this module defines: concrete adapters produce it and the frozen Provider
Interface contract returns it, so one authoritative capability model serves
both sides. This module consumes only the two fields budgeting needs.

**There is deliberately no default implementation of either port.** A tokenizer
that guesses, or a capability query that assumes a window size, would let the
budget report success without ever measuring anything — the fail-open class of
defect V-1 recorded. Both collaborators are mandatory; absence is a hard
failure, not a degraded mode.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.provider import ProviderCapabilities


@runtime_checkable
class TokenizerPort(Protocol):
    """Counts tokens in a string. Nothing else."""

    def count_tokens(self, text: str) -> int:
        """The token cost of `text` for the target provider.

        Must be deterministic for identical input and must not mutate anything.
        Raising is the correct response to an unavailable tokenizer — returning
        an estimate would make an approximate budget indistinguishable from an
        exact one.
        """
        ...


@runtime_checkable
class ProviderCapabilityPort(Protocol):
    """Supplies the target provider's capacity, without naming the provider."""

    def capabilities(self) -> ProviderCapabilities:
        """Current capabilities. A capability query, never a live call."""
        ...
