"""SessionState — the technical lifecycle of a session.

Implements the `SessionState` data model from docs/runtime-specification.md
(session_id, conversation_id, status, channel_connection_metadata, created_at,
expires_at). Written solely by the Session Manager.

**Deliberately distinct from `ConversationContext`.** The data-model row is
explicit that the two expire independently — *"a session can expire while
ConversationContext's history is retained for audit"*. That separation is the
whole reason this type exists: a session is a connection's technical lifecycle,
while a conversation is a durable record that Compliance requires be kept. One
ending must not end the other, and merging them into a single object would make
that impossible to express.

Lives in `runtime/models/` alongside every other entry in the specification's
data-model table, which is also where `ConversationContext` and `WorkflowState`
already sit.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


class SessionStatus(str, enum.Enum):
    """The three states the data-model row names: active / idle / expired.

    `IDLE` is carried because the frozen row names it, but **nothing transitions
    to it automatically**. No specification text defines what makes a session
    idle — no timeout, no heartbeat, no trigger — so inventing one would be an
    unsourced framework constant of exactly the kind ADR 0002 warns against. It
    is available for a caller that has its own reason to set it, and the Session
    Manager never sets it on its own.
    """

    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class SessionState:
    """One session's technical metadata. Immutable; transitions produce a copy.

    `expires_at` is **never computed by this framework**. The specification says
    sessions expire "per retention policy" and no such policy exists anywhere in
    the repository — not in `core/guardrails/compliance.md`, not in the
    architecture documents. A duration invented here would look authoritative
    while resting on nothing, so the field stays `None` unless a caller supplies
    a value it can defend.
    """

    session_id: str
    conversation_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    channel_connection_metadata: Mapping[str, str] = field(default_factory=dict)
    created_at: str | None = None
    expires_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "channel_connection_metadata",
            MappingProxyType(dict(self.channel_connection_metadata)),
        )

    @property
    def is_active(self) -> bool:
        return self.status is SessionStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        return self.status is SessionStatus.EXPIRED

    def with_status(
        self, status: SessionStatus, *, expires_at: str | None = None
    ) -> SessionState:
        """A copy in a new status. The original is never mutated.

        `expires_at` is only recorded when the caller supplies one; it is not
        derived from the status change.
        """
        return SessionState(
            session_id=self.session_id,
            conversation_id=self.conversation_id,
            status=status,
            channel_connection_metadata=dict(self.channel_connection_metadata),
            created_at=self.created_at,
            expires_at=expires_at if expires_at is not None else self.expires_at,
        )
