"""Where workflow state is persisted.

§7.8 names a persistence store ("in-memory for a single-process MVP; a real
store for multi-instance scaling") and §7.11 records Redis/DB backing as the
extension point. Depending on a Protocol rather than a concrete store is what
makes that a later addition rather than a rewrite.

Modelled on `runtime.session.store.SessionStore` and, before it,
`runtime.loader.cache.ProjectCache` — one persistence idiom in the runtime
rather than three.

A store deals in **records only**: no validation, no locking, no lifecycle. In
particular it does **not** provide atomicity. §7.10 requires `commitTransition`
to be atomic per conversation, and that guarantee belongs to the Manager, which
is the only thing that knows what a transition is. A store that also tried to
enforce it would leave two places disagreeing about where the boundary lies —
and a future Redis store would have to reimplement the rule rather than inherit
it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.conversation import WorkflowState


@runtime_checkable
class WorkflowStateStore(Protocol):
    """Read/write access to stored workflow state."""

    def get(self, conversation_id: str) -> WorkflowState | None:
        """The stored state, or None when nothing is stored for that id."""
        ...

    def put(self, conversation_id: str, state: WorkflowState) -> None:
        """Store state, replacing any previous state for that id."""
        ...

    def conversation_ids(self) -> tuple[str, ...]:
        """Every stored id, in deterministic order."""
        ...


class InMemoryWorkflowStateStore:
    """Process-local storage — §7.8's single-process MVP.

    `WorkflowState` is a frozen dataclass holding only tuples, so a stored state
    cannot be mutated through the reference this hands back. Isolation between
    conversations is therefore structural: one conversation's state is a
    different immutable object, not a shared mutable one.
    """

    __slots__ = ("_states",)

    def __init__(self) -> None:
        self._states: dict[str, WorkflowState] = {}

    def get(self, conversation_id: str) -> WorkflowState | None:
        return self._states.get(conversation_id)

    def put(self, conversation_id: str, state: WorkflowState) -> None:
        self._states[conversation_id] = state

    def conversation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._states))

    def __len__(self) -> int:
        return len(self._states)
