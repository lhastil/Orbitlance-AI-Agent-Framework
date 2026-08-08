"""Which Core file supplies which prompt slot.

Every entry is transcribed from `docs/runtime-specification.md` §4's assembly
order read against the actual contents of `core/prompts/` — not invented. Like
`runtime/validation/framework_spec.py`, this is a transcription that
[ADR 0002](../../docs/adr/0002-framework-constants-are-transcribed.md) expects
the Core Loader to eventually own. It cannot be derived: `CoreBundle.prompts` is
keyed by filename, and nothing in the data tells the runtime which file is
"Mission" or which files the order deliberately omits.

**Deliberately absent: `04`, `05`, `06`, `07` and `08`.**

* `04_discovery_engine.md`, `05_recommendation_engine.md` and
  `07_consultation_request.md` are carried by their workflow counterparts, which
  reach the prompt through the Workflow slot.
* `06_lead_qualification.md` is **not assembled**. The frozen order does not
  name it and the `CoreBundle` data-model row independently names the same six
  prompt modules. Its behaviour is delivered distributively — Fallback
  Responses, Escalation, Conversation Rules, and each workflow's Prerequisites
  and Decision Points. See **PA-3** in `docs/known-issues-runtime.md`. Do not
  add a slot for it without a decision from the system owner.
* `08_guardrails.md` is a **marker, not content**. It self-describes as the
  *"Guardrails (Prompt Injection Point)"* that *"marks where the rules defined
  in `core/guardrails/` (Safety, Escalation, Compliance) are injected"*.
  Rendering it would emit a signpost instead of the rules, and rendering both
  would duplicate the slot. The Guardrails slot renders `core/guardrails/` only.
"""

from __future__ import annotations

from typing import Final

from runtime.models.prompt_bundle import PromptSlot

#: Slot -> `core/prompts/` filename, for the five slots sourced from prompts.
#: Source: docs/runtime-specification.md §4 row 2.
CORE_PROMPT_FILES: Final[dict[PromptSlot, str]] = {
    PromptSlot.CORE_PERSONALITY: "01_core_personality.md",
    PromptSlot.MISSION: "02_mission.md",
    PromptSlot.CONVERSATION_RULES: "03_conversation_rules.md",
    PromptSlot.FALLBACK_RESPONSES: "09_fallback_responses.md",
    PromptSlot.TOOL_INSTRUCTIONS: "10_tool_instructions.md",
}

#: The guardrails bundle is atomic — Safety + Escalation + Compliance, always
#: together. Source: the `CoreBundle` data-model row, "guardrailsBundle (atomic
#: Safety+Escalation+Compliance)", and known-issues.md #2's resolution.
GUARDRAIL_FILES: Final[tuple[str, ...]] = (
    "safety.md",
    "escalation.md",
    "compliance.md",
)

#: Never rendered. See the module docstring.
GUARDRAIL_MARKER_PROMPT: Final[str] = "08_guardrails.md"

#: Prompt modules the frozen assembly order deliberately omits.
UNASSEMBLED_PROMPTS: Final[frozenset[str]] = frozenset(
    {
        "04_discovery_engine.md",
        "05_recommendation_engine.md",
        "06_lead_qualification.md",
        "07_consultation_request.md",
        GUARDRAIL_MARKER_PROMPT,
    }
)

#: Emitted only when `ResolvedContext.knowledge_incomplete` is true, per spec
#: rule 9: the bundle must be minimal and honest, and the agent must explain
#: that it is not fully configured. This is fixed framework text, never business
#: content — the assembler still invents nothing about the client.
DEGRADED_NOTICE: Final[str] = (
    "This assistant is not fully configured yet. Its business knowledge base is "
    "incomplete, so it cannot answer questions about services, pricing, "
    "availability, or any other business specifics.\n\n"
    "Say so plainly and politely if asked. Do not guess, estimate, infer, or "
    "fill the gap from general knowledge. Offer to hand the conversation to a "
    "human instead."
)

#: The slots the degraded bundle carries, in assembly order. Mission, Tool
#: Instructions, Branding, Knowledge and Workflow are omitted: there is no
#: configured business to pursue, no tools that should be invoked, no project
#: styling to apply, and no Knowledge to render.
DEGRADED_SLOTS: Final[tuple[PromptSlot, ...]] = (
    PromptSlot.CORE_PERSONALITY,
    PromptSlot.CONVERSATION_RULES,
    PromptSlot.GUARDRAILS,
    PromptSlot.FALLBACK_RESPONSES,
    PromptSlot.DEGRADED_NOTICE,
)
