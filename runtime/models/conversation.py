"""ConversationContext — raw conversational history and session metadata.

Implements the `ConversationContext` data model from docs/runtime-specification.md
(conversation_id, project_id, channel, turns (ordered), started_at,
last_active_at).

Ownership note: the spec names Session Manager as this model's sole writer.
That module does not exist yet, so the model lives in `runtime/models/` where
the Prompt Assembler, Guardrail Engine and Observability can depend on it
without depending on each other — the same arrangement `CoreBundle` and
`ProjectContext` already use.

Read-only throughout. The Prompt Assembler is a pure transformation and must
never mutate the conversation it renders.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TurnRole(str, enum.Enum):
    """Who produced a turn. Deliberately provider-agnostic.

    The Prompt Assembler emits a provider-agnostic intermediate structure per
    spec rule 11; mapping these onto a provider's role vocabulary belongs to
    each Provider adapter, not here.
    """

    USER = "user"
    AGENT = "agent"


@dataclass(frozen=True, slots=True)
class Turn:
    """One message in a conversation."""

    role: TurnRole
    content: str
    timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """One conversation, as the Session Manager records it."""

    conversation_id: str
    project_id: str
    channel: str = "unknown"
    turns: tuple[Turn, ...] = ()
    started_at: str | None = None
    last_active_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "turns", tuple(self.turns))

    @property
    def latest_user_message(self) -> str:
        """The most recent user turn, or empty when the conversation is new.

        The Prompt Assembler carries this as `PromptBundle.latest_message`; it
        never edits or summarises it.
        """
        for turn in reversed(self.turns):
            if turn.role is TurnRole.USER:
                return turn.content
        return ""

    @property
    def history(self) -> tuple[Turn, ...]:
        """Every turn except the trailing user message the bundle carries separately."""
        if not self.turns:
            return ()
        last = self.turns[-1]
        return self.turns[:-1] if last.role is TurnRole.USER else self.turns


@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Which workflow is active for a conversation, plus data collected so far.

    Implements the `WorkflowState` data model (conversation_id, active_workflow,
    collected_data, transition_history). Written solely by the Workflow State
    Manager; the Prompt Assembler reads it and never mutates it — spec rule 7
    names that dependency read-only explicitly.

    `active_workflow` holds a canonical Core workflow name (a `core/workflows/`
    stem, e.g. `discovery`), matching what the Resolver produces in
    `ResolvedConfig.enabled_workflows`.
    """

    conversation_id: str
    active_workflow: str | None = None
    collected_data: tuple[tuple[str, str], ...] = ()
    transition_history: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "collected_data", tuple(self.collected_data))
        object.__setattr__(self, "transition_history", tuple(self.transition_history))
