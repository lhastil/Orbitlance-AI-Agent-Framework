"""Session Manager tests — specification §12.

All four §12.12 scenarios are covered and each is named in the test that covers
it. Beyond them, the four ratified decisions each have tests that prove the
*wrong* behaviour would be caught — particularly D-1, where a pair-append
interpretation silently makes the agent answer the previous question. That
defect is reproduced here against the real Modules 4 and 5 helpers, so the
reason for the decision is executable rather than a note in a docstring.
"""

from __future__ import annotations

import itertools

import pytest

from runtime.budget.manager import _history_turns
from runtime.models.conversation import ConversationContext, Turn, TurnRole
from runtime.models.session import SessionState, SessionStatus
from runtime.session import (
    InMemorySessionStore,
    OutOfOrderTurnError,
    SessionAlreadyExistsError,
    SessionError,
    SessionExpiredError,
    SessionManager,
    SessionNotFoundError,
    SessionRecord,
    SessionStore,
    SessionStoreUnavailableError,
)


@pytest.fixture
def clock():
    """Deterministic, strictly increasing ISO-8601 timestamps."""
    counter = itertools.count(1)
    return lambda: f"2026-01-01T00:00:{next(counter):02d}+00:00"


@pytest.fixture
def sessions(clock) -> SessionManager:
    ids = itertools.count(1)
    return SessionManager(
        InMemorySessionStore(),
        clock=clock,
        session_id_factory=lambda: f"session-{next(ids)}",
    )


def started(manager: SessionManager, conversation_id: str = "conv-1") -> str:
    manager.create_session(conversation_id, project_id="sunrise", channel="web")
    return conversation_id


# =============================================================================
# §12.12(a) — creates and retrieves a session correctly
# =============================================================================
def test_a_creates_and_retrieves_a_session(sessions: SessionManager) -> None:
    created = sessions.create_session("conv-1", project_id="sunrise", channel="web")
    assert created.conversation_id == "conv-1"
    assert created.project_id == "sunrise"
    assert created.channel == "web"
    assert created.turns == ()
    assert sessions.get_context("conv-1") == created


def test_creation_records_session_metadata(sessions: SessionManager) -> None:
    sessions.create_session("conv-1", project_id="sunrise", channel="voice")
    state = sessions.get_session("conv-1")
    assert isinstance(state, SessionState)
    assert state.conversation_id == "conv-1"
    assert state.session_id == "session-1"
    assert state.status is SessionStatus.ACTIVE
    assert state.created_at is not None


def test_creation_records_timestamps(sessions: SessionManager) -> None:
    context = sessions.create_session("conv-1", project_id="sunrise")
    assert context.started_at is not None
    assert context.last_active_at == context.started_at


def test_channel_connection_metadata_is_stored_read_only(
    sessions: SessionManager,
) -> None:
    sessions.create_session(
        "conv-1", project_id="sunrise", channel_connection_metadata={"ip": "10.0.0.1"}
    )
    metadata = sessions.get_session("conv-1").channel_connection_metadata
    assert metadata["ip"] == "10.0.0.1"
    with pytest.raises(TypeError):
        metadata["ip"] = "changed"  # type: ignore[index]


def test_retrieving_an_unknown_conversation_fails_loudly(
    sessions: SessionManager,
) -> None:
    """Never an empty conversation: that is indistinguishable from a lost one."""
    with pytest.raises(SessionNotFoundError, match="retrieve-only"):
        sessions.get_context("never-created")


def test_creating_the_same_conversation_twice_fails(sessions: SessionManager) -> None:
    started(sessions)
    with pytest.raises(SessionAlreadyExistsError, match="sunrise"):
        sessions.create_session("conv-1", project_id="other-project")


