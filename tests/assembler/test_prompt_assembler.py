"""Prompt Assembler tests.

Covers the four scenarios the frozen spec names for this module, the exact
assembly order, and the invariants the module claims: no playbook content, the
guardrails marker never rendered, 06 never assembled, purity and determinism.
"""

from __future__ import annotations

import dataclasses
import pathlib

import pytest

from runtime.assembler import (
    ASSEMBLY_ORDER,
    PlaybookLeakError,
    PromptAssembler,
    PromptSlot,
    UnknownWorkflowError,
)
from runtime.assembler import core_slots as slots
from runtime.loader import markdown
from runtime.models.budget import BudgetSelection
from runtime.models.conversation import (
    ConversationContext,
    Turn,
    TurnRole,
    WorkflowState,
)
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectDocument, Section
from runtime.models.prompt_bundle import PromptSection
from runtime.models.resolved_context import ResolvedConfig, ResolvedContext

WORKFLOWS = ("consultation", "crm_sync", "discovery", "follow_up", "recommendation", "voice_agent")
KNOWLEDGE = ("01_company.md", "02_services.md", "06_pricing.md")


def doc(name: str, text: str | None = None) -> ProjectDocument:
    """A document carrying the same lossless decomposition the Loader produces."""
    body = text if text is not None else f"[{name} body]"
    parsed = markdown.split_sections(body)
    return ProjectDocument(
        name=name,
        relative_path=name,
        exists=True,
        raw_text=body,
        sections=tuple(
            Section(i, ps.heading, ps.level, ps.body)
            for i, ps in enumerate(parsed.sections)
        ),
        preamble=parsed.preamble,
    )


def kdoc(name: str, *sections: tuple[str, str]) -> ProjectDocument:
    """A Knowledge document with explicit headings.

    Knowledge is rendered section-by-section from v1.5 onward, so a Knowledge
    fixture must carry headings exactly as a real project document does.
    Defaults to one section named after the document.
    """
    pairs = sections or ((f"{name} heading", f"[{name} body]"),)
    text = "\n\n".join(f"## {h}\n\n{b}" for h, b in pairs)
    return doc(name, text)


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
        knowledge={n: kdoc(n) for n in KNOWLEDGE} if knowledge is None else knowledge,
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
        sources=("core/industry_playbooks/healthcare.md",),
        content="playbook body",
    )
    with pytest.raises(PlaybookLeakError):
        PromptAssembler._assert_no_playbook_content((leaked,))


# --- PA-5 regression: multi-source provenance -------------------------------
def test_playbook_source_is_detected_in_any_position() -> None:
    """PA-5: a joined string plus startswith() inspected only the first path."""
    leaked = PromptSection(
        slot=PromptSlot.KNOWLEDGE,
        sources=(
            "projects/x/knowledge/a.md",
            "core/industry_playbooks/healthcare.md",
        ),
        content="...",
    )
    assert leaked.is_from_playbook, "a later source must not be ignored"
    with pytest.raises(PlaybookLeakError):
        PromptAssembler._assert_no_playbook_content((leaked,))


def test_source_property_still_renders_joined_provenance() -> None:
    section = PromptSection(
        slot=PromptSlot.KNOWLEDGE, sources=("a/b.md", "c/d.md"), content="x"
    )
    assert section.source == "a/b.md, c/d.md"
    assert not section.is_from_playbook


def test_sources_record_only_documents_actually_rendered() -> None:
    """PA-7: an empty document must not be listed as a source."""
    bundle = assemble(
        ctx=resolved(
            knowledge={
                "01_company.md": kdoc("01_company.md"),
                "02_services.md": ProjectDocument(
                    "02_services.md", "knowledge/02_services.md", exists=True, raw_text="  "
                ),
            }
        )
    )
    knowledge = bundle.section(PromptSlot.KNOWLEDGE)
    assert knowledge is not None
    assert len(knowledge.sources) == 1
    assert "02_services" not in knowledge.source


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
        def select(self, request):
            return BudgetSelection(
                knowledge_sections=(("02_services.md", 0),),
                history_window=request.conversation.turns[-1:],
            )

    bundle = assemble(token_budget=Budget())
    knowledge = bundle.section(PromptSlot.KNOWLEDGE)
    assert knowledge is not None
    assert "[02_services.md body]" in knowledge.content
    assert "[01_company.md body]" not in knowledge.content
    assert knowledge.sources == ("projects/example_client/02_services.md#0",)
    assert len(bundle.conversation_history_window) == 1


