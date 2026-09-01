"""Where audit events are kept.

§15.8 names the external dependency: *"A durable, ideally append-only log
store."* This is the seam that dependency plugs into — a Protocol, plus an
in-memory implementation, following the pattern three committed modules already
use (`ProjectCache`/`InMemoryProjectCache`, `SessionStore`/`InMemorySessionStore`,
`WorkflowStateStore`/`InMemoryWorkflowStateStore`).

**The in-memory implementation is not durable, and this milestone does not
pretend otherwise.** It keeps events for the life of the process and loses them
when the process ends. §15.8 is met on the production activation path, where
`activate()` constructs a durable adapter over this seam (**OB-1** closed
2026-09-01). Which adapter is the composition root's decision and is deliberately
not named here. This in-memory implementation remains `AuditLogger`'s default and
the test store.

Two operations, because §15.6 has two members and neither needs more. There is
no delete, no update, no compaction and no retention sweep: §15.10 makes stored
events immutable, and no retention policy exists anywhere in this repository to
implement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.audit import AuditEvent, AuditFilters


@runtime_checkable
class AuditLogStore(Protocol):
    """The complete contract the Audit Logger requires of a store."""

    def append(self, event: AuditEvent) -> None:
        """Add one event. Never replaces an existing one.

        Append-only is the whole contract: §15.10 says logged events are
        immutable once written, and an implementation that could overwrite
        would make that a hope rather than a property.

        May raise. §15.9 requires that a store failure not block the
        conversation, and the Runtime Engine's guard is what honours that — so
        raising here is the correct way to report a store problem, not a
        violation of it.
        """
        ...

    def query(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        """Every stored event matching `filters`, oldest first.

        Insertion order, by ruling: it is the one ordering an append-only store
        gives without inventing a comparison. Not sorted by timestamp — two
        events can share one — and not paginated, because §15 defines no page.
        """
        ...


class InMemoryAuditLogStore:
    """Append-only storage for one process. **Not durable.**

    Deliberately the simplest thing that satisfies the contract: a list that is
    only ever appended to, and a query that filters and copies. Nothing here
    compacts, evicts, expires or rewrites.

    **No thread-safety is claimed.** §15 states no atomicity requirement — §7.10
    remains the only such clause in the specification — and the runtime is
    single-threaded by §14's explicit posture (RE-3). A lock here would
    manufacture a guarantee nothing asked for, and would be the first step
    toward the concurrency ADR 0003 says must be settled *before* it lands.
    """

    __slots__ = ("_events",)

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        """Append. There is no code path here that touches an existing entry."""
        self._events.append(event)

    def query(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        """Matching events, oldest first.

        Returns a tuple of frozen events, so a caller holds no handle through
        which the log could be mutated — not the list, and not an entry.
        """
        return tuple(event for event in self._events if filters.matches(event))

    def __len__(self) -> int:
        return len(self._events)
