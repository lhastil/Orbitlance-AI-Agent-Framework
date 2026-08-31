"""Workflow State Manager failures.

§7.9 sets the policy, and it is unusually specific about *why*:

> Persistence store unavailable → the conversation cannot continue; surfaces a
> clear "please try again," never silently resets to a default state (a silent
> reset would look like the agent forgot the entire conversation — worse than an
> honest error).

So nothing here returns a fallback state. A `WorkflowState` with no active
workflow is a perfectly valid *new* conversation, which is exactly why it must
never be produced by a failure path: the caller could not tell the two apart,
and the agent would silently start over mid-conversation.
"""

from __future__ import annotations


class WorkflowStateError(Exception):
    """Base for every Workflow State Manager failure."""


class InvalidTransitionError(WorkflowStateError):
    """The decision does not name a usable workflow.

    Structural validation only. §7.3 forbids this module from deciding anything
    about workflows, and §7.7 makes it a leaf with no `CoreBundle`, so it cannot
    and must not check that the target exists in Core — §6.10 places that
    assertion on the Router. What it can check is that a target was supplied at
    all, which is a malformed decision rather than a routing judgement.
    """

    def __init__(self, conversation_id: str, reason: str) -> None:
        super().__init__(
            f"Transition for conversation {conversation_id!r} is invalid: "
            f"{reason}. The Workflow Router is responsible for naming a "
            "workflow that exists in CoreBundle."
        )
        self.conversation_id = conversation_id
        self.reason = reason


class WorkflowStateStoreUnavailableError(WorkflowStateError):
    """The persistence store could not be reached (§7.9).

    The underlying cause is preserved. No state is returned in its place — a
    default here would be indistinguishable from a conversation that has not
    started, which is precisely the silent reset §7.9 forbids.
    """

    def __init__(self, operation: str, cause: Exception) -> None:
        super().__init__(
            f"The workflow state store failed during {operation!r}: {cause}. "
            "The conversation cannot continue; no default state is substituted."
        )
        self.operation = operation
        self.cause = cause