def test_budget_naming_an_absent_document_does_not_invent_content() -> None:
    class Budget:
        def select(self, request):
            return BudgetSelection(
                knowledge_sections=(("99_does_not_exist.md", 0), ("01_company.md", 99)),
                history_window=request.conversation.turns,
            )

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


# --- spec §12(b): known playbook string, against the real repository ---------
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAYBOOK_DIR = REPO_ROOT / "core" / "industry_playbooks"


def real_playbook_lines() -> list[tuple[str, str]]:
    """Distinctive prose lines taken verbatim from real playbook files.

    Long, non-heading lines only, so a match is genuine playbook content rather
    than an incidental word. Read from `core/` and never modified.
    """
    collected: list[tuple[str, str]] = []
    for path in sorted(PLAYBOOK_DIR.glob("*.md")):
        if path.stem.startswith("_"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if len(line) > 80 and not line.startswith(("#", "-", "|", "*", ">")):
                collected.append((path.name, line))
                break
    return collected


def real_core_bundle() -> CoreBundle:
    """A CoreBundle built from the real `core/` tree, playbooks excluded."""

    def group(sub: str) -> dict[str, ProjectDocument]:
        directory = REPO_ROOT / "core" / sub
        return {
            p.name: ProjectDocument(
                p.name, f"core/{sub}/{p.name}", True, p.read_text(encoding="utf-8")
            )
            for p in sorted(directory.glob("*.md"))
        }

    return CoreBundle(
        prompts=group("prompts"),
        guardrails=group("guardrails"),
        workflows=group("workflows"),
        playbook_names=frozenset(
            p.stem for p in PLAYBOOK_DIR.glob("*.md") if not p.stem.startswith("_")
        ),
    )


def test_real_playbook_fixture_material_exists() -> None:
    """Guards the fixture itself: a vacuous corpus would make §12(b) meaningless."""
    lines = real_playbook_lines()
    assert len(lines) >= 5, f"expected distinctive lines from each playbook, got {lines}"


@pytest.mark.parametrize(("playbook", "line"), real_playbook_lines())
def test_assembled_output_never_contains_a_known_playbook_string(playbook, line) -> None:
    """Spec §12(b), against real Core content and a real playbook fixture."""
    core = real_core_bundle()
    ctx = ResolvedContext(
        project_id="fixture_client",
        knowledge={"01_company.md": doc("01_company.md", "We sell widgets.")},
        branding={"brand.md": doc("brand.md", "Warm and precise.")},
        config=ResolvedConfig(enabled_workflows=WORKFLOWS),
        knowledge_incomplete=False,
    )
    bundle = PromptAssembler(core).assemble(
        ctx, state("consultation"), conversation()
    )
    combined = "\n".join(s.content for s in bundle.static_sections)
    assert line not in combined, f"{playbook} content leaked into the assembled prompt"


def test_degraded_bundle_also_contains_no_known_playbook_string() -> None:
    core = real_core_bundle()
    ctx = ResolvedContext(
        project_id="fixture_client", config=ResolvedConfig(), knowledge_incomplete=True
    )
    bundle = PromptAssembler(core).assemble(ctx, state(None), conversation())
    combined = "\n".join(s.content for s in bundle.static_sections)
    for _playbook, line in real_playbook_lines():
        assert line not in combined


def test_real_core_content_mentioning_playbooks_still_assembles() -> None:
    """Test 4: legitimate references must not be mistaken for leaked content.

    Real guardrails and workflows defer industry specifics to Playbooks by name.
    """
    core = real_core_bundle()
    ctx = ResolvedContext(
        project_id="fixture_client",
        knowledge={"01_company.md": doc("01_company.md", "We sell widgets.")},
        config=ResolvedConfig(enabled_workflows=WORKFLOWS),
        knowledge_incomplete=False,
    )
    bundle = PromptAssembler(core).assemble(ctx, state("discovery"), conversation())
    combined = "\n".join(s.content for s in bundle.static_sections)
    assert "Playbook" in combined, "expected legitimate references in real Core text"
    assert not any(s.is_from_playbook for s in bundle.static_sections)


# --- PA-6: the limit of what provenance can observe --------------------------
def test_playbook_document_misfiled_into_a_prompt_slot_is_detected() -> None:
    """PA-6, detectable half: a Loader that misfiles a playbook but records its
    true path is caught, because provenance now comes from the document."""
    playbook = PLAYBOOK_DIR / "healthcare.md"
    misfiled = ProjectDocument(
        "02_mission.md",
        "core/industry_playbooks/healthcare.md",
        True,
        playbook.read_text(encoding="utf-8"),
    )
    core = core_bundle(prompts={**core_bundle().prompts, "02_mission.md": misfiled})
    with pytest.raises(PlaybookLeakError):
        assemble(core=core)


def test_playbook_content_with_a_falsified_path_is_not_detectable() -> None:
    """PA-6, undetectable half — recorded honestly rather than hidden.

    If a document carries playbook text but a `relative_path` claiming to be a
    prompt, no information reaching the assembler distinguishes it from a
    genuine prompt: `CoreBundle` carries no content-origin metadata and no
    playbook text to compare against. The fixture test above is the enforcement
    boundary for this case, not the runtime assertion.
    """
    playbook = PLAYBOOK_DIR / "healthcare.md"
    falsified = ProjectDocument(
        "02_mission.md", "core/prompts/02_mission.md", True,
        playbook.read_text(encoding="utf-8"),
    )
    core = core_bundle(prompts={**core_bundle().prompts, "02_mission.md": falsified})
    bundle = assemble(core=core)  # does not raise -- documented limitation
    mission = bundle.section(PromptSlot.MISSION)
    assert mission is not None and not mission.is_from_playbook


# --- Test 5: partial CoreBundle ---------------------------------------------
def test_missing_core_prompt_omits_its_slot_without_crashing() -> None:
    prompts = {k: v for k, v in core_bundle().prompts.items() if k != "02_mission.md"}
    bundle = assemble(core=core_bundle(prompts=prompts))
    assert bundle.section(PromptSlot.MISSION) is None
    assert bundle.section(PromptSlot.CORE_PERSONALITY) is not None


def test_missing_guardrail_file_still_renders_the_remaining_bundle() -> None:
    core = core_bundle(guardrails={"safety.md": doc("safety.md")})
    guardrails = assemble(core=core).section(PromptSlot.GUARDRAILS)
    assert guardrails is not None
    assert guardrails.sources == ("core/guardrails/safety.md",)


def test_no_guardrails_at_all_omits_the_slot() -> None:
    bundle = assemble(core=core_bundle(guardrails={}))
    assert bundle.section(PromptSlot.GUARDRAILS) is None


# --- Module 4 v1.5: section-level Knowledge + render-and-count seam ----------
DUPES = (("Category", "Preventive"), ("Category", "Cosmetic"), ("CATEGORY", "Urgent"))


def budget_returning(refs, history=()):
    class Budget:
        def select(self, request):  # noqa: ARG002
            return BudgetSelection(knowledge_sections=refs, history_window=history)

    return Budget()


def test_single_section_is_rendered_with_its_original_heading() -> None:
    ctx = resolved(
        knowledge={"01_company.md": kdoc("01_company.md", ("Company Overview", "We sell widgets."))}
    )
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert k is not None
    assert k.content == "## Company Overview\n\nWe sell widgets."


def test_multiple_sections_render_in_selection_order() -> None:
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "first"), ("B", "second"))})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert k.content == "## A\n\nfirst\n\n## B\n\nsecond"


