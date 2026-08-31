"""Session Manager — specification §12.

Owns the raw conversational record and the technical session lifecycle. A leaf
module: it depends on nothing else in the runtime.

    from runtime.session import InMemorySessionStore, SessionManager

    sessions = SessionManager(InMemorySessionStore())
    sessions.create_session("conv-1", project_id="sunrise_dental_clinic",
                            channel="web")
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "hello"))   # before the call
    sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "hi"))     # after it

See `manager` for the four ratified decisions (single-turn append, retrieve-only
`get_context`, expiry that never deletes history, no invented retention policy)
and the audit findings behind them.
"""

from runtime.models.session import SessionState, SessionStatus
from runtime.session.errors import (
    OutOfOrderTurnError,
    SessionAlreadyExistsError,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionStoreUnavailableError,
)
from runtime.session.manager import SessionManager
from runtime.session.store import InMemorySessionStore, SessionRecord, SessionStore

__all__ = [
    "InMemorySessionStore",
    "OutOfOrderTurnError",
    "SessionAlreadyExistsError",
    "SessionError",
    "SessionExpiredError",
    "SessionManager",
    "SessionNotFoundError",
    "SessionRecord",
    "SessionState",
    "SessionStatus",
    "SessionStore",
    "SessionStoreUnavailableError",
]
