"""Where sessions are persisted.

§12.8 names a persistence store as this module's external dependency, and §12.11
records cross-channel continuity as a future extension. Both are served by
depending on a Protocol rather than on a concrete store: swapping to a database
means adding an implementation here and touching nothing else.

Modelled directly on `runtime.loader.cache.ProjectCache` /
`InMemoryProjectCache`, the pattern the Project Loader already established, so
there is one persistence idiom in the runtime rather than two.

A store deals in **records only**. It performs no validation, enforces no
ordering, and knows nothing about turns, expiry semantics or project isolation —
those are the Session Manager's rules, and a store that also enforced them would
mean two places could disagree about what a valid session is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from runtime.models.conversation import ConversationContext
from runtime.models.session import SessionState


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """One conversation and its session, stored together.

    They are written as a unit because they are created as a unit and every
    Session Manager operation reads both — but they remain separate objects,
    because the data-model row requires them to expire independently.
    """

    context: ConversationContext
    state: SessionState


@runtime_checkable
class SessionStore(Protocol):
    """Read/write access to stored sessions."""

    def get(self, conversation_id: str) -> SessionRecord | None:
        """The stored record, or None when nothing is stored under that id."""
        ...

    def put(self, conversation_id: str, record: SessionRecord) -> None:
        """Store a record, replacing any previous one for that id."""
        ...

    def conversation_ids(self) -> tuple[str, ...]:
        """Every stored id, in deterministic order. For audit enumeration."""
        ...


class InMemorySessionStore:
    """Process-local storage. The default, and enough for a single process.

    Deliberately has **no delete**. §12.12(d) requires an expired session's
    history to remain in an audit archive and never simply be deleted, so the
    store offers no way to remove a record — the guarantee is structural rather
    than a rule someone has to remember. A real archival store may tier records
    to cold storage, but removal is not part of this interface.
    """

    __slots__ = ("_records",)

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    def get(self, conversation_id: str) -> SessionRecord | None:
        return self._records.get(conversation_id)

    def put(self, conversation_id: str, record: SessionRecord) -> None:
        self._records[conversation_id] = record

    def conversation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    def __len__(self) -> int:
        return len(self._records)