def test_duplicate_headings_stay_distinct_sections() -> None:
    ctx = resolved(knowledge={"02_services.md": kdoc("02_services.md", *DUPES)})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    for body in ("Preventive", "Cosmetic", "Urgent"):
        assert body in k.content, "every duplicate occurrence must survive"


def test_duplicate_normalised_headings_stay_distinct() -> None:
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("Category", "A"), ("CATEGORY", "B"))})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert "## Category\n\nA" in k.content
    assert "## CATEGORY\n\nB" in k.content, "capitalisation must not be normalised"


def test_ordinal_addressing_selects_the_right_occurrence() -> None:
    ctx = resolved(knowledge={"02_services.md": kdoc("02_services.md", *DUPES)})
    bundle = assemble(ctx=ctx, token_budget=budget_returning((("02_services.md", 1),)))
    k = bundle.section(PromptSlot.KNOWLEDGE)
    assert k.content == "## Category\n\nCosmetic", "ordinal 1, not the first Category"
    assert k.sources == ("projects/example_client/02_services.md#1",)


def test_heading_levels_are_preserved() -> None:
    ctx = resolved(knowledge={"d.md": doc("d.md", "# One\n\na\n\n### Three\n\nc")})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert "# One\n\na" in k.content and "### Three\n\nc" in k.content


