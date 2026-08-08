"""Prompt Assembler tests.

Covers the four scenarios the frozen spec names for this module, the exact
assembly order, and the invariants the module claims: no playbook content, the
guardrails marker never rendered, 06 never assembled, purity and determinism.
"""

from __future__ import annotations

import dataclasses

import pytest

from runtime.assembler import (
    ASSEMBLY_ORDER,
    PlaybookLeakError,
    PromptAssembler,
    PromptSlot,
    UnknownWorkflowError,
)
from runtime.assembler import core_slots as slots
from runtime.models.conversation import (
    ConversationContext,
    Turn,
    TurnRole,
    WorkflowState,
)
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectDocument
from runtime.models.prompt_bundle import PromptSection
from runtime.models.resolved_context import ResolvedConfig, ResolvedContext

WORKFLOWS = ("consultation", "crm_sync", "discovery", "follow_up", "recommendation", "voice_agent")
KNOWLEDGE = ("01_company.md", "02_services.md", "06_pricing.md")


def doc(name: str, text: str | None = None) -> ProjectDocument:
    return ProjectDocument(
        name=name, relative_path=name, exists=True, raw_text=text or f"[{name} body]"
    )


def core_bundle(**overrides) -> CoreBundle:
    defaults = {
        "prompts": {
            n: doc(n)
            for n in (
                "01_core_personality.md",
                "02_mission.md",
                "03_conversation_rules.md",
                "04_discovery_engine.md",
                "05_recommendation_engine.md",
                "06_lead_qualification.md",
                "07_consultation_request.md",
                "08_guardrails.md",
                "09_fallback_responses.md",
                "10_tool_instructions.md",
            )
        },
        "guardrails": {n: doc(n) for n in ("safety.md", "escalation.md", "compliance.md")},
        "workflows": {f"{n}.md": doc(f"{n}.md") for n in WORKFLOWS},
    }
    return CoreBundle(**{**defaults, **overrides})


def resolved(
    *,
    knowledge: dict[str, ProjectDocument] | None = None,
    branding: dict[str, ProjectDocument] | None = None,
    incomplete: bool = False,
    enabled: tuple[str, ...] = WORKFLOWS,
) -> ResolvedContext:
    return ResolvedContext(
        project_id="example_client",
        knowledge={n: doc(n) for n in KNOWLEDGE} if knowledge is None else knowledge,
        branding=branding or {},
        config=ResolvedConfig(enabled_workflows=enabled),
        knowledge_incomplete=incomplete,
    )


def conversation(turns: tuple[Turn, ...] | None = None) -> ConversationContext:
    if turns is None:
        turns = (
            Turn(TurnRole.USER, "hello"),
            Turn(TurnRole.AGENT, "hi there"),
            Turn(TurnRole.USER, "what do you offer?"),
        )
    return ConversationContext(
        conversation_id="conv-1", project_id="example_client", channel="web", turns=turns
    )


def state(active: str | None = "discovery") -> WorkflowState:
    return WorkflowState(conversation_id="conv-1", active_workflow=active)


def assemble(core=None, ctx=None, st=None, conv=None, **kwargs):
    return PromptAssembler(core or core_bundle(), **kwargs).assemble(
        ctx if ctx is not None else resolved(),
        st if st is not None else state(),
        conv or conversation(),
    )


# --- spec scenario (a): fully-resolved context ------------------------------
def test_assembles_every_slot_for_a_fully_resolved_context() -> None:
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}))

    assert bundle.slots == ASSEMBLY_ORDER
    assert bundle.project_id == "example_client"
    assert bundle.conversation_id == "conv-1"
    assert not bundle.degraded


def test_slot_order_is_exactly_the_frozen_order() -> None:
    """Core Personality -> Mission -> Conversation Rules -> Guardrails ->
    Fallback Responses -> Tool Instructions -> Branding -> Knowledge -> Workflow."""
    assert ASSEMBLY_ORDER == (
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
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}))
    assert [s.slot for s in bundle.static_sections] == list(ASSEMBLY_ORDER)


def test_guardrails_precede_every_project_supplied_slot() -> None:
    """Core policy must be stated before branding, knowledge or workflow text."""
    order = list(ASSEMBLY_ORDER)
    guardrails = order.index(PromptSlot.GUARDRAILS)
    for later in (PromptSlot.BRANDING, PromptSlot.KNOWLEDGE, PromptSlot.WORKFLOW):
        assert guardrails < order.index(later)


def test_latest_message_and_history_are_carried_unedited() -> None:
    bundle = assemble()
    assert bundle.latest_message == "what do you offer?"
    assert [t.content for t in bundle.conversation_history_window] == ["hello", "hi there"]


