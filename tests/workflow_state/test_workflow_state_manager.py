"""Workflow State Manager tests — specification §7.

All four §7.12 scenarios are covered and each is named in the test that covers
it, including (c) with **real threads** rather than a simulated race: a
read-modify-write that lost an update would produce a shorter
`transition_history` than the number of commits, which is the observable that
matters.

The four ratified decisions each have tests that would catch the wrong
behaviour — in particular D-4, where defaulting to Discovery would let the
Prompt Assembler render a workflow a project had switched off. That is asserted
against the real Assembler, not described.
"""

from __future__ import annotations

import dataclasses
import pathlib
import threading

import pytest

from runtime.models.conversation import WorkflowState
from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_state import (
    NO_PREVIOUS_WORKFLOW,
    TRANSITION_ARROW,
    InMemoryWorkflowStateStore,
    InvalidTransitionError,
    WorkflowStateError,
    WorkflowStateManager,
    WorkflowStateStore,
    WorkflowStateStoreUnavailableError,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def workflows() -> WorkflowStateManager:
    return WorkflowStateManager(InMemoryWorkflowStateStore())


def decision(target: str = "discovery", **data: str) -> WorkflowTransitionDecision:
    return WorkflowTransitionDecision(target_workflow=target, collected_data=data)


# =============================================================================
# §7.12(a) — commits and retrieves correctly
# =============================================================================
def test_a_commits_and_retrieves(workflows: WorkflowStateManager) -> None:
    committed = workflows.commit_transition("c", decision("discovery"))
    assert committed.active_workflow == "discovery"
    assert workflows.get_state("c") == committed


def test_a_committed_state_carries_the_conversation_id(
    workflows: WorkflowStateManager,
) -> None:
    assert workflows.commit_transition("c", decision()).conversation_id == "c"


def test_first_access_creates_an_empty_state(workflows: WorkflowStateManager) -> None:
    """The data-model row's "created on first message"."""
    state = workflows.get_state("brand-new")
    assert isinstance(state, WorkflowState)
    assert state.conversation_id == "brand-new"
    assert state.active_workflow is None
    assert state.collected_data == ()
    assert state.transition_history == ()


def test_get_state_does_not_persist_the_empty_state(
    workflows: WorkflowStateManager,
) -> None:
    """Reading must not manufacture a stored conversation."""
    workflows.get_state("c")
    assert not workflows.exists("c")
    assert workflows.conversation_ids() == ()


def test_state_survives_across_turns(workflows: WorkflowStateManager) -> None:
    workflows.commit_transition("c", decision("discovery", name="Ada"))
    for _ in range(3):
        assert workflows.get_state("c").active_workflow == "discovery"
    assert dict(workflows.get_state("c").collected_data) == {"name": "Ada"}


# =============================================================================
# §7.12(b) — two conversations never see each other's state
# =============================================================================
def test_b_two_conversations_never_share_state(
    workflows: WorkflowStateManager,
) -> None:
    workflows.commit_transition("a", decision("discovery", secret="A"))
    workflows.commit_transition("b", decision("consultation", secret="B"))

    sa, sb = workflows.get_state("a"), workflows.get_state("b")
    assert sa.active_workflow == "discovery"
    assert sb.active_workflow == "consultation"
    assert dict(sa.collected_data) == {"secret": "A"}
    assert dict(sb.collected_data) == {"secret": "B"}
    assert sa.transition_history != sb.transition_history


def test_committing_one_conversation_leaves_the_other_untouched(
    workflows: WorkflowStateManager,
) -> None:
    workflows.commit_transition("a", decision("discovery"))
    before = workflows.get_state("a")
    workflows.commit_transition("b", decision("follow_up"))
    assert workflows.get_state("a") == before


def test_separate_managers_share_nothing() -> None:
    one, two = WorkflowStateManager(), WorkflowStateManager()
    one.commit_transition("c", decision("discovery"))
    assert two.get_state("c").active_workflow is None


# =============================================================================
# §7.12(c) — concurrent commits do not corrupt state (§7.10 atomicity)
# =============================================================================
def test_c_concurrent_commits_lose_no_updates(
    workflows: WorkflowStateManager,
) -> None:
    """Real threads. A lost read-modify-write shortens transition_history."""
    commits = 60
    barrier = threading.Barrier(commits)
    errors: list[BaseException] = []

    def commit(index: int) -> None:
        try:
            barrier.wait()  # maximise overlap
            workflows.commit_transition("c", decision(f"workflow_{index}"))
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=commit, args=(i,)) for i in range(commits)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    final = workflows.get_state("c")
    assert len(final.transition_history) == commits, "an update was lost"
    assert len(set(final.transition_history)) == commits, "an entry was duplicated"


