"""The Runtime Engine's request and response types.

`RuntimeResponse` is §14.5's output — *"final response to the calling channel
adapter"* — and §14.6's return type. `RuntimeRequest` is §14.4's input.

**Both are framework-introduced, and that is worth stating precisely.** The
frozen Data Models table names neither type. What §14 *does* fix is their
content: §14.4 spells the input out as *"Incoming request (`project_id`,
`conversation_id`, message, channel)"*, and §14.6 names `RuntimeResponse` as the
return type without listing fields. So the four request fields are
authoritative and only the type name is introduced here; the response's shape
was ruled by the system owner and is deliberately minimal.

They live in `runtime/models/` beside every other model because the Runtime
Engine is not their only reader — a channel adapter, out of this specification's
scope, consumes `RuntimeResponse` and produces `RuntimeRequest`.

**`RuntimeResponse` carries no fallback text of its own.** When a turn is
blocked, escalated or degraded, `text` is empty and the flags say what happened.
Composing what a customer reads from `core/prompts/09_fallback_responses.md` is
not something this runtime can do yet — those responses are prose written for a
model to follow, and no mechanism selects one. Inventing a sentence here would
put user-facing wording in a module that owns none, and it would look
authoritative while resting on nothing. Recorded as RE-5.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeRequest:
    """One incoming request, as a channel adapter delivers it (§14.4).

    Exactly the four fields §14.4 names. Nothing is added: a fifth field here
    would be a claim about what channels supply, which this specification does
    not make.
    """

    project_id: str
    conversation_id: str
    message: str
    channel: str = "unknown"


@dataclass(frozen=True, slots=True)
class RuntimeResponse:
    """What the Runtime Engine returns for one turn (§14.5, §14.6).

    Four fields, ruled minimal:

    * `text` — what the agent produced, when a turn completed normally. Empty
      whenever the turn did not produce a deliverable answer.
    * `blocked` — a guardrail stopped this turn (§8.2). The customer must not
      receive `text`; there will not be any.
    * `escalate` — a human should take over (§8's escalation semantics).
    * `degraded` — the turn completed by a reduced path: an internal failure was
      contained (§14.9), or resolution reported degraded capabilities.

    `blocked` and `degraded` are independent. A guardrail block is a *working*
    runtime refusing to send something; a degraded turn is a runtime that could
    not complete normally. Collapsing them would make an outage indistinguishable
    from a safety decision in every audit record downstream.
    """

    text: str = ""
    blocked: bool = False
    escalate: bool = False
    degraded: bool = False

    def __post_init__(self) -> None:
        if self.blocked and self.text:
            raise ValueError(
                "a blocked RuntimeResponse must not carry text: the whole point "
                "of the block is that this content does not reach the customer"
            )

    @property
    def delivered(self) -> bool:
        """Whether this turn produced an answer the customer may be shown."""
        return not self.blocked
