"""Audit Logger — specification §15.

The one consistent way any module records an auditable event, and the owner of
the audit contract. It replaces the placeholder seam §14 carried while this
module did not exist.

§15.6's two members, spelled in this repository's convention:

    log_event(event) -> AuditEvent
    query_audit_log(filters) -> tuple[AuditEvent, ...]

**A pure recorder.** §15.3 is unambiguous: *"Never makes decisions based on what
it logs — a pure recorder, not a decision-maker (it must never itself decide to
block a request based on an observed pattern; that's Guardrail Engine's job)."*
Nothing here inspects a payload, counts anything, compares an event to a
previous one, or returns a verdict. It stamps, stores, and reads back.

**A leaf.** §15.7: *"it depends on nothing else in the runtime."* This module
imports `runtime.models` and the standard library, and that is all.

---

## What the logger owns, and what the caller owns

    caller supplies   type, project_id, conversation_id, payload
    logger assigns    event_id, timestamp

`event_id` is generated here, from `uuid4`, following the identity precedent
`SessionManager` already set. **A caller cannot supply one**: whatever
`AuditEvent.event_id` holds on the way in is replaced on the way out.

That has a consequence §15.12(d) is written against, and it is stated plainly
rather than engineered around: *"a second write to the same event ID is rejected
or versioned, never overwritten."* Because ids are generated per call and are
opaque, **two calls can never collide**, so the duplicate case cannot arise from
outside this module. No artificial duplicate detection was added to make the
clause look satisfied. Recorded as **OB-2**.

## What it does not do

* **No redaction.** §15.3 forbids logging PII beyond what Compliance allows, and
  `core/guardrails/compliance.md`'s Data Privacy section is prose obligation, not
  a machine-checkable allowance. The logger records the structured payload it is
  handed. Deciding what may be in a payload belongs to the module that builds
  it — and §14 already builds a payload of five outcome scalars, verified by
  test to contain no message, prompt or answer.
* **No event-type vocabulary.** There is no enum. §14's four string constants
  are the only event types that exist; a future module can emit its own without
  amending anything here, which is what §15.2's *"from any module"* requires.
* **No retention, no authorization, no pagination.** None is defined anywhere.
* **No alert on its own failure.** §15.9 requires one; the repository has no
  metrics or alerting seam, and inventing an external dependency to satisfy the
  wording was explicitly out of scope. **§15.9 is therefore partially met** — the
  non-blocking half holds, the alert half does not. Recorded as **OB-3**.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from runtime.models.audit import AuditEvent, AuditFilters
from runtime.observability.store import AuditLogStore, InMemoryAuditLogStore


def _utc_now() -> str:
    """An ISO-8601 UTC timestamp, matching `SessionManager`'s convention."""
    return datetime.now(UTC).isoformat()


@runtime_checkable
class AuditLog(Protocol):
    """§15.6's interface, as every other module sees it.

    Consumers depend on this rather than on `AuditLogger` or on a store, so the
    persistence choice stays behind the seam §15.8 describes.
    """

    def log_event(self, event: AuditEvent) -> AuditEvent:
        """Record one event and return it as stored (§15.5's confirmation)."""
        ...

    def query_audit_log(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        """Every matching event, oldest first."""
        ...


class AuditLogger:
    """§15's implementation. Stamps identity and time, then appends.

    The store is injected so a durable implementation can replace the in-memory
    one without touching this class — which is the whole point of §15.8 being an
    *external* dependency. It defaults to a fresh `InMemoryAuditLogStore` so a
    logger is never silently shared between two of them.
    """

    __slots__ = ("_store", "_clock", "_new_event_id")

    def __init__(
        self,
        store: AuditLogStore | None = None,
        *,
        clock: Callable[[], str] = _utc_now,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store if store is not None else InMemoryAuditLogStore()
        self._clock = clock
        self._new_event_id = event_id_factory or (lambda: uuid.uuid4().hex)

    # -- §15.6 ---------------------------------------------------------------
    def log_event(self, event: AuditEvent) -> AuditEvent:
        """Stamp the event with a generated identity and time, then store it.

        Returns the stored event — §15.5's *"persistence confirmation"*, and the
        only way a caller learns the id its event was given.

        The returned event is frozen, and the id and timestamp on it are this
        logger's, not the caller's. Raises if the store raises: reporting a
        store problem is correct, and containing it so a conversation is
        unaffected is §14's job, which it already does (§15.9).
        """
        recorded = AuditEvent(
            type=event.type,
            project_id=event.project_id,
            conversation_id=event.conversation_id,
            payload=event.payload,
            event_id=self._new_event_id(),
            timestamp=self._clock(),
        )
        self._store.append(recorded)
        return recorded

    def query_audit_log(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        """Events matching every supplied filter, in insertion order.

        Delegates to the store, which owns ordering. Empty filters return
        everything; the three authorized fields AND together.
        """
        return self._store.query(filters)