def test_empty_section_renders_its_heading_only() -> None:
    ctx = resolved(knowledge={"d.md": doc("d.md", "## Empty\n\n## Full\n\nbody")})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert k.content == "## Empty\n\n## Full\n\nbody"


def test_all_knowledge_is_selected_when_no_budget_is_injected() -> None:
    """Phase 1 default: every section of every document."""
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "1"), ("B", "2"), ("C", "3"))})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert len(k.sources) == 3


def test_budget_raising_fail_closed_propagates() -> None:
    """Phase 1: full Knowledge or fail closed. The assembler must not absorb it."""

    class Failing:
        def select(self, request):  # noqa: ARG002
            raise RuntimeError("knowledge does not fit")

    with pytest.raises(RuntimeError, match="does not fit"):
        assemble(token_budget=Failing())


def test_unresolvable_reference_invents_nothing() -> None:
    bundle = assemble(token_budget=budget_returning((("nope.md", 0), ("01_company.md", 99))))
    assert bundle.section(PromptSlot.KNOWLEDGE) is None


def test_knowledge_never_falls_back_to_raw_text() -> None:
    """raw_text carries preamble the decomposition excludes; it must not appear."""
    ctx = resolved(knowledge={"d.md": doc("d.md", "PREAMBLE_MARKER\n\n## H\n\nbody")})
    k = assemble(ctx=ctx).section(PromptSlot.KNOWLEDGE)
    assert "PREAMBLE_MARKER" not in k.content, "raw_text must not be the render source"
    assert k.content == "## H\n\nbody"


# --- the render-and-count seam ----------------------------------------------
class Recorder:
    """Captures the request so tests can assert what Module 5 actually receives."""

    def __init__(self):
        self.request = None

    def select(self, request):
        self.request = request
        return BudgetSelection(
            knowledge_sections=tuple(c.ref for c in request.knowledge_candidates),
            history_window=request.conversation.history,
        )


def test_budget_receives_the_actual_rendered_fixed_text() -> None:
    rec = Recorder()
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}), token_budget=rec)

    assert rec.request is not None
    fixed = {s.slot for s in rec.request.fixed_sections}
    assert PromptSlot.KNOWLEDGE not in fixed, "Knowledge is the variable part"
    assert PromptSlot.WORKFLOW in fixed, "workflow must be rendered before selection"
    for section in rec.request.fixed_sections:
        rendered = bundle.section(section.slot)
        assert rendered is not None and rendered.content == section.content, (
            "the budget manager must see the exact text that ships"
        )


def test_workflow_index_sentence_is_inside_the_counted_fixed_text() -> None:
    rec = Recorder()
    assemble(ctx=resolved(enabled=("discovery", "consultation")), token_budget=rec)
    workflow = next(s for s in rec.request.fixed_sections if s.slot is PromptSlot.WORKFLOW)
    assert "Other workflows available" in workflow.content
    assert "consultation" in workflow.content


def test_rendering_changes_change_what_the_budget_counts() -> None:
    """Drift-proofing: alter rendered content, the counted text follows."""
    rec_a, rec_b = Recorder(), Recorder()
    assemble(token_budget=rec_a)
    altered = {**core_bundle().prompts, "02_mission.md": doc("02_mission.md", "A MUCH LONGER MISSION")}
    assemble(core=core_bundle(prompts=altered), token_budget=rec_b)
    a = "".join(rec_a.request.fixed_text)
    b = "".join(rec_b.request.fixed_text)
    assert a != b and "A MUCH LONGER MISSION" in b


def test_budget_receives_latest_message_and_conversation() -> None:
    rec = Recorder()
    assemble(token_budget=rec)
    assert rec.request.latest_message == "what do you offer?"
    assert rec.request.conversation is not None
    assert len(rec.request.conversation.turns) == 3


def test_history_window_comes_from_the_budget_selection() -> None:
    only_first = (Turn(TurnRole.USER, "hello"),)
    bundle = assemble(token_budget=budget_returning((), history=only_first))
    assert bundle.conversation_history_window == only_first


