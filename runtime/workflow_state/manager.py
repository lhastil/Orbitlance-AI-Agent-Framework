"""Workflow State Manager — specification §7.

Owns persistence and lifecycle of `WorkflowState` per conversation. A leaf:
§7.7 makes it something the Workflow Router *calls*, depending on nothing
itself, and it does not import another runtime module.

**It decides nothing.** §7.3 is the sharpest constraint in this module's spec —
"never decides what the next state should be (only persists/commits what Router
hands it)". Every method here either reads or writes; none chooses a workflow,
merges data, or infers a transition.

---

## Ratified decisions

**D-1 — the decision carries `target_workflow` and `collected_data`, nothing
else.** The frozen spec names `WorkflowTransitionDecision` five times without a
data-model row, so the type was defined at the minimum the contract requires.
See `runtime.models.workflow`.

**D-2 — `collected_data` is persisted exactly as the decision supplies it.**
Not merged with what was already stored, not filtered, not normalised. Merging
would be this module deciding what the conversation now knows, which §7.3
forbids; the Router receives the current state (§6.4) and is the component in a
position to carry data forward. The only change made is representational — a
`Mapping` becomes the frozen model's tuple of pairs, preserving every key,
value and their order.

**D-3 — `transition_history` entries are `"previous->target"`.** Plain
strings, matching the frozen `tuple[str, ...]`; no timestamps, no richer
structure. Creating a conversation's initial state is not a transition and
records nothing (WR-4). `"None->target"` appears only for a manager built
without an initial workflow, whose first commit leaves no active workflow.

**D-4 — a new conversation starts in the initial workflow it is given (WR-4,
superseding the earlier `None` start).** The `WorkflowState` data-model row says
creation "defaults to Discovery". This module still chooses nothing: the value
is supplied at construction (`initial_workflow`), and `activate()` supplies the
Workflow Router's `FIRST_TURN_WORKFLOW`. Project scope is not checked here —
this module never sees `ResolvedContext` — and does not need to be: WR-3's
activation rule refuses any project that has not enabled the first-turn
workflow, and the Prompt Assembler refuses to render a workflow the project has
not enabled. A manager built without an initial workflow keeps the standalone
default: `active_workflow` is None until the Router commits a transition.
"""

from __future__ import annotations

import threading

from runtime.models.conversation import WorkflowState
from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_state.errors import (
    InvalidTransitionError,
    WorkflowStateStoreUnavailableError,
)
from runtime.workflow_state.store import (
    InMemoryWorkflowStateStore,
    WorkflowStateStore,
)

#: How a transition is recorded in `WorkflowState.transition_history` (D-3).
TRANSITION_ARROW = "->"

#: What a first transition records as its origin, when nothing was active (D-3).
#: Reached only by a manager built without an initial workflow.
NO_PREVIOUS_WORKFLOW = "None"