# =============================================================================
# §12.12(b) — appends turns in order
# =============================================================================
def test_b_appends_turns_in_order(sessions: SessionManager) -> None:
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "first"))
    sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "second"))
    context = sessions.append_turn("conv-1", Turn(TurnRole.USER, "third"))
    assert [t.content for t in context.turns] == ["first", "second", "third"]
    assert [t.role for t in context.turns] == [
        TurnRole.USER,
        TurnRole.AGENT,
        TurnRole.USER,
    ]


def test_appending_updates_last_active_but_not_started_at(
    sessions: SessionManager,
) -> None:
    created = sessions.create_session("conv-1", project_id="sunrise")
    updated = sessions.append_turn("conv-1", Turn(TurnRole.USER, "hello"))
    assert updated.started_at == created.started_at
    assert updated.last_active_at != created.last_active_at


def test_past_turns_are_never_mutated(sessions: SessionManager) -> None:
    """§12.10 audit integrity — held by construction, not by discipline."""
    started(sessions)
    first = sessions.append_turn("conv-1", Turn(TurnRole.USER, "original"))
    snapshot = first.turns
    sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "later"))
    assert snapshot == (Turn(TurnRole.USER, "original"),)
    assert sessions.get_context("conv-1").turns[0].content == "original"


def test_the_returned_context_is_a_new_object_each_time(
    sessions: SessionManager,
) -> None:
    started(sessions)
    first = sessions.get_context("conv-1")
    second = sessions.append_turn("conv-1", Turn(TurnRole.USER, "hi"))
    assert first is not second
    assert first.turns == ()


def test_out_of_order_timestamps_are_refused_not_reordered(
    sessions: SessionManager,
) -> None:
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "a", timestamp="2026-01-02"))
    with pytest.raises(OutOfOrderTurnError, match="never reordered"):
        sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "b", timestamp="2026-01-01"))
    assert [t.content for t in sessions.get_context("conv-1").turns] == ["a"]


def test_equal_timestamps_are_accepted(sessions: SessionManager) -> None:
    """Two turns in the same instant are ordered by position, not rejected."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "a", timestamp="2026-01-01"))
    context = sessions.append_turn(
        "conv-1", Turn(TurnRole.AGENT, "b", timestamp="2026-01-01")
    )
    assert len(context.turns) == 2


def test_turns_without_timestamps_are_accepted(sessions: SessionManager) -> None:
    """`Turn.timestamp` is optional; absence cannot prove disorder."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "a"))
    context = sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "b"))
    assert len(context.turns) == 2


def test_appending_to_an_unknown_conversation_fails(sessions: SessionManager) -> None:
    with pytest.raises(SessionNotFoundError):
        sessions.append_turn("nope", Turn(TurnRole.USER, "hi"))


# =============================================================================
# §12.12(c) — two conversations never share data
# =============================================================================
def test_c_two_conversations_never_share_data(sessions: SessionManager) -> None:
    sessions.create_session("conv-a", project_id="sunrise")
    sessions.create_session("conv-b", project_id="orbitlance")
    sessions.append_turn("conv-a", Turn(TurnRole.USER, "SECRET-A"))
    sessions.append_turn("conv-b", Turn(TurnRole.USER, "SECRET-B"))

    a = sessions.get_context("conv-a")
    b = sessions.get_context("conv-b")
    assert [t.content for t in a.turns] == ["SECRET-A"]
    assert [t.content for t in b.turns] == ["SECRET-B"]
    assert a.project_id != b.project_id


def test_sessions_do_not_share_session_ids(sessions: SessionManager) -> None:
    sessions.create_session("conv-a", project_id="sunrise")
    sessions.create_session("conv-b", project_id="sunrise")
    assert sessions.get_session("conv-a").session_id != (
        sessions.get_session("conv-b").session_id
    )


def test_expiring_one_conversation_leaves_the_other_live(
    sessions: SessionManager,
) -> None:
    sessions.create_session("conv-a", project_id="sunrise")
    sessions.create_session("conv-b", project_id="sunrise")
    sessions.expire("conv-a")
    assert sessions.get_session("conv-b").is_active
    assert sessions.get_context("conv-b") is not None