def test_latest_message_is_never_truncated_by_selection() -> None:
    bundle = assemble(token_budget=budget_returning((), history=()))
    assert bundle.latest_message == "what do you offer?"


def test_internal_build_order_does_not_change_output_order() -> None:
    """Workflow renders before Knowledge internally; output order is unchanged."""
    bundle = assemble(ctx=resolved(branding={"brand.md": doc("brand.md")}))
    assert [s.slot for s in bundle.static_sections] == list(ASSEMBLY_ORDER)


# --- architecture boundaries -------------------------------------------------
def test_assembler_has_no_tokenizer_dependency() -> None:
    root = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "assembler"
    for path in root.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for banned in ("tiktoken", "count_tokens", "Tokenizer"):
            assert banned not in src, f"{path.name} references {banned}"


def test_assembler_still_parses_no_markdown() -> None:
    root = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "assembler"
    for path in root.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        assert "split_sections" not in src
        assert "re.compile" not in src


def test_seam_types_avoid_a_module_five_import_cycle() -> None:
    """BudgetRequest/BudgetSelection live in models so Module 5 need not import Module 4."""
    from runtime.models import budget as budget_module

    src = pathlib.Path(budget_module.__file__).read_text(encoding="utf-8")
    assert "runtime.assembler" not in src


def test_repeated_assembly_is_deterministic_through_the_seam() -> None:
    core, ctx, st, conv = core_bundle(), resolved(), state(), conversation()
    a = PromptAssembler(core, token_budget=Recorder()).assemble(ctx, st, conv)
    b = PromptAssembler(core, token_budget=Recorder()).assemble(ctx, st, conv)
    assert a == b


# --- Module 4 v1.6: Knowledge crosses the seam already rendered --------------
def test_every_knowledge_section_arrives_as_a_rendered_candidate() -> None:
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    assemble(ctx=ctx, token_budget=rec)

    assert [c.ref for c in rec.request.knowledge_candidates] == [("d.md", 0), ("d.md", 1)]
    assert [c.rendered_text for c in rec.request.knowledge_candidates] == [
        "## A\n\none",
        "## B\n\ntwo",
    ]


def test_knowledge_text_is_exactly_what_ships() -> None:
    """v1.7: the seam delivers the composed slot, so no test supplies the join.

    The v1.6 version of this test joined the candidates with a literal "\\n\\n".
    That proved the candidates *could* reconstruct the slot if you already knew
    the separator — which is precisely the knowledge Module 5 is forbidden to
    have. The assertion now reads the composed string off the request.
    """
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    bundle = assemble(ctx=ctx, token_budget=rec)

    shipped = bundle.section(PromptSlot.KNOWLEDGE).content
    assert rec.request.knowledge_text == shipped


def test_selected_subset_still_matches_its_candidates_exactly() -> None:
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"), ("C", "three"))})
    rec = Recorder()
    assemble(ctx=ctx, token_budget=rec)
    chosen = rec.request.knowledge_candidates[1]

    bundle = assemble(ctx=ctx, token_budget=budget_returning((chosen.ref,)))
    assert bundle.section(PromptSlot.KNOWLEDGE).content == chosen.rendered_text


def test_candidates_preserve_duplicate_headings_distinctly() -> None:
    rec = Recorder()
    ctx = resolved(knowledge={"02_services.md": kdoc("02_services.md", *DUPES)})
    assemble(ctx=ctx, token_budget=rec)

    cands = rec.request.knowledge_candidates
    assert [c.ordinal for c in cands] == [0, 1, 2]
    assert len({c.rendered_text for c in cands}) == 3, "duplicates must not collapse"
    assert "## Category\n\nPreventive" in cands[0].rendered_text
    assert "## CATEGORY\n\nUrgent" in cands[2].rendered_text


def test_candidates_preserve_heading_levels() -> None:
    rec = Recorder()
    assemble(ctx=resolved(knowledge={"d.md": doc("d.md", "# One\n\na\n\n### Three\n\nc")}),
             token_budget=rec)
    assert [c.rendered_text for c in rec.request.knowledge_candidates] == [
        "# One\n\na",
        "### Three\n\nc",
    ]


def test_empty_section_candidate_carries_its_heading() -> None:
    rec = Recorder()
    assemble(ctx=resolved(knowledge={"d.md": doc("d.md", "## Empty\n\n## Full\n\nbody")}),
             token_budget=rec)
    assert [c.rendered_text for c in rec.request.knowledge_candidates] == [
        "## Empty",
        "## Full\n\nbody",
    ]


