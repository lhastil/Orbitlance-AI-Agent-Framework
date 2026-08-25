"""Provider-neutral models shared across the provider boundary.

These types describe what *any* LLM provider offers and returns. They name no
vendor, import no SDK, and contain no provider-specific structure — that is the
whole point: Modules 1–5 reason about capacity and responses without ever
learning which provider is behind them.

They live here rather than in `runtime/provider/` because both sides need them.
The Token Budget Manager consumes `ProviderCapabilities` to size its budget;
concrete adapters produce it. If the type lived in the provider package, the
budget module would have to import the provider layer, inverting the dependency
the architecture depends on.

`ProviderCapabilities` previously lived in `runtime/budget/ports.py`. Moving it
here resolves a name collision with the capability model the frozen Provider
Interface contract requires: streaming and tool-calling support are provider
facts the budget module neither owns nor cares about, and keeping two types
called `ProviderCapabilities` would have made the context window a second source
of truth.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """What a provider offers, queryable without a live call.

    `serialization_reserve` is the adapter's **declared** envelope cost — role
    markers, message framing, whatever wrapping it applies around content the
    rest of the runtime never sees. It is declared rather than measured because
    the adapter owns serialization. Specification §9.10 already makes a provider
    that misreports its capabilities a conformance failure, and the adapter's
    own final payload assertion is the backstop if a declaration proves too
    small.

    Phase 1 keeps this a single scalar. It cannot vary with message count, so an
    adapter must declare it conservatively; per-message accounting is a recorded
    future refinement, deliberately not built.

    **C-1a — the reserve also covers output (Phase-1 policy).** Providers bound
    input and output against the same `context_window`, and nothing in the
    framework reserves room for the model's completion: the Token Budget Manager
    budgets input only. So an adapter's declared reserve must cover *both* its
    serialization envelope and its completion allocation, and its own final
    assertion is `serialized request + output allocation <= context_window`,
    checked before the call and failing closed if it cannot be established.

    This deliberately overloads one field rather than adding `max_output_tokens`
    as a second capability. The overload is the known cost, accepted because it
    requires no change to Module 5's arithmetic and no new term in a budget that
    was only just proven exact. A dedicated output capability may replace it
    later — but only through a deliberate architecture change, never as a quiet
    refinement, because splitting the field changes what every existing adapter's
    declared number means.
    """

    context_window: int
    serialization_reserve: int
    streaming_support: bool = False
    tool_calling_support: bool = False

    def __post_init__(self) -> None:
        if self.context_window <= 0:
            raise ValueError("context_window must be positive")
        if self.serialization_reserve < 0:
            raise ValueError("serialization_reserve cannot be negative")

    # A reserve equal to or larger than the window is deliberately *not*
    # rejected here. It is degenerate rather than malformed, and the Token
    # Budget Manager already reports it precisely, as reserved content
    # exceeding the window. Rejecting it at construction would move a runtime
    # budgeting decision into the model and change where that failure surfaces.
    # Adapters are held to the stricter standard by the conformance suite,
    # which is where "declare something usable" belongs.


class ProviderErrorType(str, enum.Enum):
    """The normalised failure classes every adapter maps its vendor errors onto.

    Deliberately small, per specification §9.9: the rest of the runtime handles
    provider failures without knowing which vendor produced them. A new vendor
    error that fits none of these belongs in `UNKNOWN` rather than as a new
    member — growing this enum per provider would defeat normalisation.
    """

    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    CONTEXT_WINDOW_EXCEEDED = "context_window_exceeded"
    INVALID_REQUEST = "invalid_request"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Observability facts about one call. Every field is optional.

    A provider that does not report token usage or latency reports `None` rather
    than a fabricated number — an invented count here would be indistinguishable
    from a measured one downstream.
    """

    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Normalised response from an LLM call, regardless of provider.

    Implements the frozen `ProviderResponse` data model: text, provider
    metadata, a nullable error type, and a raw payload retained for debugging
    only. Written solely by a Provider Interface implementation.

    `raw_payload` is explicitly debug-only. Nothing in the runtime may branch on
    it — doing so would reintroduce provider-specific handling through the back
    door, which `error_type` exists to prevent.
    """

    text: str = ""
    metadata: ProviderMetadata = field(default_factory=ProviderMetadata)
    error_type: ProviderErrorType | None = None
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_payload", MappingProxyType(dict(self.raw_payload)))

    @property
    def failed(self) -> bool:
        return self.error_type is not None