def test_a_conversation_keeps_the_project_it_was_created_for(
    sessions: SessionManager,
) -> None:
    """§12.3: never persists across projects."""
    sessions.create_session("conv-1", project_id="sunrise")
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "hi"))
    assert sessions.get_context("conv-1").project_id == "sunrise"


# =============================================================================
# §12.12(d) / D-3 — expired sessions: unretrievable, archived, never deleted
# =============================================================================
def test_d_expired_sessions_are_no_longer_retrievable(
    sessions: SessionManager,
) -> None:
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "hello"))
    sessions.expire("conv-1")
    with pytest.raises(SessionExpiredError, match="archived_context"):
        sessions.get_context("conv-1")


def test_d_expired_history_remains_in_the_audit_archive(
    sessions: SessionManager,
) -> None:
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "AUDIT-ME"))
    sessions.expire("conv-1")
    archived = sessions.archived_context("conv-1")
    assert [t.content for t in archived.turns] == ["AUDIT-ME"]


def test_d_expiry_never_deletes_the_conversation(sessions: SessionManager) -> None:
    started(sessions)
    sessions.expire("conv-1")
    assert sessions.exists("conv-1")
    assert "conv-1" in sessions.conversation_ids()


def test_the_store_offers_no_way_to_delete() -> None:
    """Structural: §12.12(d) cannot be violated by forgetting a rule."""
    store = InMemorySessionStore()
    for forbidden in ("delete", "remove", "pop", "clear", "invalidate"):
        assert not hasattr(store, forbidden), f"store exposes {forbidden}"


def test_expiry_transitions_status_only(sessions: SessionManager) -> None:
    started(sessions)
    before = sessions.get_session("conv-1")
    state = sessions.expire("conv-1")
    assert state.status is SessionStatus.EXPIRED
    assert state.session_id == before.session_id
    assert state.created_at == before.created_at


def test_expiry_is_idempotent(sessions: SessionManager) -> None:
    started(sessions)
    first = sessions.expire("conv-1")
    assert sessions.expire("conv-1") == first


def test_appending_to_an_expired_session_is_refused(sessions: SessionManager) -> None:
    started(sessions)
    sessions.expire("conv-1")
    with pytest.raises(SessionExpiredError):
        sessions.append_turn("conv-1", Turn(TurnRole.USER, "too late"))


def test_expiring_an_unknown_conversation_fails(sessions: SessionManager) -> None:
    with pytest.raises(SessionNotFoundError):
        sessions.expire("nope")


# =============================================================================
# D-1 — single-turn append, and the defect it prevents
# =============================================================================
def test_d1_append_turn_takes_one_turn() -> None:
    import inspect

    params = list(inspect.signature(SessionManager.append_turn).parameters)
    assert params == ["self", "conversation_id", "turn"]


def test_d1_the_user_turn_can_be_recorded_before_the_provider_call(
    sessions: SessionManager,
) -> None:
    """The ordering Modules 4 and 5 require, and §12.9's history guarantee."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "PREVIOUS question"))
    sessions.append_turn("conv-1", Turn(TurnRole.AGENT, "previous answer"))
    context = sessions.append_turn("conv-1", Turn(TurnRole.USER, "CURRENT question"))

    assert context.latest_user_message == "CURRENT question"
    assert [t.content for t in _history_turns(context)] == [
        "PREVIOUS question",
        "previous answer",
    ]


def test_d1_the_pair_append_interpretation_would_answer_the_wrong_question() -> None:
    """The defect the audit found, reproduced against the real Module 5 helper.

    If `append_turn` recorded a user+response pair only after the provider call,
    the incoming message would be absent at assembly time. This asserts that
    outcome explicitly so the reason for D-1 stays visible: it is not a style
    preference, it is a correctness requirement.
    """
    without_current = ConversationContext(
        conversation_id="conv-1",
        project_id="sunrise",
        turns=(
            Turn(TurnRole.USER, "PREVIOUS question"),
            Turn(TurnRole.AGENT, "previous answer"),
        ),
    )
    assert without_current.latest_user_message == "PREVIOUS question"
    assert [t.content for t in _history_turns(without_current)] == ["previous answer"]


def test_d1_a_user_turn_survives_a_failed_provider_call(
    sessions: SessionManager,
) -> None:
    """§12.9: never silently lose history."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "asked before the failure"))
    # the provider call would raise here; nothing else is appended
    assert [t.content for t in sessions.get_context("conv-1").turns] == [
        "asked before the failure"
    ]