class WorkflowStateManager:
    """Persists and exposes `WorkflowState` per conversation (§7.6).

    `commitTransition` is atomic per conversation id, as §7.10 requires: the
    read-modify-write is performed under a per-conversation lock, so two
    concurrent commits for the same conversation cannot lose an update. Locks
    are per conversation rather than global so that traffic on one conversation
    never serialises another — the guarantee §7.10 asks for is per id, and a
    single global lock would buy nothing extra at the cost of throughput.
    """

    __slots__ = ("_initial_workflow", "_lock_registry", "_locks", "_store")

    def __init__(
        self,
        store: WorkflowStateStore | None = None,
        *,
        initial_workflow: str | None = None,
    ) -> None:
        self._store = store if store is not None else InMemoryWorkflowStateStore()
        # D-4: the workflow a new conversation starts in, supplied by the caller
        # (`activate()` passes the Router's FIRST_TURN_WORKFLOW). None keeps the
        # standalone default of no active workflow.
        self._initial_workflow = initial_workflow
        self._locks: dict[str, threading.Lock] = {}
        # Guards creation of the per-conversation locks themselves. Without it,
        # two threads first-touching the same conversation could each build a
        # lock and then "hold" different ones, which would look like locking
        # while providing none of it.
        self._lock_registry = threading.Lock()

    # -- §7.6 public interface ----------------------------------------------
    def get_state(self, conversation_id: str) -> WorkflowState:
        """The current state, creating a new one on first access.

        Creation here is the data-model row's "created on first message". The new
        state starts in the initial workflow supplied at construction, with an
        empty `transition_history` — starting is not a transition (D-3, D-4). It
        is not stored until the first commit. Without an initial workflow,
        `active_workflow` is None until the Router commits a transition.

        A store failure raises rather than returning that empty state — the two
        are indistinguishable to a caller, and §7.9 calls the silent reset
        "worse than an honest error".
        """
        with self._lock_for(conversation_id):
            return self._load_or_create(conversation_id)

    def commit_transition(
        self, conversation_id: str, decision: WorkflowTransitionDecision
    ) -> WorkflowState:
        """Commit the Router's decision and return the new state (§7.6).

        Atomic per conversation (§7.10): the whole read-modify-write happens
        under one lock, so a concurrent commit cannot read the state this call
        is about to replace.
        """
        self._assert_usable(conversation_id, decision)

        with self._lock_for(conversation_id):
            current = self._load_or_create(conversation_id)
            committed = WorkflowState(
                conversation_id=conversation_id,
                active_workflow=decision.target_workflow,
                # D-2: persisted exactly as supplied. Order is the decision's
                # own; sorting or merging would be this module editing it.
                collected_data=tuple(decision.collected_data.items()),
                transition_history=(
                    *current.transition_history,
                    self._transition_entry(
                        current.active_workflow, decision.target_workflow
                    ),
                ),
            )
            self._write(conversation_id, committed)
            return committed

    # -- inspection ----------------------------------------------------------
    def exists(self, conversation_id: str) -> bool:
        """Whether state has been stored, without creating any."""
        return self._read(conversation_id) is not None

    def conversation_ids(self) -> tuple[str, ...]:
        try:
            return self._store.conversation_ids()
        except Exception as exc:  # noqa: BLE001 - §7.9: fail clearly
            raise WorkflowStateStoreUnavailableError("conversation_ids", exc) from exc

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _transition_entry(previous: str | None, target: str) -> str:
        """D-3: `"previous->target"`, or `"None->target"` when nothing was active."""
        origin = previous if previous is not None else NO_PREVIOUS_WORKFLOW
        return f"{origin}{TRANSITION_ARROW}{target}"

    @staticmethod
    def _assert_usable(
        conversation_id: str, decision: WorkflowTransitionDecision
    ) -> None:
        """Structural validation only — never a routing judgement.

        Whether the named workflow exists in Core is §6.10's assertion, and this
        module has no `CoreBundle` to check it against (§7.7). What it refuses is
        a decision that names no workflow at all, which is malformed rather than
        wrong.
        """
        if not isinstance(decision, WorkflowTransitionDecision):
            raise InvalidTransitionError(
                conversation_id,
                f"expected a WorkflowTransitionDecision, got "
                f"{type(decision).__name__}",
            )
        if not decision.target_workflow or not decision.target_workflow.strip():
            raise InvalidTransitionError(
                conversation_id, "target_workflow is empty"
            )

    def _lock_for(self, conversation_id: str) -> threading.Lock:
        with self._lock_registry:
            lock = self._locks.get(conversation_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[conversation_id] = lock
            return lock

    def _load_or_create(self, conversation_id: str) -> WorkflowState:
        """Assumes the conversation's lock is held."""
        stored = self._read(conversation_id)
        if stored is not None:
            return stored
        # D-4: no workflow is chosen here — the initial workflow was supplied at
        # construction. Starting in it is not a transition, so the history stays
        # empty (D-3, WR-4).
        return WorkflowState(
            conversation_id=conversation_id,
            active_workflow=self._initial_workflow,
        )

    def _read(self, conversation_id: str) -> WorkflowState | None:
        try:
            return self._store.get(conversation_id)
        except Exception as exc:  # noqa: BLE001 - §7.9: never a silent reset
            raise WorkflowStateStoreUnavailableError("get", exc) from exc

    def _write(self, conversation_id: str, state: WorkflowState) -> None:
        try:
            self._store.put(conversation_id, state)
        except Exception as exc:  # noqa: BLE001 - §7.9: never a silent reset
            raise WorkflowStateStoreUnavailableError("put", exc) from exc
