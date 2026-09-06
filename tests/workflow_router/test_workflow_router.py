"""Workflow Router tests — specification §6.

Covers the four §6.12 scenarios, with one documented substitution.

**§6.12(a) — "a clear Discovery→Recommendation trigger routes correctly" — is
not implementable and is deliberately not faked.** That transition is defined in
`core/workflows/discovery.md` as *"If sufficient information has been
collected"*, a semantic judgement the frozen documents delegate to the AI. There
is no machine-checkable rule to test, and manufacturing a keyword heuristic in
the test would invent the very framework semantics the ratified decision forbids.
What is tested instead is the structural behaviour that genuinely exists: the
first-turn default and the conservative stay, plus the seam that will carry a
real transition once one can be justified.
"""

from __future__ import annotations

import pathlib

import pytest

from runtime.core_loader import CoreLoader, FilesystemCoreSource
from runtime.models.conversation import WorkflowState
from runtime.models.core_bundle import CoreBundle
from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_router import (
    FIRST_TURN_WORKFLOW,
    RouterError,
    UndefinedWorkflowError,
    WorkflowRouter,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def swap_workflow(core: CoreBundle, name: str, text: str) -> CoreBundle:
    """A `CoreBundle` whose named workflow carries `text`, sections re-derived.

    Uses the Core Loader's own splitter, so the substituted document is shaped
    exactly as a loaded one — the router must not be able to tell the difference.
    """
    import dataclasses

    from runtime.loader.markdown import split_sections
    from runtime.models.project_context import ProjectDocument, Section

    original = core.workflows[name]
    parsed = split_sections(text)
    replaced = ProjectDocument(
        name=original.name,
        relative_path=original.relative_path,
        exists=True,
        raw_text=text,
        sections=tuple(
            Section(
                ordinal=index,
                heading_text=section.heading,
                heading_level=section.level,
                body=section.body,
            )
            for index, section in enumerate(parsed.sections)
        ),
        preamble=parsed.preamble,
    )
    return dataclasses.replace(
        core, workflows={**dict(core.workflows), name: replaced}
    )


@pytest.fixture(scope="module")
def core() -> CoreBundle:
    return CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()


@pytest.fixture
def router() -> WorkflowRouter:
    return WorkflowRouter()


def state(active: str | None = None) -> WorkflowState:
    return WorkflowState(conversation_id="conv-1", active_workflow=active)


# =============================================================================
# 1. new conversation -> the ratified first-turn workflow (R-1)
# =============================================================================
def test_a_new_conversation_routes_to_discovery(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    decision = router.route(state(None), "hello", core)
    assert decision.target_workflow == "discovery"


def test_the_first_turn_workflow_is_one_centralised_constant() -> None:
    """Not scattered magic strings — one reviewable decision."""
    assert FIRST_TURN_WORKFLOW == "discovery"
    src = (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
        encoding="utf-8"
    )
    code = "\n".join(
        line for line in src.splitlines() if not line.strip().startswith("#")
    )
    assert code.count('"discovery"') == 1, "the workflow name appears exactly once"


def test_the_first_turn_choice_is_supported_by_core_content() -> None:
    """R-1 is grounded in the framework's own document, not invented."""
    trigger = (REPO_ROOT / "core" / "workflows" / "discovery.md").read_text(
        encoding="utf-8"
    )
    assert "A new conversation begins" in trigger


def test_the_first_turn_workflow_is_injectable_for_tests(core: CoreBundle) -> None:
    other = WorkflowRouter(first_turn_workflow="consultation")
    assert other.route(state(None), "hi", core).target_workflow == "consultation"


# =============================================================================
# 2. existing workflow + ambiguous input -> stay put (R-2, §6.9)
# =============================================================================
@pytest.mark.parametrize(
    "active",
    ["discovery", "recommendation", "consultation", "crm_sync", "follow_up",
     "voice_agent"],
)
def test_an_active_workflow_is_retained(
    router: WorkflowRouter, core: CoreBundle, active: str
) -> None:
    """§6.9: ambiguous input keeps the current workflow — no thrashing."""
    assert router.route(state(active), "anything at all", core).target_workflow == active


@pytest.mark.parametrize(
    "message",
    ["", "   ", "yes", "we have collected sufficient information",
     "I accept the recommendation", "book me a consultation"],
)
def test_a_message_discovery_does_not_publish_keeps_the_workflow(
    router: WorkflowRouter, core: CoreBundle, message: str
) -> None:
    """Proof there is still no hidden keyword list acting as framework semantics.

    Every message here reads like a prose transition, and the last two are
    genuinely routing phrases — **for `recommendation`, not for `discovery`**.
    A workflow routes only on what *it* publishes, so none of these moves a
    discovery conversation. Two of them did move it in an earlier draft of this
    suite, which is exactly the confusion this case now pins.
    """
    assert router.route(state("discovery"), message, core).target_workflow == "discovery"


# =============================================================================
# 3. deterministic transition — DOCUMENTED AS NOT AVAILABLE
# =============================================================================
def test_the_prose_decision_points_are_still_judgements() -> None:
    """The prose rules did not become machine-checkable; a vocabulary was added.

    Was `test_no_machine_checkable_transition_rule_exists_in_core`, written to
    fail the day rules were authored. WR-1 authored them — as a **separate**
    Core-published routing vocabulary, not by rewriting these Decision Points.
    Both halves are asserted: the judgements below are unchanged, and the
    vocabulary lives elsewhere (see the WR-1 tests further down).
    """
    import re

    workflows = sorted((REPO_ROOT / "core" / "workflows").glob("*.md"))
    assert len(workflows) == 6

    with_decision_point = [
        p.stem
        for p in workflows
        if re.search(r"^## Decision Point", p.read_text(encoding="utf-8"), re.M)
    ]
    assert sorted(with_decision_point) == [
        "consultation", "crm_sync", "discovery", "follow_up", "recommendation"
    ], "five of six define a Decision Point; voice_agent defines none"

    # Every one of them turns on a judgement, not a checkable condition. That —
    # not their absence — is why no deterministic transition rule exists.
    judgements = {
        "consultation": "If the customer confirms the information",
        "crm_sync": "If synchronization succeeds",
        "discovery": "If sufficient information has been collected",
        "follow_up": "If the customer responds",
        "recommendation": "If the customer accepts the recommendation",
    }
    for stem, phrase in judgements.items():
        src = (REPO_ROOT / "core" / "workflows" / f"{stem}.md").read_text(
            encoding="utf-8"
        )
        assert phrase in src, f"{stem} no longer states {phrase!r}"


def test_the_router_documents_that_core_owns_the_vocabulary() -> None:
    """Was an assertion that the router could not advance a conversation.

    WR-1 made that false. What replaces it is the claim that matters now: this
    module defines no phrase and no ordering, and says so.
    """
    src = " ".join(
        (REPO_ROOT / "runtime" / "workflow_router" / "router.py")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "defines no phrase and no ordering" in src
    assert "never advances a conversation past its first workflow" not in src


# =============================================================================
# 4. unknown target -> clear failure (§6.10)
# =============================================================================
def test_an_active_workflow_absent_from_core_fails_clearly(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    with pytest.raises(UndefinedWorkflowError) as caught:
        router.route(state("not_a_workflow"), "hi", core)
    message = str(caught.value)
    assert "not_a_workflow" in message
    assert "discovery" in message, "the message lists what is available"
    assert "6.10" in message


def test_a_missing_first_turn_workflow_fails_clearly(core: CoreBundle) -> None:
    router = WorkflowRouter(first_turn_workflow="nonexistent")
    with pytest.raises(UndefinedWorkflowError, match="nonexistent"):
        router.route(state(None), "hi", core)


def test_an_empty_core_bundle_fails_rather_than_inventing(
    router: WorkflowRouter,
) -> None:
    with pytest.raises(UndefinedWorkflowError, match=r"\(none\)"):
        router.route(state(None), "hi", CoreBundle())


def test_the_error_is_a_router_error() -> None:
    assert issubclass(UndefinedWorkflowError, RouterError)


def test_the_two_failure_reasons_are_distinguished(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    with pytest.raises(UndefinedWorkflowError) as first_turn:
        WorkflowRouter(first_turn_workflow="ghost").route(state(None), "x", core)
    with pytest.raises(UndefinedWorkflowError) as carried:
        router.route(state("ghost"), "x", core)
    assert "not defined in Core" in str(first_turn.value)
    assert "no longer defined in Core" in str(carried.value)


# =============================================================================
# 5. the target is a stem, not a filename
# =============================================================================
def test_the_decision_names_a_stem_not_a_filename(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    target = router.route(state(None), "hi", core).target_workflow
    assert not target.endswith(".md")
    assert f"{target}.md" in core.workflows


def test_every_reachable_target_matches_a_core_stem(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    stems = {n[:-3] for n in core.workflows}
    for active in (None, *stems):
        assert router.route(state(active), "hi", core).target_workflow in stems


# =============================================================================
# 6-9. purity: determinism, no side effects, no mutation (§6.12c)
# =============================================================================
def test_identical_inputs_produce_identical_decisions(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    a = router.route(state("discovery"), "same message", core)
    b = router.route(state("discovery"), "same message", core)
    assert a == b
    assert a is not b


def test_repeated_calls_have_no_side_effects(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """§6.12(c): calling route() twice with identical inputs changes nothing."""
    current = state("discovery")
    before = (current.active_workflow, current.collected_data,
              current.transition_history)
    core_before = (sorted(core.workflows), sorted(core.prompts))
    for _ in range(3):
        router.route(current, "hello", core)
    assert (current.active_workflow, current.collected_data,
            current.transition_history) == before
    assert (sorted(core.workflows), sorted(core.prompts)) == core_before


def test_workflow_state_is_not_mutated(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    current = WorkflowState(
        conversation_id="conv-1",
        active_workflow="discovery",
        collected_data=(("k", "v"),),
        transition_history=("None->discovery",),
    )
    router.route(current, "hi", core)
    assert current.active_workflow == "discovery"
    assert current.collected_data == (("k", "v"),)
    assert current.transition_history == ("None->discovery",)


def test_core_bundle_is_not_mutated(router: WorkflowRouter, core: CoreBundle) -> None:
    workflows_before = dict(core.workflows)
    router.route(state(None), "hi", core)
    assert dict(core.workflows) == workflows_before


def test_the_router_holds_no_mutable_state(core: CoreBundle) -> None:
    router = WorkflowRouter()
    assert set(WorkflowRouter.__slots__) == {"_first_turn_workflow"}
    router.route(state("discovery"), "a", core)
    assert router.route(state(None), "b", core).target_workflow == FIRST_TURN_WORKFLOW


# =============================================================================
# 10-12. forbidden dependencies and content
# =============================================================================
def test_the_router_never_imports_module_seven() -> None:
    package = REPO_ROOT / "runtime" / "workflow_router"
    for path in package.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        assert "workflow_state" not in src, f"{path.name} references Module 7"


def test_the_router_depends_only_on_models_and_itself() -> None:
    """§6.7 permits Core Loader and optionally the Provider Interface; the
    provider path is out of scope, so only the shared models are imported."""
    package = REPO_ROOT / "runtime" / "workflow_router"
    allowed = ("runtime.models", "runtime.workflow_router")
    for path in package.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("from runtime", "import runtime")):
                continue
            module = stripped.split()[1]
            assert module.startswith(allowed), f"{path.name} imports {module}"


def test_no_provider_or_network_code() -> None:
    """D-4: the provider-backed path is out of scope for this milestone."""
    package = REPO_ROOT / "runtime" / "workflow_router"
    for path in package.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for forbidden in ("runtime.provider", "requests", "httpx", "socket",
                          "urllib", "google", "openai", "anthropic"):
            assert forbidden not in src, f"{path.name} references {forbidden}"


def test_no_persistence_or_filesystem_access() -> None:
    """Checked against executable code, not prose.

    The docstrings explain what the router does *not* do and name Module 7's
    `commit_transition` in a usage example; describing a boundary is not
    crossing it.
    """
    import ast

    forbidden = {"open", "Path", "pathlib", "store", "commit", "commit_transition"}
    package = REPO_ROOT / "runtime" / "workflow_router"
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            ast.get_docstring(n)
            for n in ast.walk(tree)
            if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in forbidden, f"{path.name} uses {node.id}"
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden, f"{path.name} uses {node.attr}"
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in docstrings:
                    continue
                assert node.value not in forbidden, f"{path.name} uses {node.value}"


def test_no_industry_playbook_content_is_referenced(core: CoreBundle) -> None:
    """§6.12(d). The Core Loader already keeps playbook content out of the
    bundle, so the router could not reach it even if it tried."""
    assert core.playbook_names
    assert not any(
        "industry_playbooks" in d.relative_path for d in core.all_documents
    )
    package = REPO_ROOT / "runtime" / "workflow_router"
    for path in package.glob("*.py"):
        assert "playbook" not in path.read_text(encoding="utf-8").lower()


# =============================================================================
# 13. collected_data is deterministic and empty (D-3)
# =============================================================================
def test_collected_data_is_empty_when_nothing_can_be_extracted(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    for message in ("", "my name is Ada and my budget is 5000", "yes"):
        decision = router.route(state("discovery"), message, core)
        assert dict(decision.collected_data) == {}


def test_collected_data_is_a_read_only_mapping(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    decision = router.route(state(None), "hi", core)
    with pytest.raises(TypeError):
        decision.collected_data["k"] = "v"  # type: ignore[index]


def test_the_router_invents_no_classification_machinery() -> None:
    """Was `test_the_router_invents_no_extraction_rules`.

    Its premise — that the router must not inspect the message at all — was
    correct until WR-1 authorized exactly that. What survives is the part that
    still holds and still matters: **no pattern machinery, no scoring, no
    thresholds, no invented vocabulary**. `startswith` and `in` were removed
    from the list because the implementation now uses them to strip a Core
    bullet and to match a Core phrase, which is the authorized behaviour; the
    stronger guarantee is asserted separately by
    `test_wr1_no_routing_phrase_is_authoritative_in_python`.
    """
    src = (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("re.search", "re.match", "re.compile", "regex", "keywords",
                      "KEYWORDS", "threshold", "confidence", "score",
                      "similarity", "classify", ".lower()"):
        assert forbidden not in src, f"router.py uses {forbidden}"


# =============================================================================
# WR-1 — §6.2: message-driven routing on Core-published vocabulary
# =============================================================================
ROUTING_SECTION = "Routing Phrases"
PUBLISHED = {"discovery": "recommendation", "recommendation": "consultation"}


def published_phrases(workflow: str, target: str) -> tuple[str, ...]:
    """The phrases Core publishes, read from the document the router reads."""
    text = (REPO_ROOT / "core" / "workflows" / f"{workflow}.md").read_text(
        encoding="utf-8"
    )
    section = text.split(f"## {ROUTING_SECTION}", 1)[1]
    body = section.split(f"### {target}\n", 1)[1].split("\n#", 1)[0]
    return tuple(
        line[2:].strip() for line in body.splitlines() if line.startswith("- ")
    )


def test_wr1_discovery_advances_to_recommendation(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """§6.12(a) as a real transition — the scenario that could not be written."""
    for phrase in published_phrases("discovery", "recommendation"):
        decision = router.route(state("discovery"), f"Hi, {phrase}?", core)
        assert decision.target_workflow == "recommendation", phrase


def test_wr1_recommendation_advances_to_consultation(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    for phrase in published_phrases("recommendation", "consultation"):
        decision = router.route(state("recommendation"), f"OK — {phrase}.", core)
        assert decision.target_workflow == "consultation", phrase


def test_wr1_matching_is_case_insensitive(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    phrase = published_phrases("recommendation", "consultation")[0]
    for variant in (phrase.upper(), phrase.title(), phrase):
        assert (
            router.route(state("recommendation"), variant, core).target_workflow
            == "consultation"
        )


def test_wr1_the_latest_message_changes_the_decision(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """The same state, two messages, two outcomes — §6.2's message clause."""
    phrase = published_phrases("discovery", "recommendation")[0]
    current = state("discovery")
    assert router.route(current, phrase, core).target_workflow == "recommendation"
    assert router.route(current, "how do I get there?", core).target_workflow == "discovery"


def test_wr1_an_unpublished_message_stays_put(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """§6.9 conservative default, on the workflows that do publish a vocabulary."""
    for active in PUBLISHED:
        for message in ("", "   ", "hello", "what are your opening hours?"):
            assert (
                router.route(state(active), message, core).target_workflow == active
            )


def test_wr1_a_workflow_publishing_nothing_routes_nowhere(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """consultation, crm_sync, follow_up and voice_agent publish no vocabulary.

    They are out of WR-1's scope, and the router must not invent one for them.
    `consultation` in particular has no onward target: what completion means is
    WR-2, which this work does not implement.
    """
    for active in ("consultation", "crm_sync", "follow_up", "voice_agent"):
        for message in ("I accept the recommendation", "submit the request",
                        "what do you recommend", "yes please"):
            assert (
                router.route(state(active), message, core).target_workflow == active
            )


def test_wr1_no_published_target_is_regressive() -> None:
    """H-2: no-regression is a property of Core's content, asserted here.

    The router holds no ordering table by design, so this is where the
    progression is guaranteed. A backward subsection published tomorrow fails
    this test rather than silently making conversations oscillate.
    """
    order = ["discovery", "recommendation", "consultation"]
    for workflow in (REPO_ROOT / "core" / "workflows").glob("*.md"):
        text = workflow.read_text(encoding="utf-8")
        if f"## {ROUTING_SECTION}" not in text:
            continue
        section = text.split(f"## {ROUTING_SECTION}", 1)[1].split("\n## ", 1)[0]
        targets = [
            line[4:].strip() for line in section.splitlines() if line.startswith("### ")
        ]
        assert targets, f"{workflow.name} publishes a routing section with no target"
        for target in targets:
            assert target in order, f"{workflow.name} routes to {target!r}"
            assert order.index(target) > order.index(workflow.stem), (
                f"{workflow.name} publishes a regressive target {target!r}"
            )


def test_wr1_only_the_two_authorized_workflows_publish_a_vocabulary() -> None:
    """Scope, asserted against Core rather than assumed."""
    publishing = {
        path.stem
        for path in (REPO_ROOT / "core" / "workflows").glob("*.md")
        if f"## {ROUTING_SECTION}" in path.read_text(encoding="utf-8")
    }
    assert publishing == set(PUBLISHED)


def test_wr1_every_published_target_exists_in_core(core: CoreBundle) -> None:
    """§6.10, at the source: Core cannot publish a target Core does not define."""
    for workflow, target in PUBLISHED.items():
        assert f"{target}.md" in core.workflows
        assert published_phrases(workflow, target)


def test_wr1_no_decision_ever_targets_submit(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """WR-2's boundary: `submit` is not a workflow and must never be a target."""
    assert "submit.md" not in core.workflows
    for active in (None, "discovery", "recommendation", "consultation"):
        for message in ("submit the consultation request", "I confirm the information",
                        "please submit it"):
            decision = router.route(state(active), message, core)
            assert decision.target_workflow != "submit"
            assert f"{decision.target_workflow}.md" in core.workflows


def test_wr1_no_routing_phrase_is_authoritative_in_python() -> None:
    """The substance of the ruling: Core is the authority, Python is not.

    Every phrase the router can match appears in `core/workflows/`, and none is
    written in `router.py`. A list in Python that Core happens to agree with is
    exactly what the ruling forbids.
    """
    src = (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
        encoding="utf-8"
    )
    for workflow, target in PUBLISHED.items():
        phrases = published_phrases(workflow, target)
        assert phrases
        for phrase in phrases:
            assert phrase not in src, f"router.py hardcodes {phrase!r}"


def test_wr1_the_router_holds_no_workflow_ordering_policy() -> None:
    """H-2: the progression is Core-declared, not tabulated in Python.

    `_ROUTING_SECTION` is the one routing constant, and it is an address. A
    from/to map here would move ordering policy into the runtime.

    Checked against **executable string values only** — docstrings and comments
    are prose and may discuss workflows freely. `discovery` is exempt because
    `FIRST_TURN_WORKFLOW` is R-1's single reviewable choice, sourced from Core
    and asserted by `test_the_first_turn_choice_is_supported_by_core_content`.
    Every other workflow name appearing in executable code would be an ordering
    table by another name.
    """
    import ast

    tree = ast.parse(
        (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
            encoding="utf-8"
        )
    )
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    values = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]
    for workflow in ("recommendation", "consultation", "crm_sync", "follow_up",
                     "voice_agent"):
        for value in values:
            assert workflow not in value, f"router.py names {workflow!r} in code"


def test_wr1_the_router_follows_core_when_core_changes(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """Proof of derivation rather than transcription.

    A Core document carrying a different phrase produces different behaviour
    with no code change. A transcribed copy would ignore this entirely.
    """
    original = core.workflows["discovery.md"]
    phrase = published_phrases("discovery", "recommendation")[0]
    rewritten = original.raw_text.replace(f"- {phrase}", "- summon the badger")
    patched = swap_workflow(core, "discovery.md", rewritten)

    assert router.route(state("discovery"), "summon the badger", patched).target_workflow == "recommendation"
    assert router.route(state("discovery"), phrase, patched).target_workflow == "discovery"


def test_wr1_collected_data_is_still_empty_on_a_transition(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """D-3 unchanged: advancing a workflow extracts nothing."""
    phrase = published_phrases("discovery", "recommendation")[0]
    decision = router.route(state("discovery"), phrase, core)
    assert decision.target_workflow == "recommendation"
    assert dict(decision.collected_data) == {}


def test_wr1_a_transition_is_deterministic_and_side_effect_free(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """§6.12(c) on the new path, not only on the stay-put path."""
    phrase = published_phrases("recommendation", "consultation")[0]
    current = state("recommendation")
    first = router.route(current, phrase, core)
    second = router.route(current, phrase, core)
    assert first == second
    assert current.active_workflow == "recommendation"


def test_wr1_the_seam_carries_a_real_transition_through_module_seven(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """H-1's Router -> Module 7 proof for discovery -> recommendation.

    No activatable fixture enables Recommendation, so the end-to-end proof for
    this transition stops here, at the seam §6 and §7 actually share. The
    limitation is the fixtures', not the router's — recorded in WR-1's closure.
    """
    from runtime.workflow_state import WorkflowStateManager

    states = WorkflowStateManager()
    states.commit_transition("c1", router.route(state(None), "hello", core))
    assert states.get_state("c1").active_workflow == "discovery"

    phrase = published_phrases("discovery", "recommendation")[0]
    committed = states.commit_transition(
        "c1", router.route(states.get_state("c1"), phrase, core)
    )
    assert committed.active_workflow == "recommendation"
    assert committed.transition_history[-1] == "discovery->recommendation"

    phrase = published_phrases("recommendation", "consultation")[0]
    committed = states.commit_transition(
        "c1", router.route(states.get_state("c1"), phrase, core)
    )
    assert committed.active_workflow == "consultation"
    assert committed.transition_history[-1] == "recommendation->consultation"


# =============================================================================
# 14. real seam: Router -> Module 7 -> Prompt Assembler
# =============================================================================
def test_seam_a_decision_flows_through_module_seven_to_the_assembler(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    from runtime.assembler import PromptAssembler
    from runtime.loader import FilesystemProjectSource, ProjectLoader
    from runtime.models.budget import BudgetSelection
    from runtime.models.conversation import ConversationContext, Turn, TurnRole
    from runtime.models.prompt_bundle import PromptSlot
    from runtime.resolver import Resolver
    from runtime.workflow_state import WorkflowStateManager

    resolved = Resolver().resolve(
        core,
        ProjectLoader(FilesystemProjectSource(REPO_ROOT / "projects")).load(
            "sunrise_dental_clinic"
        ),
    )
    workflows = WorkflowStateManager()

    decision = router.route(workflows.get_state("conv-1"), "hello", core)
    committed = workflows.commit_transition("conv-1", decision)
    assert committed.active_workflow == "discovery"
    assert committed.transition_history == ("None->discovery",)

    class Budget:
        def select(self, request):  # noqa: ARG002
            return BudgetSelection(knowledge_sections=(), history_window=())

    bundle = PromptAssembler(core, token_budget=Budget()).assemble(
        resolved,
        committed,
        ConversationContext(
            conversation_id="conv-1",
            project_id="sunrise_dental_clinic",
            turns=(Turn(TurnRole.USER, "hello"),),
        ),
    )
    workflow_section = bundle.section(PromptSlot.WORKFLOW)
    assert workflow_section is not None
    assert workflow_section.sources == ("core/workflows/discovery.md",)


def test_seam_the_router_produces_what_module_seven_accepts(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    decision = router.route(state(None), "hi", core)
    assert isinstance(decision, WorkflowTransitionDecision)
    assert decision.target_workflow and decision.target_workflow.strip()


# =============================================================================
# 15. project scope is NOT this module's responsibility
# =============================================================================
def test_the_router_does_not_enforce_project_enabled_workflows() -> None:
    """§6.6 gives the router no `ResolvedContext`, so it cannot know what a
    project enabled. The Prompt Assembler enforces that scope as defence in
    depth; the Runtime Engine will be the primary gate."""
    import ast
    import inspect

    params = list(inspect.signature(WorkflowRouter.route).parameters)
    assert params == ["self", "current_state", "latest_message", "core_bundle"]

    # Checked against the syntax tree: the docstring explains that the router
    # does not receive these, which is the opposite of using them.
    tree = ast.parse(
        (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
            encoding="utf-8"
        )
    )
    docstrings = {
        ast.get_docstring(n)
        for n in ast.walk(tree)
        if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in {"ResolvedContext", "enabled_workflows"}
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"enabled_workflows"}
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in docstrings:
                continue
            assert node.value not in {"ResolvedContext", "enabled_workflows"}


def test_the_assembler_still_rejects_an_unenabled_routed_workflow(
    router: WorkflowRouter, core: CoreBundle
) -> None:
    """The division of labour, end to end: the router names discovery, and the
    assembler refuses it for a project that did not enable it."""
    import dataclasses

    from runtime.assembler import PromptAssembler, WorkflowNotEnabledError
    from runtime.loader import FilesystemProjectSource, ProjectLoader
    from runtime.models.budget import BudgetSelection
    from runtime.models.conversation import ConversationContext, Turn, TurnRole
    from runtime.resolver import Resolver
    from runtime.workflow_state import WorkflowStateManager

    resolved = Resolver().resolve(
        core,
        ProjectLoader(FilesystemProjectSource(REPO_ROOT / "projects")).load(
            "sunrise_dental_clinic"
        ),
    )
    restricted = dataclasses.replace(
        resolved,
        config=dataclasses.replace(
            resolved.config, enabled_workflows=("consultation",)
        ),
    )

    workflows = WorkflowStateManager()
    decision = router.route(workflows.get_state("conv-2"), "hello", core)
    assert decision.target_workflow == "discovery"  # the router does not object
    committed = workflows.commit_transition("conv-2", decision)

    class Budget:
        def select(self, request):  # noqa: ARG002
            return BudgetSelection(knowledge_sections=(), history_window=())

    with pytest.raises(WorkflowNotEnabledError):
        PromptAssembler(core, token_budget=Budget()).assemble(
            restricted,
            committed,
            ConversationContext(
                conversation_id="conv-2",
                project_id="sunrise_dental_clinic",
                turns=(Turn(TurnRole.USER, "hello"),),
            ),
        )
