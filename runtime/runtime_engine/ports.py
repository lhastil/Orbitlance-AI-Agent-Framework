"""The observability seam §14 needs before §15 exists.

§14.2 ends its pipeline with *"observability logging"*, and §15 — the module
that owns it — is not implemented. This is the smallest Protocol that keeps that
architectural seam real rather than imagined, and it is **§14-local**: when §15
is built it owns the contract, and this Protocol is replaced rather than
extended.

**No `AuditEvent` model is created.** §15.4 describes an event as *"type,
`project_id`, `conversation_id`, payload"*, so the four arguments below carry
exactly that and a model would add nothing §14 needs. Naming the frozen type
before §15 can specify it is how a placeholder becomes a constraint.

Nothing here logs, persists, batches, retries, or reaches a network. The default
implementation does nothing at all. That is not a stub standing in for work —
it is the honest state of a runtime whose audit logger has not been built, and
it is visible rather than hidden behind an interface that looks complete.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ObservabilitySink(Protocol):
    """Where the Runtime Engine reports what happened on a turn."""

    def record(
        self,
        event_type: str,
        project_id: str,
        conversation_id: str,
        payload: Mapping[str, str],
    ) -> None:
        """Record one auditable event.

        `payload` carries only values the engine can state about the turn's
        *outcome* — never the customer's message, never the assembled prompt,
        never the provider's text. §15.3 forbids logging *"raw credentials or
        PII beyond what Compliance's data-handling rules allow"*, and no such
        allowance has been written, so the engine records nothing that could
        need one.

        **May fail; failing must not matter.** §15.9 is explicit that a log
        store being unavailable *"must not block the conversation from
        proceeding"*. The engine calls this inside its own guard, so an
        implementation that raises cannot turn a logging problem into a
        conversation problem.
        """
        ...


class NullObservabilitySink:
    """Records nothing.

    The default, and deliberately not a queue, a buffer or a deferred writer:
    a sink that quietly accumulates events nobody drains is worse than one that
    plainly does nothing, because it looks like it is working.

    §15.9 also notes that a silent audit gap *"is itself a Compliance risk"*.
    That risk is real and is recorded as RE-4 rather than papered over here —
    running with this default means the runtime keeps no audit trail.
    """

    __slots__ = ()

    def record(
        self,
        event_type: str,
        project_id: str,
        conversation_id: str,
        payload: Mapping[str, str],
    ) -> None:
        del event_type, project_id, conversation_id, payload
