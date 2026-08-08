"""PromptBundle — the assembled, provider-agnostic prompt for one turn.

Implements the `PromptBundle` data model from docs/runtime-specification.md
(staticSections, conversationHistoryWindow, latestMessage). Written solely by
the Prompt Assembler and consumed immediately by the Provider Registry.

**Provider-agnostic by construction.** Spec rule 11 reserves provider-specific
shaping — role-separated versus flat string — for each Provider adapter. This
type therefore carries ordered sections and turns, never a rendered blob and
never a provider's role vocabulary.

`PromptSection.source` records where the text came from. That is what makes the
spec's rule-10 assertion checkable: the rule forbids any string *sourced from*
`core/industry_playbooks/`, which is a statement about provenance, not about
wording. A substring check would be wrong — `core/guardrails/safety.md`,
`compliance.md`, `escalation.md`, `discovery.md` and `recommendation.md` all
legitimately *mention* Industry Playbooks while containing none of their
content.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from runtime.models.conversation import Turn

#: Frozen: playbooks are reference-only and never load at runtime.
PLAYBOOK_DIRECTORY = "core/industry_playbooks/"


class PromptSlot(str, enum.Enum):
    """The assembly order, exactly as docs/runtime-specification.md §4 states it.

    > Core Personality -> Mission -> Conversation Rules -> Guardrails bundle ->
    > Fallback Responses -> Tool Instructions -> Branding overlay -> Knowledge
    > (per Token Budget Manager's selection) -> active Workflow's instructions
    > (others present only as an index).

    Declaration order is the assembly order and is asserted by tests. There is
    deliberately no slot for `core/prompts/04`, `05`, `06` or `07`: the frozen
    order names none of them, and the `CoreBundle` data-model row independently
    names the same six prompt modules. See PA-3 in docs/known-issues-runtime.md.

    `DEGRADED_NOTICE` is not a tenth slot in the normal order. It appears only
    in the degraded bundle spec rule 9 requires.
    """

    CORE_PERSONALITY = "core_personality"
    MISSION = "mission"
    CONVERSATION_RULES = "conversation_rules"
    GUARDRAILS = "guardrails"
    FALLBACK_RESPONSES = "fallback_responses"
    TOOL_INSTRUCTIONS = "tool_instructions"
    BRANDING = "branding"
    KNOWLEDGE = "knowledge"
    WORKFLOW = "workflow"
    DEGRADED_NOTICE = "degraded_notice"


#: The nine normal slots, in frozen order. Excludes DEGRADED_NOTICE.
ASSEMBLY_ORDER: tuple[PromptSlot, ...] = (
    PromptSlot.CORE_PERSONALITY,
    PromptSlot.MISSION,
    PromptSlot.CONVERSATION_RULES,
    PromptSlot.GUARDRAILS,
    PromptSlot.FALLBACK_RESPONSES,
    PromptSlot.TOOL_INSTRUCTIONS,
    PromptSlot.BRANDING,
    PromptSlot.KNOWLEDGE,
    PromptSlot.WORKFLOW,
)


@dataclass(frozen=True, slots=True)
class PromptSection:
    """One rendered slot, with the provenance of the text it carries."""

    slot: PromptSlot
    source: str
    content: str

    @property
    def is_from_playbook(self) -> bool:
        return self.source.replace("\\", "/").startswith(PLAYBOOK_DIRECTORY)


@dataclass(frozen=True, slots=True)
class PromptBundle:
    """What to send the LLM this turn. Ephemeral; discarded after the call."""

    project_id: str
    conversation_id: str
    static_sections: tuple[PromptSection, ...] = ()
    conversation_history_window: tuple[Turn, ...] = ()
    latest_message: str = ""
    degraded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "static_sections", tuple(self.static_sections))
        object.__setattr__(
            self, "conversation_history_window", tuple(self.conversation_history_window)
        )

    @property
    def slots(self) -> tuple[PromptSlot, ...]:
        return tuple(section.slot for section in self.static_sections)

    def section(self, slot: PromptSlot) -> PromptSection | None:
        for section in self.static_sections:
            if section.slot is slot:
                return section
        return None
