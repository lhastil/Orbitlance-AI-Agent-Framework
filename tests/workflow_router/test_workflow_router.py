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
    ["", "   ", "yes", "I accept the recommendation", "book me a consultation",
     "we have collected sufficient information"],
)
def test_no_message_content_changes_the_outcome(
    router: WorkflowRouter, core: CoreBundle, message: str
) -> None:
    """Proof there is no hidden keyword list acting as framework semantics.

    Several of these read like the prose transitions in the workflow documents.
    None of them moves the router, because no machine-checkable rule exists and
    none was invented.
    """
    assert router.route(state("discovery"), message, core).target_workflow == "discovery"


# =============================================================================
# 3. deterministic transition — DOCUMENTED AS NOT AVAILABLE
# =============================================================================
def test_no_machine_checkable_transition_rule_exists_in_core() -> None:
    """Why §6.12(a) is not tested as a real transition.

    Asserted against the actual documents so this limitation is visible, and so
    the day someone authors machine-readable rules this test fails and points at
    the router that should then implement them.
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


def test_the_router_documents_that_it_cannot_advance_a_conversation() -> None:
    src = " ".join(
        (REPO_ROOT / "runtime" / "workflow_router" / "router.py")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "never advances a conversation past its first workflow" in src


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


def test_the_router_invents_no_extraction_rules() -> None:
    src = (REPO_ROOT / "runtime" / "workflow_router" / "router.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("re.search", "re.match", "regex", "keywords", "KEYWORDS",
                      ".lower()", "startswith", "in message"):
        assert forbidden not in src, f"router.py inspects the message via {forbidden}"


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