def test_candidates_span_multiple_documents_in_order() -> None:
    rec = Recorder()
    ctx = resolved(knowledge={"a.md": kdoc("a.md", ("A", "1")), "b.md": kdoc("b.md", ("B", "2"))})
    assemble(ctx=ctx, token_budget=rec)
    assert [c.ref for c in rec.request.knowledge_candidates] == [("a.md", 0), ("b.md", 0)]


def test_heading_format_change_propagates_into_the_candidates() -> None:
    """The regression the previous gap hid: rendering drift must reach budgeting."""
    rec_a, rec_b = Recorder(), Recorder()
    assemble(ctx=resolved(knowledge={"d.md": kdoc("d.md", ("Short", "x"))}), token_budget=rec_a)
    assemble(
        ctx=resolved(knowledge={"d.md": kdoc("d.md", ("A Very Much Longer Heading", "x"))}),
        token_budget=rec_b,
    )
    a = rec_a.request.knowledge_candidates[0].rendered_text
    b = rec_b.request.knowledge_candidates[0].rendered_text
    assert a != b and len(b) > len(a)
    assert "A Very Much Longer Heading" in b


def test_body_only_accounting_would_undercount() -> None:
    """Guards the specific defect: bodies alone are not the rendered cost."""
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("Heading One", "b"), ("Heading Two", "b"))})
    assemble(ctx=ctx, token_budget=rec)

    rendered = sum(len(c.rendered_text) for c in rec.request.knowledge_candidates)
    bodies = sum(len(s.body) for d in ctx.knowledge.values() for s in d.sections)
    assert rendered > bodies, "headings and separators are part of the real cost"


def test_request_exposes_no_project_documents() -> None:
    """Module 5 must not be able to reach raw_text, sections or section_body."""
    rec = Recorder()
    assemble(token_budget=rec)
    assert not hasattr(rec.request, "knowledge")
    for field in ("raw_text", "sections", "section_body", "preamble"):
        assert not hasattr(rec.request.knowledge_candidates[0], field)


def test_knowledge_is_rendered_exactly_once() -> None:
    """Candidates are reused when assembling; nothing is re-rendered."""
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    bundle = assemble(ctx=ctx, token_budget=rec)
    for candidate in rec.request.knowledge_candidates:
        assert candidate.rendered_text in bundle.section(PromptSlot.KNOWLEDGE).content


def test_candidate_identity_is_ordinal_not_heading() -> None:
    rec = Recorder()
    assemble(ctx=resolved(knowledge={"02_services.md": kdoc("02_services.md", *DUPES)}),
             token_budget=rec)
    refs = [c.ref for c in rec.request.knowledge_candidates]
    assert refs == [("02_services.md", 0), ("02_services.md", 1), ("02_services.md", 2)]
    assert len(set(refs)) == 3, "identity must stay unique despite repeated headings"


def test_seam_remains_free_of_module_four_imports() -> None:
    from runtime.models import budget as budget_module

    src = pathlib.Path(budget_module.__file__).read_text(encoding="utf-8")
    assert "runtime.assembler" not in src
    assert "import ProjectDocument" not in src, "candidates are opaque text plus identity"
    assert not hasattr(budget_module.BudgetRequest, "knowledge")


def test_candidates_are_deterministic_across_calls() -> None:
    ctx = resolved()
    a, b = Recorder(), Recorder()
    assemble(ctx=ctx, token_budget=a)
    assemble(ctx=ctx, token_budget=b)
    assert [c.ref for c in a.request.knowledge_candidates] == [
        c.ref for c in b.request.knowledge_candidates
    ]
    assert a.request.knowledge_text == b.request.knowledge_text
    assert isinstance(a.request.knowledge_text, str)


# --- Module 4 v1.7: the composed Knowledge slot crosses the seam -------------
def test_budget_request_carries_the_assembled_knowledge_text() -> None:
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    assemble(ctx=ctx, token_budget=rec)

    assert isinstance(rec.request.knowledge_text, str)
    assert rec.request.knowledge_text, "the composed slot must not be empty here"


def test_knowledge_text_exceeds_the_sum_of_its_candidates() -> None:
    """The v1.6 gap in one assertion: joins are real cost the sum omits."""
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"), ("C", "three"))})
    assemble(ctx=ctx, token_budget=rec)

    summed = sum(len(c.rendered_text) for c in rec.request.knowledge_candidates)
    assert len(rec.request.knowledge_text) > summed
    assert len(rec.request.knowledge_text) - summed == 2 * (
        len(rec.request.knowledge_candidates) - 1
    )