# --- spec scenario (b): no playbook content ---------------------------------
def test_no_section_is_sourced_from_a_playbook() -> None:
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}))
    for section in bundle.static_sections:
        assert not section.is_from_playbook
        assert "industry_playbooks" not in section.source


def test_playbook_sourced_section_raises() -> None:
    """The rule-10 assertion is hard, not advisory."""
    leaked = PromptSection(
        slot=PromptSlot.KNOWLEDGE,
        source="core/industry_playbooks/healthcare.md",
        content="playbook body",
    )
    with pytest.raises(PlaybookLeakError):
        PromptAssembler._assert_no_playbook_content((leaked,))


def test_content_that_merely_mentions_playbooks_is_allowed() -> None:
    """Provenance, not substring.

    core/guardrails/safety.md, compliance.md and escalation.md all defer
    industry specifics to Playbooks, and discovery.md/recommendation.md state
    that playbooks never load at runtime. A text search would reject these
    valid bundles.
    """
    core = core_bundle(
        guardrails={
            "safety.md": doc(
                "safety.md",
                "Industry-specific safety requirements should be implemented "
                "within the appropriate Playbook.",
            )
        }
    )
    bundle = assemble(core=core)
    guardrails = bundle.section(PromptSlot.GUARDRAILS)
    assert guardrails is not None and "Playbook" in guardrails.content


def test_active_playbooks_are_never_rendered() -> None:
    ctx = dataclasses.replace(
        resolved(),
        config=ResolvedConfig(
            enabled_workflows=WORKFLOWS,
            active_playbooks=("core/industry_playbooks/healthcare.md",),
        ),
    )
    bundle = assemble(ctx=ctx)
    for section in bundle.static_sections:
        assert "healthcare" not in section.content
        assert "industry_playbooks" not in section.content


# --- spec scenario (c): degraded bundle -------------------------------------
def test_knowledge_incomplete_produces_the_honest_degraded_bundle() -> None:
    bundle = assemble(ctx=resolved(incomplete=True))

    assert bundle.degraded
    assert bundle.slots == slots.DEGRADED_SLOTS
    notice = bundle.section(PromptSlot.DEGRADED_NOTICE)
    assert notice is not None and "not fully configured" in notice.content


def test_degraded_bundle_carries_no_knowledge_branding_or_workflow() -> None:
    bundle = assemble(
        ctx=resolved(incomplete=True, branding={"brand.md": doc("brand.md")})
    )
    for absent in (
        PromptSlot.KNOWLEDGE,
        PromptSlot.BRANDING,
        PromptSlot.WORKFLOW,
        PromptSlot.TOOL_INSTRUCTIONS,
        PromptSlot.MISSION,
    ):
        assert bundle.section(absent) is None


def test_degraded_bundle_keeps_guardrails_and_fallback_responses() -> None:
    """Minimal, but never unsafe."""
    bundle = assemble(ctx=resolved(incomplete=True))
    assert bundle.section(PromptSlot.GUARDRAILS) is not None
    assert bundle.section(PromptSlot.FALLBACK_RESPONSES) is not None


def test_degraded_bundle_invents_no_business_content() -> None:
    bundle = assemble(ctx=resolved(incomplete=True))
    combined = " ".join(s.content for s in bundle.static_sections)
    for knowledge_doc in KNOWLEDGE:
        assert knowledge_doc not in combined


# --- spec scenario (d): only the active workflow is expanded ----------------
def test_only_the_active_workflow_is_expanded_others_are_indexed() -> None:
    bundle = assemble(st=state("discovery"))
    workflow = bundle.section(PromptSlot.WORKFLOW)
    assert workflow is not None

    assert "[discovery.md body]" in workflow.content
    for other in WORKFLOWS:
        if other != "discovery":
            assert f"[{other}.md body]" not in workflow.content, "inactive workflow expanded"
            assert other in workflow.content, "inactive workflow missing from the index"


def test_workflow_index_lists_only_enabled_workflows() -> None:
    bundle = assemble(ctx=resolved(enabled=("discovery", "consultation")), st=state("discovery"))
    workflow = bundle.section(PromptSlot.WORKFLOW)
    assert workflow is not None
    assert "consultation" in workflow.content
    assert "voice_agent" not in workflow.content


def test_unknown_active_workflow_raises_rather_than_omitting() -> None:
    with pytest.raises(UnknownWorkflowError):
        assemble(st=state("not_a_workflow"))


def test_no_active_workflow_omits_the_slot() -> None:
    bundle = assemble(st=state(None))
    assert bundle.section(PromptSlot.WORKFLOW) is None