# =============================================================================
# D-2 — retrieve-only get_context
# =============================================================================
def test_d2_get_context_takes_only_a_conversation_id() -> None:
    import inspect

    params = list(inspect.signature(SessionManager.get_context).parameters)
    assert params == ["self", "conversation_id"]


def test_d2_get_context_never_creates(sessions: SessionManager) -> None:
    with pytest.raises(SessionNotFoundError):
        sessions.get_context("conv-1")
    assert not sessions.exists("conv-1")
    assert sessions.conversation_ids() == ()


def test_d2_creation_carries_the_identity_retrieval_lacks() -> None:
    import inspect

    params = inspect.signature(SessionManager.create_session).parameters
    assert "project_id" in params
    assert "channel" in params


# =============================================================================
# D-4 — no retention duration is invented
# =============================================================================
def test_d4_expires_at_is_none_unless_supplied(sessions: SessionManager) -> None:
    started(sessions)
    assert sessions.get_session("conv-1").expires_at is None


def test_d4_expiring_does_not_compute_an_expiry_time(sessions: SessionManager) -> None:
    started(sessions)
    assert sessions.expire("conv-1").expires_at is None


def test_d4_a_caller_supplied_expiry_is_preserved(sessions: SessionManager) -> None:
    sessions.create_session("conv-1", project_id="sunrise", expires_at="2027-01-01")
    assert sessions.get_session("conv-1").expires_at == "2027-01-01"
    assert sessions.expire("conv-1").expires_at == "2027-01-01"


def test_d4_no_duration_constant_exists_in_the_module() -> None:
    import pathlib

    package = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "session"
    for path in package.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for forbidden in ("timedelta", "TTL", "ttl_seconds", "days=", "hours="):
            assert forbidden not in src, f"{path.name} invents a retention duration"


def test_idle_is_never_entered_automatically(sessions: SessionManager) -> None:
    """The status exists because the frozen row names it; nothing triggers it."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "hi"))
    assert sessions.get_session("conv-1").status is SessionStatus.ACTIVE
    assert SessionStatus.IDLE.value == "idle"


# =============================================================================
# SessionState model
# =============================================================================
def test_session_state_carries_the_frozen_fields() -> None:
    assert set(SessionState.__dataclass_fields__) == {
        "session_id",
        "conversation_id",
        "status",
        "channel_connection_metadata",
        "created_at",
        "expires_at",
    }


def test_session_state_is_immutable() -> None:
    import dataclasses

    state = SessionState(session_id="s", conversation_id="c")
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.status = SessionStatus.EXPIRED  # type: ignore[misc]


def test_with_status_returns_a_copy_and_leaves_the_original() -> None:
    state = SessionState(session_id="s", conversation_id="c")
    expired = state.with_status(SessionStatus.EXPIRED)
    assert expired is not state
    assert state.status is SessionStatus.ACTIVE
    assert expired.status is SessionStatus.EXPIRED


def test_session_and_conversation_expire_independently(
    sessions: SessionManager,
) -> None:
    """The data-model row's central requirement."""
    started(sessions)
    sessions.append_turn("conv-1", Turn(TurnRole.USER, "kept"))
    sessions.expire("conv-1")
    assert sessions.get_session("conv-1").is_expired
    assert sessions.archived_context("conv-1").turns


