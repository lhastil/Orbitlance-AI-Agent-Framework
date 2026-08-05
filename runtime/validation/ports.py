"""Ports (abstract collaborators) the Validation Layer depends on.

The Validation Layer must validate a project's declared LLM provider against
the Provider Registry, but the Provider Registry is a separate runtime module
that does not exist yet. Depending on a Protocol instead of a concrete class
inverts that dependency: validation depends on an abstraction, and the real
registry satisfies it later without validation changing.

This keeps the module provider-independent — nothing here knows Anthropic from
OpenAI — and keeps the frozen dependency graph acyclic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderRegistryPort(Protocol):
    """Minimum the validator needs from the future Provider Registry."""

    def is_registered(self, provider_id: str) -> bool:
        """True when `provider_id` maps to a registered provider adapter."""
        ...

    def registered_providers(self) -> frozenset[str]:
        """All known provider ids, used to build an actionable error message."""
        ...


class NullProviderRegistry:
    """Stand-in used until the real Provider Registry ships.

    It deliberately reports that it knows no providers and is not authoritative.
    Rules consult `is_authoritative` and downgrade "provider not registered" to
    a warning when no real registry is wired in — otherwise every project would
    fail validation today for a module that does not exist yet.

    This is a bridge, not a permanent component: once the Provider Registry
    lands, inject it and the downgrade stops applying automatically.
    """

    is_authoritative: bool = False

    def is_registered(self, provider_id: str) -> bool:  # noqa: ARG002
        return False

    def registered_providers(self) -> frozenset[str]:
        return frozenset()


def is_authoritative(registry: ProviderRegistryPort) -> bool:
    """Whether a registry's negative answer can be trusted to block activation."""
    return bool(getattr(registry, "is_authoritative", True))