def test_module_five_can_count_one_opaque_string() -> None:
    """knowledge_text is countable directly; no candidate summation is needed."""
    rec = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    bundle = assemble(ctx=ctx, token_budget=rec)

    def count_tokens(text: str) -> int:
        return len(text.split())

    assert count_tokens(rec.request.knowledge_text) == count_tokens(
        bundle.section(PromptSlot.KNOWLEDGE).content
    )


def test_empty_knowledge_yields_empty_text_and_no_slot() -> None:
    rec = Recorder()
    bundle = assemble(ctx=resolved(knowledge={}), token_budget=rec)

    assert rec.request.knowledge_text == ""
    assert rec.request.knowledge_candidates == ()
    assert bundle.section(PromptSlot.KNOWLEDGE) is None, "nothing fabricated"


def test_knowledge_text_preserves_duplicate_occurrences() -> None:
    rec = Recorder()
    ctx = resolved(knowledge={"02_services.md": kdoc("02_services.md", *DUPES)})
    assemble(ctx=ctx, token_budget=rec)

    for body in ("Preventive", "Cosmetic", "Urgent"):
        assert body in rec.request.knowledge_text
    assert rec.request.knowledge_text.count("Category") >= 2


# --- CRITICAL DRIFT TESTS ----------------------------------------------------
def test_changing_the_knowledge_separator_changes_knowledge_text(monkeypatch) -> None:
    """Composition drift must reach the seam automatically.

    Repointing the assembler's separator must change the composed string handed
    to the budget manager. If it did not, a future formatting change could
    silently invalidate the budget while the check still reported success.
    """
    from runtime.assembler import prompt_assembler as pa

    rec_before = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"), ("B", "two"))})
    bundle_before = assemble(ctx=ctx, token_budget=rec_before)

    monkeypatch.setattr(pa, "_SEPARATOR", "\n\n<<SEP>>\n\n")
    rec_after = Recorder()
    bundle_after = assemble(ctx=ctx, token_budget=rec_after)

    assert rec_after.request.knowledge_text != rec_before.request.knowledge_text
    assert "<<SEP>>" in rec_after.request.knowledge_text
    assert rec_after.request.knowledge_text == bundle_after.section(
        PromptSlot.KNOWLEDGE
    ).content, "composed text and shipped text must still agree after the change"
    assert "<<SEP>>" not in bundle_before.section(PromptSlot.KNOWLEDGE).content


def test_changing_heading_rendering_changes_knowledge_text(monkeypatch) -> None:
    from runtime.assembler import prompt_assembler as pa

    original = pa._render_section
    rec_before = Recorder()
    ctx = resolved(knowledge={"d.md": kdoc("d.md", ("A", "one"))})
    assemble(ctx=ctx, token_budget=rec_before)

    monkeypatch.setattr(pa, "_render_section", lambda s: "<<H>> " + original(s))
    rec_after = Recorder()
    bundle_after = assemble(ctx=ctx, token_budget=rec_after)

    assert "<<H>>" in rec_after.request.knowledge_text
    assert rec_after.request.knowledge_text != rec_before.request.knowledge_text
    assert rec_after.request.knowledge_text == bundle_after.section(
        PromptSlot.KNOWLEDGE
    ).content


def test_single_composition_path_is_used_for_both() -> None:
    """One join implementation only: the seam text and the slot come from it."""
    from runtime.assembler import prompt_assembler as pa

    src = pathlib.Path(pa.__file__).read_text(encoding="utf-8")
    assert src.count("_SEPARATOR.join") == 3, (
        "guardrails, branding and _compose_knowledge — Knowledge must not join twice"
    )
    assert "def _compose_knowledge" in src


def test_separator_exists_only_in_module_four() -> None:
    root = pathlib.Path(__file__).resolve().parents[2] / "runtime"
    for path in root.rglob("*.py"):
        if "__pycache__" in str(path) or path.name == "prompt_assembler.py":
            continue
        src = path.read_text(encoding="utf-8")
        assert "_SEPARATOR" not in src, f"{path.name} knows the separator"
        assert "_compose_knowledge" not in src, f"{path.name} knows the composition"