# =============================================================================
# §12.8 / §12.9 — persistence port and clear failure
# =============================================================================
def test_the_store_protocol_is_structural() -> None:
    assert isinstance(InMemorySessionStore(), SessionStore)


def test_a_custom_store_can_be_injected(clock) -> None:
    class Recording(InMemorySessionStore):
        def __init__(self) -> None:
            super().__init__()
            self.writes = 0

        def put(self, conversation_id: str, record: SessionRecord) -> None:
            self.writes += 1
            super().put(conversation_id, record)

    store = Recording()
    manager = SessionManager(store, clock=clock)
    manager.create_session("conv-1", project_id="sunrise")
    manager.append_turn("conv-1", Turn(TurnRole.USER, "hi"))
    assert store.writes == 2


def test_the_default_store_is_in_memory() -> None:
    assert isinstance(SessionManager()._store, InMemorySessionStore)  # noqa: SLF001


@pytest.mark.parametrize("operation", ["get", "put"])
def test_a_store_failure_is_reported_clearly(clock, operation: str) -> None:
    """§12.9: fail clearly, never silently lose history."""

    class Broken(InMemorySessionStore):
        def get(self, conversation_id: str):
            if operation == "get":
                raise OSError("store offline")
            return super().get(conversation_id)

        def put(self, conversation_id: str, record: SessionRecord) -> None:
            if operation == "put":
                raise OSError("store offline")
            super().put(conversation_id, record)

    manager = SessionManager(Broken(), clock=clock)
    with pytest.raises(SessionStoreUnavailableError, match="No history is returned"):
        manager.create_session("conv-1", project_id="sunrise")


def test_a_store_failure_preserves_the_cause(clock) -> None:
    class Broken(InMemorySessionStore):
        def get(self, conversation_id: str):  # noqa: ARG002
            raise OSError("disk gone")

    manager = SessionManager(Broken(), clock=clock)
    with pytest.raises(SessionStoreUnavailableError) as caught:
        manager.get_context("conv-1")
    assert isinstance(caught.value.cause, OSError)
    assert caught.value.__cause__ is not None


def test_every_error_is_a_session_error() -> None:
    for error in (
        SessionNotFoundError,
        SessionExpiredError,
        SessionAlreadyExistsError,
        OutOfOrderTurnError,
        SessionStoreUnavailableError,
    ):
        assert issubclass(error, SessionError)


# =============================================================================
# §12.7 — a leaf module
# =============================================================================
def test_the_module_depends_on_no_other_runtime_module() -> None:
    """§12.7: "depends on nothing else in the runtime"."""
    import pathlib

    package = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "session"
    allowed = ("runtime.models", "runtime.session")
    for path in package.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("from runtime", "import runtime")):
                continue
            module = stripped.split()[1]
            assert module.startswith(allowed), f"{path.name} imports {module}"


def test_the_manager_never_touches_workflow_state() -> None:
    """§12.3: workflow logic is delegated entirely elsewhere.

    Checked against the parsed syntax tree, not the source text: the module
    docstring mentions `WorkflowState` deliberately, to record that the Prompt
    Assembler still needs one from the unbuilt Module 7. Naming the dependency
    is the opposite of taking it.
    """
    import ast
    import pathlib

    package = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "session"
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "WorkflowState", f"{path.name} uses WorkflowState"
            if isinstance(node, ast.Attribute):
                assert node.attr != "WorkflowState", f"{path.name} uses WorkflowState"
            if isinstance(node, ast.ImportFrom):
                names = {alias.name for alias in node.names}
                assert "WorkflowState" not in names, f"{path.name} imports WorkflowState"


def test_the_ratified_decisions_are_recorded_in_the_module() -> None:
    import pathlib

    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "runtime"
        / "session"
        / "manager.py"
    ).read_text(encoding="utf-8")
    for marker in ("D-1", "D-2", "D-3", "D-4"):
        assert marker in src
