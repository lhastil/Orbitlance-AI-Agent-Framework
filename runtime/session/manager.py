"""Session Manager — specification §12.

Owns the technical lifecycle of a session and the raw conversational record.
A leaf module: §12.7 states it depends on nothing else in the runtime, and it
does not. The Prompt Assembler, Token Budget Manager and Guardrail Engine read
what it writes; none of them is imported here.

It is the sole writer of two frozen data models — `ConversationContext` (the
durable record) and `SessionState` (the technical lifecycle) — which expire
independently, because Compliance requires history to outlive the connection
that produced it.

---

## Ratified decisions, and the audit findings behind them

These are recorded here rather than in a document because they are the reasons
this module has the shape it does, and a reader changing it needs them.

**D-1 — `append_turn` records exactly one turn.** The frozen §12.6 signature
`appendTurn(conversation_id, message, response)` reads as a user+response pair
appended after the provider call. That interpretation breaks Modules 4 and 5.
Both locate the latest USER turn and treat it as the message being answered:
`ConversationContext.latest_user_message` ships it as `PromptBundle.latest_message`,
and the Token Budget Manager's `_history_turns` excludes it from history *by
position*. If the incoming message were not yet appended at assembly time, the
assembler would answer the **previous** question and the previous user turn
would also be dropped from history — two silent defects compounding.

Single-turn append is also what §12.4 describes ("new message/response to
append", singular) and what §12.9 requires: a user turn recorded before the
provider call survives a provider failure, where a pair appended afterwards
would be lost.

**D-2 — `get_context` is retrieve-only.** `ConversationContext` requires
`project_id`, and `getContext(conversation_id)` carries none. Creating one here
would mean inventing a project, and §12.3 forbids persisting across projects
while §12.12(c) requires that two conversations never share data. Creation is
`create_session`, which takes the identity it needs.

**D-3 — expiry never deletes history.** §12.12(d): expired sessions are *"no
longer retrievable but remain in an audit archive … never simply deleted"*.
`expire` transitions `SessionState.status`; the `ConversationContext` is
untouched and stays reachable through `archived_context`. The store has no
delete operation at all, so this is structural.

**D-4 — no retention duration is invented.** §12.2 and §12.12(d) both defer to a
"retention policy" that exists nowhere in the repository. `expires_at` is
recorded only when a caller supplies it, and nothing here computes one.

**Open, and not this module's to close:** the Assembler also needs a
`WorkflowState`, whose sole writer is the unbuilt Workflow State Manager (§7).
Session Manager alone therefore does not enable an end-to-end assembly path.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from runtime.models.conversation import ConversationContext, Turn
from runtime.models.session import SessionState, SessionStatus
from runtime.session.errors import (
    OutOfOrderTurnError,
    SessionAlreadyExistsError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionStoreUnavailableError,
)
from runtime.session.store import InMemorySessionStore, SessionRecord, SessionStore


def _utc_now() -> str:
    """An ISO-8601 UTC timestamp. Injectable so tests are deterministic."""
    return datetime.now(UTC).isoformat()


class SessionManager:
    """Creates, reads, appends to and expires sessions (§12.6).

    The clock and id factory are injected rather than called directly, so a test
    can make timestamps and session ids deterministic without patching module
    globals — the same reason every other module here takes its collaborators by
    construction.
    """

    __slots__ = ("_clock", "_new_session_id", "_store")

    def __init__(
        self,
        store: SessionStore | None = None,
        *,
        clock: Callable[[], str] = _utc_now,
        session_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store if store is not None else InMemorySessionStore()
        self._clock = clock
        self._new_session_id = session_id_factory or (lambda: uuid.uuid4().hex)

    # -- creation (D-2) -------------------------------------------------------
    def create_session(
        self,
        conversation_id: str,
        project_id: str,
        *,
        channel: str = "unknown",
        channel_connection_metadata: Mapping[str, str] | None = None,
        expires_at: str | None = None,
    ) -> ConversationContext:
        """Start a conversation and its session together.

        Separate from `get_context` because creation needs identity the frozen
        retrieval signature does not carry (D-2). `expires_at` is stored exactly
        as given and is never computed (D-4).
        """
        existing = self._read(conversation_id)
        if existing is not None:
            raise SessionAlreadyExistsError(
                conversation_id, existing.context.project_id
            )

        now = self._clock()
        context = ConversationContext(
            conversation_id=conversation_id,
            project_id=project_id,
            channel=channel,
            turns=(),
            started_at=now,
            last_active_at=now,
        )
        state = SessionState(
            session_id=self._new_session_id(),
            conversation_id=conversation_id,
            status=SessionStatus.ACTIVE,
            channel_connection_metadata=channel_connection_metadata or {},
            created_at=now,
            expires_at=expires_at,
        )
        self._write(conversation_id, SessionRecord(context=context, state=state))
        return context

    # -- §12.6 public interface ----------------------------------------------
    def get_context(self, conversation_id: str) -> ConversationContext:
        """The live conversation. Retrieve-only (D-2).

        Raises rather than returning an empty conversation for an unknown id:
        an empty history is indistinguishable from a lost one, and the caller
        would assemble a prompt with no context and never know.
        """
        record = self._require(conversation_id)
        if record.state.is_expired:
            raise SessionExpiredError(conversation_id)
        return record.context

    def append_turn(self, conversation_id: str, turn: Turn) -> ConversationContext:
        """Append exactly one turn (D-1) and return the updated conversation.

        The Runtime Engine calls this before the provider call with the user's
        turn, and again afterwards with the response. Appending the user turn
        first is what makes `latest_user_message` and the Budget Manager's
        history window correct, and it is what preserves the user's message when
        the provider call fails.

        Past turns are never touched: the new conversation is built by appending
        to the existing tuple, so §12.10's "never reordered or mutated" holds by
        construction rather than by discipline.
        """
        record = self._require(conversation_id)
        if record.state.is_expired:
            raise SessionExpiredError(conversation_id)

        self._assert_chronological(conversation_id, record.context.turns, turn)

        now = self._clock()
        context = ConversationContext(
            conversation_id=record.context.conversation_id,
            project_id=record.context.project_id,
            channel=record.context.channel,
            turns=(*record.context.turns, turn),
            started_at=record.context.started_at,
            last_active_at=now,
        )
        self._write(
            conversation_id, SessionRecord(context=context, state=record.state)
        )
        return context

    def expire(self, conversation_id: str) -> SessionState:
        """End the session. The conversation is retained for audit (D-3).

        Idempotent: expiring an already-expired session returns its state
        unchanged rather than failing, because the caller's intent is already
        satisfied and an error would invite a swallow-and-continue.
        """
        record = self._require(conversation_id)
        if record.state.is_expired:
            return record.state

        state = record.state.with_status(SessionStatus.EXPIRED)
        # The context is written through untouched: expiry ends the session,
        # never the record Compliance requires be kept.
        self._write(
            conversation_id, SessionRecord(context=record.context, state=state)
        )
        return state

    # -- audit and inspection -------------------------------------------------
    def archived_context(self, conversation_id: str) -> ConversationContext:
        """The conversation regardless of session status (§12.12d).

        The audit path. `get_context` refuses an expired session; this does not,
        because the whole point of expiring rather than deleting is that the
        history remains available for review.
        """
        return self._require(conversation_id).context

    def get_session(self, conversation_id: str) -> SessionState:
        """The technical session state, whatever its status."""
        return self._require(conversation_id).state

    def exists(self, conversation_id: str) -> bool:
        return self._read(conversation_id) is not None

    def conversation_ids(self) -> tuple[str, ...]:
        """Every stored conversation, expired included. For audit enumeration."""
        try:
            return self._store.conversation_ids()
        except Exception as exc:  # noqa: BLE001 - §12.9: fail clearly
            raise SessionStoreUnavailableError("conversation_ids", exc) from exc

    # -- internals ------------------------------------------------------------
    def _read(self, conversation_id: str) -> SessionRecord | None:
        try:
            return self._store.get(conversation_id)
        except Exception as exc:  # noqa: BLE001 - §12.9: never silently lose history
            raise SessionStoreUnavailableError("get", exc) from exc

    def _write(self, conversation_id: str, record: SessionRecord) -> None:
        try:
            self._store.put(conversation_id, record)
        except Exception as exc:  # noqa: BLE001 - §12.9: never silently lose history
            raise SessionStoreUnavailableError("put", exc) from exc

    def _require(self, conversation_id: str) -> SessionRecord:
        record = self._read(conversation_id)
        if record is None:
            raise SessionNotFoundError(conversation_id)
        return record

    @staticmethod
    def _assert_chronological(
        conversation_id: str, existing: tuple[Turn, ...], incoming: Turn
    ) -> None:
        """§12.10: strict chronological order, enforced rather than repaired.

        Only comparable when both turns carry a timestamp — `Turn.timestamp` is
        optional, and a turn without one cannot be shown to be out of order.
        Position already guarantees append-only ordering; this catches a caller
        replaying an older turn into a live conversation.
        """
        if incoming.timestamp is None:
            return
        for previous in reversed(existing):
            if previous.timestamp is None:
                continue
            if incoming.timestamp < previous.timestamp:
                raise OutOfOrderTurnError(
                    conversation_id, previous.timestamp, incoming.timestamp
                )
            return
