"""Session Manager failures.

§12.9 sets the policy: *"Persistence unavailable → fail clearly, never silently
lose history."* Every failure here is loud. None returns a partial or empty
conversation, because an empty history is indistinguishable from a real one that
was lost — and a prompt assembled from a silently truncated conversation would
answer the wrong question with full confidence.

§12.10 adds the audit rule: *"Turns append in strict chronological order; past
turns are never reordered or mutated."* `OutOfOrderTurnError` enforces it, and
it is a hard failure rather than a reordering, because quietly sorting a turn
into place would rewrite the record Compliance requires be accurate.
"""

from __future__ import annotations


class SessionError(Exception):
    """Base for every Session Manager failure."""


class SessionNotFoundError(SessionError):
    """No conversation with this id exists.

    Raised by the retrieve-only `get_context` rather than creating one. The
    frozen `getContext(conversation_id)` signature carries no `project_id` or
    `channel`, so a context created here would have to invent a project — and
    §12.3 forbids persisting across projects. Creation is `create_session`,
    which takes the identity it needs.
    """

    def __init__(self, conversation_id: str) -> None:
        super().__init__(
            f"No session exists for conversation {conversation_id!r}. "
            "get_context is retrieve-only; use create_session to start one."
        )
        self.conversation_id = conversation_id


class SessionExpiredError(SessionError):
    """The session expired, so its conversation is no longer retrievable.

    §12.12(d): expired sessions *"are no longer retrievable but remain in an
    audit archive … never simply deleted"*. The history is still stored and
    still reachable through `archived_context`; only the live retrieval path
    refuses. Deleting it would break the audit guarantee, and returning it
    normally would ignore the expiry.
    """

    def __init__(self, conversation_id: str) -> None:
        super().__init__(
            f"Session for conversation {conversation_id!r} has expired. Its "
            "history is retained for audit and is available via "
            "archived_context; it is not available for live use."
        )
        self.conversation_id = conversation_id


class SessionAlreadyExistsError(SessionError):
    """A conversation id was created twice.

    Silently returning the existing conversation would let a second project
    adopt an id another project already owns, which is exactly the cross-project
    bleed §12.3 forbids and §12.12(c) tests for.
    """

    def __init__(self, conversation_id: str, existing_project_id: str) -> None:
        super().__init__(
            f"Conversation {conversation_id!r} already exists and belongs to "
            f"project {existing_project_id!r}. Session ids are never reused "
            "across projects."
        )
        self.conversation_id = conversation_id
        self.existing_project_id = existing_project_id


class OutOfOrderTurnError(SessionError):
    """A turn was appended with a timestamp earlier than the turn before it.

    §12.10 requires strict chronological order. This fails rather than sorting:
    reordering would mutate the record, and a conversation whose turns are
    rearranged after the fact is not an audit trail.
    """

    def __init__(self, conversation_id: str, previous: str, incoming: str) -> None:
        super().__init__(
            f"Turn for conversation {conversation_id!r} is timestamped "
            f"{incoming!r}, which precedes the previous turn at {previous!r}. "
            "Turns append in strict chronological order and are never reordered."
        )
        self.conversation_id = conversation_id
        self.previous = previous
        self.incoming = incoming


class SessionStoreUnavailableError(SessionError):
    """The persistence store could not be reached.

    §12.9's clear failure. The original error is chained so the cause survives,
    and no conversation is returned in its place.
    """

    def __init__(self, operation: str, cause: Exception) -> None:
        super().__init__(
            f"The session store failed during {operation!r}: {cause}. "
            "No history is returned in its place."
        )
        self.operation = operation
        self.cause = cause