# --- branding -----------------------------------------------------------------
def test_empty_branding_omits_the_overlay_without_substituting_core_personality() -> None:
    """R3-3: empty means Core's default voice already applies, via slot 1."""
    bundle = assemble(ctx=resolved(branding={}))

    assert bundle.section(PromptSlot.BRANDING) is None
    personality = bundle.section(PromptSlot.CORE_PERSONALITY)
    assert personality is not None
    assert (
        sum(1 for s in bundle.static_sections if s.content == personality.content) == 1
    ), "Core Personality must appear exactly once"


def test_supplied_branding_is_rendered_in_its_own_slot() -> None:
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md", "Warm and clear.")}))
    branding = bundle.section(PromptSlot.BRANDING)
    assert branding is not None and branding.content == "Warm and clear."


# --- the guardrails marker and the unassembled prompt modules -----------------
def test_guardrails_slot_renders_core_guardrails_not_the_marker_prompt() -> None:
    bundle = assemble()
    guardrails = bundle.section(PromptSlot.GUARDRAILS)
    assert guardrails is not None
    assert "[08_guardrails.md body]" not in guardrails.content
    for expected in ("safety.md", "escalation.md", "compliance.md"):
        assert f"[{expected} body]" in guardrails.content


@pytest.mark.parametrize("filename", sorted(slots.UNASSEMBLED_PROMPTS))
def test_deliberately_unassembled_prompts_never_reach_the_bundle(filename) -> None:
    """PA-3: 06 is not assembled; 04/05/07 arrive via workflows; 08 is a marker."""
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}))
    combined = " ".join(s.content for s in bundle.static_sections)
    assert f"[{filename} body]" not in combined


def test_06_has_no_slot_in_the_assembly_order() -> None:
    assert "06_lead_qualification.md" not in slots.CORE_PROMPT_FILES.values()
    assert "06_lead_qualification.md" in slots.UNASSEMBLED_PROMPTS


# --- token budget port --------------------------------------------------------
def test_absent_budget_includes_all_knowledge_phase_one_behaviour() -> None:
    bundle = assemble()
    knowledge = bundle.section(PromptSlot.KNOWLEDGE)
    assert knowledge is not None
    for name in KNOWLEDGE:
        assert f"[{name} body]" in knowledge.content


def test_injected_budget_restricts_knowledge_and_history() -> None:
    class Budget:
        def select_knowledge(self, context):  # noqa: ARG002
            return ("02_services.md",)

        def select_history(self, conversation):
            return conversation.turns[-1:]

    bundle = assemble(token_budget=Budget())
    knowledge = bundle.section(PromptSlot.KNOWLEDGE)
    assert knowledge is not None
    assert "[02_services.md body]" in knowledge.content
    assert "[01_company.md body]" not in knowledge.content
    assert len(bundle.conversation_history_window) == 1


def test_budget_naming_an_absent_document_does_not_invent_content() -> None:
    class Budget:
        def select_knowledge(self, context):  # noqa: ARG002
            return ("99_does_not_exist.md",)

        def select_history(self, conversation):
            return conversation.turns

    bundle = assemble(token_budget=Budget())
    assert bundle.section(PromptSlot.KNOWLEDGE) is None


# --- purity, determinism, immutability ----------------------------------------
def test_identical_inputs_produce_an_equal_bundle() -> None:
    core, ctx, st, conv = core_bundle(), resolved(), state(), conversation()
    a = PromptAssembler(core).assemble(ctx, st, conv)
    b = PromptAssembler(core).assemble(ctx, st, conv)
    assert a == b


def test_assembler_never_mutates_its_inputs() -> None:
    core, ctx, st, conv = core_bundle(), resolved(), state(), conversation()
    before = (tuple(core.prompts), tuple(ctx.knowledge), st, conv.turns)
    PromptAssembler(core).assemble(ctx, st, conv)
    assert (tuple(core.prompts), tuple(ctx.knowledge), st, conv.turns) == before


def test_bundle_is_immutable() -> None:
    bundle = assemble()
    with pytest.raises(dataclasses.FrozenInstanceError):
        bundle.latest_message = "mutated"  # type: ignore[misc]


# --- boundaries ----------------------------------------------------------------
def test_assembler_touches_no_forbidden_module_or_capability() -> None:
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "assembler"
    for path in root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in ("runtime.validation", "runtime.loader", "runtime.resolver"):
            assert forbidden not in source, f"{path.name} imports {forbidden}"
        for capability in ("open(", "pathlib", "re.compile", "os."):
            assert capability not in source, f"{path.name} uses {capability}"