def test_c_concurrent_commits_across_conversations_stay_isolated() -> None:
    manager = WorkflowStateManager()
    ids = [f"conv-{i}" for i in range(12)]
    barrier = threading.Barrier(len(ids))

    def commit(cid: str) -> None:
        barrier.wait()
        for step in range(5):
            manager.commit_transition(cid, decision(f"{cid}_step_{step}"))

    threads = [threading.Thread(target=commit, args=(c,)) for c in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for cid in ids:
        state = manager.get_state(cid)
        assert len(state.transition_history) == 5
        assert all(cid in entry for entry in state.transition_history)


def test_c_the_history_chain_is_internally_consistent(
    workflows: WorkflowStateManager,
) -> None:
    """Each entry's origin is the previous entry's target — no torn writes."""
    commits = 40
    barrier = threading.Barrier(commits)

    def commit(i: int) -> None:
        barrier.wait()
        workflows.commit_transition("c", decision(f"w{i}"))

    threads = [threading.Thread(target=commit, args=(i,)) for i in range(commits)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    history = workflows.get_state("c").transition_history
    assert history[0].startswith(f"{NO_PREVIOUS_WORKFLOW}{TRANSITION_ARROW}")
    for earlier, later in zip(history, history[1:], strict=False):
        assert later.split(TRANSITION_ARROW)[0] == earlier.split(TRANSITION_ARROW)[1]


def test_locks_are_per_conversation_not_global(
    workflows: WorkflowStateManager,
) -> None:
    workflows.commit_transition("a", decision())
    workflows.commit_transition("b", decision())
    locks = workflows._locks  # noqa: SLF001
    assert locks["a"] is not locks["b"]


# =============================================================================
# §7.12(d) — persistence failure is loud, never a silent reset (§7.9)
# =============================================================================
@pytest.mark.parametrize("operation", ["get", "put"])
def test_d_store_failure_surfaces_clearly(operation: str) -> None:
    class Broken(InMemoryWorkflowStateStore):
        def get(self, conversation_id: str):  # noqa: ARG002
            if operation == "get":
                raise OSError("store offline")
            return super().get(conversation_id)

        def put(self, conversation_id: str, state: WorkflowState) -> None:
            if operation == "put":
                raise OSError("store offline")
            super().put(conversation_id, state)

    manager = WorkflowStateManager(Broken())
    with pytest.raises(WorkflowStateStoreUnavailableError, match="cannot continue"):
        manager.commit_transition("c", decision())


def test_d_store_failure_never_returns_a_default_state() -> None:
    """§7.9: a silent reset would look like the agent forgot the conversation."""

    class Broken(InMemoryWorkflowStateStore):
        def get(self, conversation_id: str):  # noqa: ARG002
            raise OSError("disk gone")

    manager = WorkflowStateManager(Broken())
    with pytest.raises(WorkflowStateStoreUnavailableError) as caught:
        manager.get_state("c")
    assert isinstance(caught.value.cause, OSError)
    assert caught.value.__cause__ is not None


def test_d_a_read_failure_mid_conversation_does_not_reset() -> None:
    """The dangerous case: state exists, then the store breaks."""
    class Flaky(InMemoryWorkflowStateStore):
        failing = False

        def get(self, conversation_id: str):
            if self.failing:
                raise OSError("transient")
            return super().get(conversation_id)

    store = Flaky()
    manager = WorkflowStateManager(store)
    manager.commit_transition("c", decision("recommendation", got="data"))

    store.failing = True
    with pytest.raises(WorkflowStateStoreUnavailableError):
        manager.get_state("c")

    store.failing = False
    # recovery leaves the real state intact - nothing was reset
    recovered = manager.get_state("c")
    assert recovered.active_workflow == "recommendation"
    assert dict(recovered.collected_data) == {"got": "data"}


def test_every_error_is_a_workflow_state_error() -> None:
    for error in (InvalidTransitionError, WorkflowStateStoreUnavailableError):
        assert issubclass(error, WorkflowStateError)


# =============================================================================
# D-1 / D-2 — the decision model and collected_data
# =============================================================================
def test_d1_decision_has_exactly_the_two_ratified_fields() -> None:
    assert set(WorkflowTransitionDecision.__dataclass_fields__) == {
        "target_workflow",
        "collected_data",
    }


def test_d1_no_speculative_fields_were_added() -> None:
    for forbidden in ("reason", "rationale", "confidence", "timestamp", "changed"):
        assert not hasattr(WorkflowTransitionDecision("x"), forbidden)


def test_d1_collected_data_defaults_to_empty() -> None:
    assert dict(WorkflowTransitionDecision("discovery").collected_data) == {}


def test_d1_the_decision_is_immutable() -> None:
    d = WorkflowTransitionDecision("discovery", {"a": "1"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.target_workflow = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        d.collected_data["a"] = "2"  # type: ignore[index]


def test_d1_the_decision_copies_the_callers_mapping() -> None:
    supplied = {"name": "Ada"}
    d = WorkflowTransitionDecision("discovery", supplied)
    supplied["name"] = "MUTATED"
    assert dict(d.collected_data) == {"name": "Ada"}


def test_d2_collected_data_is_persisted_exactly(
    workflows: WorkflowStateManager,
) -> None:
    state = workflows.commit_transition(
        "c", decision("discovery", name="Ada", need="cleaning")
    )
    assert dict(state.collected_data) == {"name": "Ada", "need": "cleaning"}


def test_d2_collected_data_preserves_the_supplied_order(
    workflows: WorkflowStateManager,
) -> None:
    """Order is the decision's own; sorting it would be transforming it."""
    supplied = {"z": "1", "a": "2", "m": "3"}
    state = workflows.commit_transition(
        "c", WorkflowTransitionDecision("discovery", supplied)
    )
    assert [k for k, _ in state.collected_data] == ["z", "a", "m"]


def test_d2_a_later_decision_replaces_rather_than_merges(
    workflows: WorkflowStateManager,
) -> None:
    """Merging would be Module 7 deciding what the conversation knows (§7.3).

    The Router receives the current state (§6.4) and is the component in a
    position to carry data forward.
    """
    workflows.commit_transition("c", decision("discovery", first="1"))
    state = workflows.commit_transition("c", decision("recommendation", second="2"))
    assert dict(state.collected_data) == {"second": "2"}


def test_d2_the_manager_never_generates_collected_data(
    workflows: WorkflowStateManager,
) -> None:
    state = workflows.commit_transition("c", decision("discovery"))
    assert state.collected_data == ()


def test_d2_mutating_the_callers_mapping_after_commit_changes_nothing(
    workflows: WorkflowStateManager,
) -> None:
    supplied = {"name": "Ada"}
    workflows.commit_transition("c", WorkflowTransitionDecision("discovery", supplied))
    supplied["name"] = "MUTATED"
    assert dict(workflows.get_state("c").collected_data) == {"name": "Ada"}


# =============================================================================
# D-3 — transition history
# =============================================================================
def test_d3_the_first_transition_records_no_previous_workflow(
    workflows: WorkflowStateManager,
) -> None:
    state = workflows.commit_transition("c", decision("discovery"))
    assert state.transition_history == ("None->discovery",)


def test_d3_subsequent_transitions_record_previous_to_target(
    workflows: WorkflowStateManager,
) -> None:
    workflows.commit_transition("c", decision("discovery"))
    workflows.commit_transition("c", decision("recommendation"))
    state = workflows.commit_transition("c", decision("consultation"))
    assert state.transition_history == (
        "None->discovery",
        "discovery->recommendation",
        "recommendation->consultation",
    )


def test_d3_a_same_workflow_transition_is_still_recorded(
    workflows: WorkflowStateManager,
) -> None:
    """Staying put is §6.9's conservative outcome; the commit is still a commit."""
    workflows.commit_transition("c", decision("discovery"))
    state = workflows.commit_transition("c", decision("discovery"))
    assert state.active_workflow == "discovery"
    assert state.transition_history == ("None->discovery", "discovery->discovery")


def test_d3_history_is_append_only(workflows: WorkflowStateManager) -> None:
    workflows.commit_transition("c", decision("discovery"))
    first = workflows.get_state("c").transition_history
    workflows.commit_transition("c", decision("recommendation"))
    second = workflows.get_state("c").transition_history
    assert second[: len(first)] == first
    assert len(second) == len(first) + 1


def test_d3_no_timestamps_or_richer_structure(
    workflows: WorkflowStateManager,
) -> None:
    state = workflows.commit_transition("c", decision("discovery"))
    entry = state.transition_history[0]
    assert isinstance(entry, str)
    assert entry.count(TRANSITION_ARROW) == 1
    assert not any(ch.isdigit() for ch in entry)


# =============================================================================
# D-4 — no implicit Discovery default
# =============================================================================
def test_d4_a_new_conversation_has_no_active_workflow(
    workflows: WorkflowStateManager,
) -> None:
    assert workflows.get_state("fresh").active_workflow is None


def test_d4_the_module_names_no_workflow_anywhere() -> None:
    """Module 7 must never choose a workflow (§7.3).

    Checked against the parsed syntax tree: the package docstring shows a usage
    example naming a workflow, which is documentation, not a choice the module
    makes.
    """
    import ast

    names = {"discovery", "recommendation", "consultation",
             "crm_sync", "follow_up", "voice_agent"}
    package = REPO_ROOT / "runtime" / "workflow_state"
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            ast.get_docstring(n)
            for n in ast.walk(tree)
            if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node.value in docstrings:
                continue
            assert node.value not in names, f"{path.name} names {node.value}"


def test_d4_only_a_committed_decision_sets_a_workflow(
    workflows: WorkflowStateManager,
) -> None:
    assert workflows.get_state("c").active_workflow is None
    assert workflows.commit_transition("c", decision("follow_up")).active_workflow == (
        "follow_up"
    )


# =============================================================================
# invalid transitions — structural only, never a routing judgement
# =============================================================================
@pytest.mark.parametrize("target", ["", "   ", "\t\n"])
def test_an_empty_target_workflow_is_refused(
    workflows: WorkflowStateManager, target: str
) -> None:
    with pytest.raises(InvalidTransitionError, match="target_workflow is empty"):
        workflows.commit_transition("c", WorkflowTransitionDecision(target))


def test_a_non_decision_object_is_refused(workflows: WorkflowStateManager) -> None:
    with pytest.raises(InvalidTransitionError, match="expected a"):
        workflows.commit_transition("c", "discovery")  # type: ignore[arg-type]


def test_an_invalid_transition_does_not_touch_stored_state(
    workflows: WorkflowStateManager,
) -> None:
    workflows.commit_transition("c", decision("discovery"))
    before = workflows.get_state("c")
    with pytest.raises(InvalidTransitionError):
        workflows.commit_transition("c", WorkflowTransitionDecision(""))
    assert workflows.get_state("c") == before


def test_the_manager_does_not_validate_against_core(
    workflows: WorkflowStateManager,
) -> None:
    """§6.10's assertion is the Router's; §7.7 leaves this module no CoreBundle."""
    state = workflows.commit_transition("c", decision("not_a_real_workflow"))
    assert state.active_workflow == "not_a_real_workflow"


# =============================================================================
# snapshot / alias safety
# =============================================================================
def test_a_returned_state_is_not_changed_by_later_commits(
    workflows: WorkflowStateManager,
) -> None:
    first = workflows.commit_transition("c", decision("discovery"))
    workflows.commit_transition("c", decision("recommendation"))
    assert first.active_workflow == "discovery"
    assert first.transition_history == ("None->discovery",)


def test_state_is_immutable(workflows: WorkflowStateManager) -> None:
    state = workflows.commit_transition("c", decision("discovery"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.active_workflow = "other"  # type: ignore[misc]
    assert isinstance(state.collected_data, tuple)
    assert isinstance(state.transition_history, tuple)


def test_repeated_reads_return_equal_state(workflows: WorkflowStateManager) -> None:
    workflows.commit_transition("c", decision("discovery", k="v"))
    assert workflows.get_state("c") == workflows.get_state("c")


# =============================================================================
# §7.8 persistence port
# =============================================================================
def test_the_store_protocol_is_structural() -> None:
    assert isinstance(InMemoryWorkflowStateStore(), WorkflowStateStore)


def test_a_custom_store_can_be_injected() -> None:
    class Counting(InMemoryWorkflowStateStore):
        def __init__(self) -> None:
            super().__init__()
            self.writes = 0

        def put(self, conversation_id: str, state: WorkflowState) -> None:
            self.writes += 1
            super().put(conversation_id, state)

    store = Counting()
    manager = WorkflowStateManager(store)
    manager.commit_transition("c", decision("discovery"))
    manager.commit_transition("c", decision("recommendation"))
    assert store.writes == 2


def test_the_default_store_is_in_memory() -> None:
    assert isinstance(WorkflowStateManager()._store, InMemoryWorkflowStateStore)  # noqa: SLF001


# =============================================================================
# §7.7 — a leaf module
# =============================================================================
def test_the_module_depends_on_no_other_runtime_module() -> None:
    package = REPO_ROOT / "runtime" / "workflow_state"
    allowed = ("runtime.models", "runtime.workflow_state")
    for path in package.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("from runtime", "import runtime")):
                continue
            module = stripped.split()[1]
            assert module.startswith(allowed), f"{path.name} imports {module}"


def test_the_manager_never_calls_a_provider() -> None:
    """§7.3: never calls an LLM provider."""
    package = REPO_ROOT / "runtime" / "workflow_state"
    for path in package.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        assert "runtime.provider" not in src
        for vendor in ("gemini", "openai", "anthropic"):
            assert vendor not in src.lower()


# =============================================================================
# seam — the real Prompt Assembler consumes what this module commits
# =============================================================================
@pytest.fixture(scope="module")
def real_context():
    from runtime.core_loader import CoreLoader, FilesystemCoreSource
    from runtime.loader import FilesystemProjectSource, ProjectLoader
    from runtime.resolver import Resolver

    core = CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()
    project = ProjectLoader(
        FilesystemProjectSource(REPO_ROOT / "projects")
    ).load("sunrise_dental_clinic")
    return core, Resolver().resolve(core, project)


def _assembler(core):
    from runtime.assembler import PromptAssembler
    from runtime.models.budget import BudgetSelection

    class Budget:
        def select(self, request):  # noqa: ARG002
            return BudgetSelection(knowledge_sections=(), history_window=())

    return PromptAssembler(core, token_budget=Budget())


def _conversation():
    from runtime.models.conversation import ConversationContext, Turn, TurnRole

    return ConversationContext(
        conversation_id="c",
        project_id="sunrise_dental_clinic",
        turns=(Turn(TurnRole.USER, "hello"),),
    )


def test_seam_committed_state_drives_the_real_assembler(real_context) -> None:
    from runtime.models.prompt_bundle import PromptSlot

    core, resolved = real_context
    manager = WorkflowStateManager()
    state = manager.commit_transition("c", decision("discovery"))

    bundle = _assembler(core).assemble(resolved, state, _conversation())
    workflow_section = bundle.section(PromptSlot.WORKFLOW)
    assert workflow_section is not None
    assert workflow_section.sources == ("core/workflows/discovery.md",)


def test_seam_a_fresh_conversation_assembles_with_no_workflow_slot(
    real_context,
) -> None:
    """D-4 in practice: no workflow is rendered until the Router routes."""
    from runtime.models.prompt_bundle import PromptSlot

    core, resolved = real_context
    state = WorkflowStateManager().get_state("c")
    bundle = _assembler(core).assemble(resolved, state, _conversation())
    assert bundle.section(PromptSlot.WORKFLOW) is None


def test_seam_d4_avoids_rendering_a_workflow_the_project_disabled(
    real_context,
) -> None:
    """Why D-4 matters, demonstrated against the real Assembler.

    The Assembler checks only that an active workflow exists in `CoreBundle` —
    not that the project enabled it. Had this module defaulted to Discovery, a
    project that enabled only `consultation` would have had Discovery rendered
    into its prompt. Starting at None means nothing is rendered until the Router
    chooses, and the Router does see the project's configuration.
    """
    from runtime.models.prompt_bundle import PromptSlot

    core, resolved = real_context
    restricted = dataclasses.replace(
        resolved,
        config=dataclasses.replace(resolved.config, enabled_workflows=("consultation",)),
    )
    assembler = _assembler(core)

    fresh = WorkflowStateManager().get_state("c")
    assert fresh.active_workflow is None
    assert assembler.assemble(restricted, fresh, _conversation()).section(
        PromptSlot.WORKFLOW
    ) is None

    # and the hazard the default would have created is real
    forced = WorkflowState(conversation_id="c", active_workflow="discovery")
    assert assembler.assemble(restricted, forced, _conversation()).section(
        PromptSlot.WORKFLOW
    ) is not None


def test_seam_session_and_workflow_state_key_on_the_same_conversation_id() -> None:
    from runtime.models.conversation import Turn, TurnRole
    from runtime.session import SessionManager

    sessions = SessionManager()
    workflows = WorkflowStateManager()
    sessions.create_session("conv-9", project_id="sunrise_dental_clinic")
    sessions.append_turn("conv-9", Turn(TurnRole.USER, "hi"))
    workflows.commit_transition("conv-9", decision("discovery"))

    assert sessions.get_context("conv-9").conversation_id == (
        workflows.get_state("conv-9").conversation_id
    )
