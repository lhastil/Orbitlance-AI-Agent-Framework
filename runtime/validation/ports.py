"""Ports (abstract collaborators) the Validation Layer depends on.

The Validation Layer must check a project's declared LLM provider against the
Provider Registry, but the Provider Registry is a separate runtime module that
does not exist yet. Depending on a Protocol instead of a concrete class inverts
that dependency: validation depends on an abstraction, and the real registry
satisfies it later without validation changing.

This keeps the module provider-independent -- nothing here knows Anthropic from
OpenAI -- and keeps the frozen dependency graph acyclic.

There is deliberately **no null/stand-in implementation**. An earlier revision
shipped one that answered "no provider is registered" while flagging itself as
non-authoritative, which caused rules to downgrade a real failure to a warning.
That made the default `Validator()` fail *open*: a project naming a nonexistent
provider passed validation. The correct model is that an absent registry means
the question was never asked -- expressed by omitting the collaborator, so the
rule is recorded as skipped and coverage drops to PARTIAL. Silence is never
substituted for an answer.

Every member of this Protocol is consulted by runtime behaviour. Nothing about
how a registry participates in validation lives outside this interface.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderRegistryPort(Protocol):
    """The complete contract the Validation Layer requires of a registry."""

    def is_registered(self, provider_id: str) -> bool:
        """True when `provider_id` maps to a registered provider adapter.

        A False answer is treated as authoritative and blocks activation. Do not
        implement this port with a placeholder that returns False for everything
        -- omit the collaborator instead, so the gap is reported honestly.
        """
        ...

    def registered_providers(self) -> frozenset[str]:
        """All known provider ids, used to build an actionable error message."""
        ...
