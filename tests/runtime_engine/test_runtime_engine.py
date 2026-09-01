"""Runtime Engine tests — specification §14.

**This file carries the integration coverage the repository did not previously
have.** Every other suite tests one module, or a cluster of two or three; none
connected the assembly half of the runtime to the provider half. The pipeline
below runs the *real* Core Loader, Project Loader, Resolver, Validator, Session
Manager, Guardrail Engine, Prompt Assembler, Token Budget Manager, Provider
Registry, Workflow Router, Workflow State Manager and Tool Executor against a
real project on disk.

Exactly one thing is a double: the provider adapter. It has to be — a real one
needs a credential and a network, and this suite runs offline. It is a
*conforming* double, satisfying `ProviderInterface`, `ModelBoundProvider` and
`PromptInspectable`, and the conformance suite is run against it here so it
cannot quietly drift into something no real adapter could be.

Tests are labelled: a docstring citing a clause asserts a **frozen
requirement**; one marked *implementation decision* asserts a choice made under
the system owner's rulings, which §14 does not state.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from runtime.assembler.ports import TokenBudgetPort
from runtime.budget import TokenBudgetManager
from runtime.core_loader import CoreLoader, FilesystemCoreSource
from runtime.guardrail import GuardrailEngine
from runtime.loader import FilesystemProjectSource, ProjectLoader
from runtime.models.conversation import TurnRole
from runtime.models.core_bundle import CoreBundle
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import (
    ProviderCapabilities,
    ProviderMetadata,
    ProviderResponse,
)
from runtime.models.resolved_context import ResolvedContext
from runtime.models.runtime import RuntimeRequest, RuntimeResponse
from runtime.models.tool import ToolRequest, ToolResponse
from runtime.models.validation import ValidationResult, ValidationTarget
from runtime.provider import (
    ModelBinding,
    ModelIdentity,
    ProviderRateLimitError,
    RecordingSerializer,
    SerializedPrompt,
    run_conformance,
)
from runtime.provider_registry import ProviderRegistry
from runtime.resolver import Resolver
from runtime.runtime_engine import (
    NullObservabilitySink,
    ProjectNotActivatedError,
    RuntimeEngine,
)
from runtime.session import SessionManager
from runtime.tool_executor import ToolExecutor
from runtime.validation import Validator
from runtime.workflow_router import WorkflowRouter
from runtime.workflow_state import WorkflowStateManager

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "runtime" / "runtime_engine"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "projects"
FIXTURE_ID = "fixture_clinic"

#: The identity the fixture's config.md declares. Not a vendor.
FIXTURE_IDENTITY = ModelIdentity("fixture_provider", "fixture-model-1")

ANSWER = "We offer routine examinations and hygiene appointments."


# =============================================================================
# the one double: a conforming, offline provider adapter
# =============================================================================
class FixtureTokenizer:
    def __init__(self, identity: ModelIdentity) -> None:
        self._identity = identity

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def model_identity(self) -> ModelIdentity:
        return self._identity


class FixtureAdapter:
    """A `ProviderInterface` bound to the fixture's declared identity.

    Conforming rather than convenient: it honours C-1a's fail-closed payload
    assertion and P-1's authoritative-history rule, and `run_conformance` is
    executed against it below.
    """

    def __init__(
        self,
        *,
        identity: ModelIdentity = FIXTURE_IDENTITY,
        window: int = 100_000,
        reserve: int = 64,
        text: str = ANSWER,
        fail_with: Exception | None = None,
    ) -> None:
        self._binding = ModelBinding(
            identity=identity,
            capabilities=ProviderCapabilities(window, reserve),
            tokenizer=FixtureTokenizer(identity),
        )
        self._text = text
        self._fail_with = fail_with
        self._last: SerializedPrompt | None = None
        self.calls: list[PromptBundle] = []

    def get_capabilities(self) -> ProviderCapabilities:
        return self._binding.capabilities

    def model_binding(self) -> ModelBinding:
        return self._binding

    def last_serialized_prompt(self) -> SerializedPrompt | None:
        return self._last

    def generate(self, prompt_bundle: PromptBundle, history) -> ProviderResponse:  # noqa: ANN001, ARG002
        # P-1: the bundle's window is the only authoritative history.
        snapshot = RecordingSerializer().record(prompt_bundle)
        caps = self._binding.capabilities
        cost = sum(
            self._binding.tokenizer.count_tokens(text) for text in snapshot.all_texts
        )
        if cost + caps.serialization_reserve > caps.context_window:
            from runtime.provider import ContextWindowExceededError

            raise ContextWindowExceededError(f"{cost} tokens exceeds the window")
        if self._fail_with is not None:
            raise self._fail_with
        self.calls.append(prompt_bundle)
        self._last = snapshot
        return ProviderResponse(
            text=self._text,
            metadata=ProviderMetadata(model=self._binding.identity.model_id),
        )


class AdapterCapabilities:
    """Bridges an adapter's capabilities onto Module 5's port."""

    def __init__(self, adapter: FixtureAdapter) -> None:
        self._adapter = adapter

    def capabilities(self) -> ProviderCapabilities:
        return self._adapter.get_capabilities()


class RecordingSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, str, dict]] = []

    def record(self, event_type, project_id, conversation_id, payload) -> None:  # noqa: ANN001
        self.events.append((event_type, project_id, conversation_id, dict(payload)))


class ExplodingSink:
    def record(self, event_type, project_id, conversation_id, payload) -> None:  # noqa: ANN001
        del event_type, project_id, conversation_id, payload
        raise RuntimeError("the audit store is down")


# =============================================================================
# real wiring — everything below the adapter is the framework itself
# =============================================================================
@pytest.fixture(scope="module")
def core() -> CoreBundle:
    return CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()


@pytest.fixture(scope="module")
def fixture_context(core: CoreBundle) -> ResolvedContext:
    project = ProjectLoader(FilesystemProjectSource(FIXTURES)).load(FIXTURE_ID)
    return Resolver().resolve(core, project)


def validation_for(core: CoreBundle, registry: ProviderRegistry) -> ValidationResult:
    """The real Validation Layer, with the real registry as its collaborator."""
    project = ProjectLoader(FilesystemProjectSource(FIXTURES)).load(FIXTURE_ID)
    return Validator(provider_registry=registry).validate_project(project, core)


def build_engine(
    core: CoreBundle,
    context: ResolvedContext,
    *,
    adapter: FixtureAdapter | None = None,
    observability=None,
    tools: ToolExecutor | None = None,
    token_budget: TokenBudgetPort | None = None,
) -> tuple[RuntimeEngine, FixtureAdapter, ProviderRegistry]:
    adapter = adapter if adapter is not None else FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    budget = token_budget or TokenBudgetManager(
        tokenizer=adapter.model_binding().tokenizer,
        capabilities=AdapterCapabilities(adapter),
    )
    engine = RuntimeEngine(
        resolved_context=context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        token_budget=budget,
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=tools if tools is not None else ToolExecutor(),
        observability=observability,
    )
    return engine, adapter, registry


def request(message: str = "What do you offer?", **kw) -> RuntimeRequest:
    return RuntimeRequest(
        project_id=kw.pop("project_id", FIXTURE_ID),
        conversation_id=kw.pop("conversation_id", "conv-1"),
        message=message,
        channel=kw.pop("channel", "web"),
    )


def source_files() -> list[pathlib.Path]:
    return sorted(PACKAGE.glob("*.py")) + [REPO_ROOT / "runtime" / "models" / "runtime.py"]


def trees() -> list[tuple[pathlib.Path, ast.Module]]:
    return [(p, ast.parse(p.read_text(encoding="utf-8"))) for p in source_files()]


# =============================================================================
# 20. the complete offline pipeline, RuntimeRequest -> RuntimeResponse
# =============================================================================
def test_20_the_whole_pipeline_runs_offline_on_the_real_fixture(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The seam the repository lacked: resolved project -> assembler -> budget
    -> registry -> provider -> guardrail -> RuntimeResponse, with real modules."""
    engine, adapter, _ = build_engine(core, fixture_context)
    response = engine.handle_request(request())

    assert isinstance(response, RuntimeResponse)
    assert response.text == ANSWER
    assert not response.blocked
    assert not response.degraded
    assert response.delivered
    assert len(adapter.calls) == 1


def test_20_the_bundle_that_reached_the_provider_carries_real_project_content(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    engine, adapter, _ = build_engine(core, fixture_context)
    engine.handle_request(request())
    bundle = adapter.calls[0]
    assert bundle.project_id == FIXTURE_ID
    assert bundle.latest_message == "What do you offer?"
    rendered = "\n".join(section.content for section in bundle.static_sections)
    assert "Fixture Clinic" in rendered


def test_20_a_second_turn_carries_the_first_turns_history(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    engine, adapter, _ = build_engine(core, fixture_context)
    engine.handle_request(request("first question"))
    engine.handle_request(request("second question"))
    second = adapter.calls[1]
    assert second.latest_message == "second question"
    contents = [turn.content for turn in second.conversation_history_window]
    assert "first question" in contents
    assert ANSWER in contents


def test_20_the_fake_adapter_passes_the_real_conformance_suite() -> None:
    """So the one double in this suite cannot drift into an impossible adapter."""
    report = run_conformance(FixtureAdapter())
    assert report.passed, report.failures


# =============================================================================
# 1-2. activation gate (§14.10)
# =============================================================================
def test_1_the_fixture_project_passes_activation(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.10: a passed ValidationResult is a hard precondition."""
    registry = ProviderRegistry().register(FixtureAdapter())
    result = validation_for(core, registry)
    assert result.valid
    assert result.issues == ()
    engine, _, _ = build_engine(core, fixture_context)
    assert engine.project_id == FIXTURE_ID


def test_2_an_invalid_project_cannot_construct_an_engine(core: CoreBundle) -> None:
    """The real sunrise project fails validation; no engine may exist for it."""
    project = ProjectLoader(FilesystemProjectSource(REPO_ROOT / "projects")).load(
        "sunrise_dental_clinic"
    )
    real_context = Resolver().resolve(core, project)
    invalid = Validator(
        provider_registry=ProviderRegistry().register(FixtureAdapter())
    ).validate_project(project, core)
    assert not invalid.valid

    with pytest.raises(ProjectNotActivatedError, match="has not passed validation"):
        RuntimeEngine(
            resolved_context=real_context,
            validation=invalid,
            core=core,
            sessions=SessionManager(),
            guardrails=GuardrailEngine(core),
            token_budget=TokenBudgetManager(
                tokenizer=FixtureTokenizer(FIXTURE_IDENTITY),
                capabilities=AdapterCapabilities(FixtureAdapter()),
            ),
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
        )


def test_2_a_validation_result_for_another_project_is_refused(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """Two projects must never be assembled into one engine."""
    foreign = ValidationResult.build(ValidationTarget.PROJECT, "someone_else", ())
    assert foreign.valid
    with pytest.raises(ProjectNotActivatedError, match="two different projects"):
        RuntimeEngine(
            resolved_context=fixture_context,
            validation=foreign,
            core=core,
            sessions=SessionManager(),
            guardrails=GuardrailEngine(core),
            token_budget=TokenBudgetManager(
                tokenizer=FixtureTokenizer(FIXTURE_IDENTITY),
                capabilities=AdapterCapabilities(FixtureAdapter()),
            ),
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
        )


def test_2_a_core_validation_result_is_refused(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.10 admits only a project result; a Core one proves nothing about it."""
    core_result = Validator().validate_core(core)
    with pytest.raises(ProjectNotActivatedError, match="project ValidationResult"):
        RuntimeEngine(
            resolved_context=fixture_context,
            validation=core_result,
            core=core,
            sessions=SessionManager(),
            guardrails=GuardrailEngine(core),
            token_budget=TokenBudgetManager(
                tokenizer=FixtureTokenizer(FIXTURE_IDENTITY),
                capabilities=AdapterCapabilities(FixtureAdapter()),
            ),
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
        )


def test_2_handle_request_never_re_runs_validation() -> None:
    """§14.2: activation is decided at deploy time, not on every message."""
    tree = ast.parse((PACKAGE / "engine.py").read_text(encoding="utf-8"))
    handler = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "handle_request"
    )
    for node in ast.walk(handler):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"validate_project", "validate_core"}


# =============================================================================
# 3. cross-project identity fails closed
# =============================================================================
def test_3_a_foreign_project_id_is_refused_before_any_provider_call(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """Implementation decision: a §14-local boundary check. TE-7 stays open."""
    engine, adapter, _ = build_engine(core, fixture_context)
    response = engine.handle_request(request(project_id="another_clinic"))
    assert response.degraded
    assert not response.blocked
    assert adapter.calls == [], "no provider call may happen for a foreign project"


def test_3_the_refusal_is_recorded(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    sink = RecordingSink()
    engine, _, _ = build_engine(core, fixture_context, observability=sink)
    engine.handle_request(request(project_id="another_clinic"))
    assert sink.events[0][0] == "runtime.request_rejected"


# =============================================================================
# 4. real Session Manager
# =============================================================================
def test_4_the_user_turn_survives_a_provider_failure(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§12's contract: the user turn is appended first, so a failure cannot lose it."""
    sessions = SessionManager()
    adapter = FixtureAdapter(fail_with=RuntimeError("down"))
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=sessions,
        guardrails=GuardrailEngine(core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    assert engine.handle_request(request("remember me")).degraded
    turns = sessions.get_context("conv-1").turns
    assert [t.content for t in turns] == ["remember me"]


def test_4_both_turns_are_recorded_on_a_successful_turn(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    sessions = SessionManager()
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=sessions,
        guardrails=GuardrailEngine(core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    engine.handle_request(request("hello"))
    turns = sessions.get_context("conv-1").turns
    assert [t.role for t in turns] == [TurnRole.USER, TurnRole.AGENT]
    assert turns[0].content == "hello"
    assert turns[1].content == ANSWER


# =============================================================================
# 5. pre-flight guardrail is called and can short-circuit
# =============================================================================
def test_5_the_pre_flight_guardrail_runs_on_every_turn(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    calls: list[str] = []

    class Watching(GuardrailEngine):
        def check_pre_flight(self, message, resolved_context):
            calls.append(message)
            return super().check_pre_flight(message, resolved_context)

    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=Watching(core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    engine.handle_request(request("hello"))
    assert calls == ["hello"]


def test_5_a_pre_flight_block_short_circuits_before_the_provider(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.12(b): assert the provider was never invoked.

    Driven by the real Guardrail Engine's real fail-closed path — an empty Core
    guardrails bundle — rather than by a stubbed verdict.
    """
    empty_core = CoreBundle()
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(empty_core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    response = engine.handle_request(request())
    assert response.blocked
    assert response.escalate
    assert response.text == ""
    assert adapter.calls == [], "the provider must never be reached after a block"


def test_5_both_guardrail_stages_are_present_and_ordered(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14: the composition mechanism must not allow omitting them."""
    engine, _, _ = build_engine(core, fixture_context)
    names = engine.stage_names
    assert "pre_flight_guardrail" in names
    assert "post_response_guardrail" in names
    assert names.index("pre_flight_guardrail") < names.index("provider")
    assert names.index("provider") < names.index("post_response_guardrail")


def test_5_the_pipeline_cannot_be_supplied_as_a_list() -> None:
    """There is no argument through which a guardrail stage could be dropped."""
    import inspect

    params = set(inspect.signature(RuntimeEngine.__init__).parameters)
    for forbidden in ("stages", "pipeline", "steps"):
        assert forbidden not in params


# =============================================================================
# 6-7. the budget is mandatory and actually exercised
# =============================================================================
def test_6_the_engine_cannot_be_constructed_without_a_budget() -> None:
    """Ruling D-1(b): Module 4's unbudgeted default stays, §14 never reaches it."""
    import inspect

    parameter = inspect.signature(RuntimeEngine.__init__).parameters["token_budget"]
    assert parameter.default is inspect.Parameter.empty


def test_6_no_engine_code_path_builds_an_unbudgeted_assembler() -> None:
    """Structural: every PromptAssembler(...) in this package passes a budget."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id != "PromptAssembler":
                    continue
                keywords = {kw.arg for kw in node.keywords}
                assert "token_budget" in keywords, f"{path.name} assembles unbudgeted"


def test_7_the_budget_is_actually_consulted(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    seen: list[str] = []
    real = TokenBudgetManager(
        tokenizer=FixtureTokenizer(FIXTURE_IDENTITY),
        capabilities=AdapterCapabilities(FixtureAdapter()),
    )

    class Recording:
        def select(self, budget_request):
            seen.append(budget_request.project_id)
            return real.select(budget_request)

    engine, _, _ = build_engine(core, fixture_context, token_budget=Recording())
    engine.handle_request(request())
    assert seen == [FIXTURE_ID]


def test_7_a_tight_window_changes_what_ships(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """Proof the budget is load-bearing, not decorative."""
    wide = FixtureAdapter(window=100_000)
    engine_wide, _, _ = build_engine(core, fixture_context, adapter=wide)
    engine_wide.handle_request(request())

    narrow = FixtureAdapter(window=400)
    engine_narrow, _, _ = build_engine(core, fixture_context, adapter=narrow)
    engine_narrow.handle_request(request())

    if narrow.calls:
        assert len(narrow.calls[0].static_sections) <= len(
            wide.calls[0].static_sections
        )


# =============================================================================
# 8-9. provider selection and the post-response guardrail
# =============================================================================
def test_8_the_provider_is_selected_for_the_activated_project(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The registry resolves the identity the fixture's config.md declares."""
    engine, adapter, registry = build_engine(core, fixture_context)
    engine.handle_request(request())
    assert registry.get_provider(fixture_context) is adapter
    assert adapter.model_binding().identity == FIXTURE_IDENTITY


def test_8_a_provider_the_project_does_not_declare_is_refused(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    other = FixtureAdapter(identity=ModelIdentity("other_provider", "other-model"))
    registry = ProviderRegistry().register(other)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=ValidationResult.build(ValidationTarget.PROJECT, FIXTURE_ID, ()),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        token_budget=TokenBudgetManager(
            tokenizer=other.model_binding().tokenizer,
            capabilities=AdapterCapabilities(other),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    response = engine.handle_request(request())
    assert response.degraded, "an unresolvable provider is contained, not raised"


def test_9_the_provider_response_reaches_the_post_response_guardrail(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    seen: list[str] = []

    class Watching(GuardrailEngine):
        def check_post_response(self, response, resolved_context):
            seen.append(response.text)
            return super().check_post_response(response, resolved_context)

    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=Watching(core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    engine.handle_request(request())
    assert seen == [ANSWER]


# =============================================================================
# 10-11. blocked and escalating responses
# =============================================================================
def test_10_a_post_response_block_produces_a_blocked_runtime_response(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The real price guardrail, driven by real fixture Knowledge.

    `$4,321` appears nowhere in the fixture's pricing document, so the Guardrail
    Engine blocks it as an invented business fact.
    """
    inventing = FixtureAdapter(text="A root canal is $4,321.")
    engine, _, _ = build_engine(core, fixture_context, adapter=inventing)
    response = engine.handle_request(request())
    assert response.blocked
    assert response.text == ""


def test_10_a_supported_price_is_not_blocked(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """$80 is genuinely published in the fixture's 06_pricing.md."""
    honest = FixtureAdapter(text="A routine examination is $80.")
    engine, _, _ = build_engine(core, fixture_context, adapter=honest)
    response = engine.handle_request(request())
    assert not response.blocked
    assert response.text == "A routine examination is $80."


def test_10_a_blocked_response_never_carries_text() -> None:
    with pytest.raises(ValueError, match="must not carry text"):
        RuntimeResponse(text="leaked", blocked=True)


def test_11_an_escalating_guardrail_sets_escalate(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The bundle-unavailable path escalates, and §14 carries that through."""
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(CoreBundle()),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
    response = engine.handle_request(request())
    assert response.blocked and response.escalate


# =============================================================================
# 12. contained failures become a safe degraded response
# =============================================================================
def test_12_a_provider_failure_is_contained(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.9: a lower-level exception never becomes a crash reaching the user."""
    engine, _, _ = build_engine(
        core,
        fixture_context,
        adapter=FixtureAdapter(fail_with=ProviderRateLimitError("throttled")),
    )
    response = engine.handle_request(request())
    assert response.degraded
    assert response.text == ""
    assert not response.blocked


def test_12_no_exception_text_reaches_the_customer(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """A vendor message is a known credential-bearing channel."""
    secret = "sk-abcdefghijklmnopqrstuvwx"  # noqa: S105 - fake, for the assertion
    engine, _, _ = build_engine(
        core, fixture_context, adapter=FixtureAdapter(fail_with=RuntimeError(secret))
    )
    response = engine.handle_request(request())
    assert secret not in repr(response)
    assert response.text == ""


def test_12_handle_request_never_raises(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    for failure in (RuntimeError("x"), ValueError("y"), KeyError("z")):
        engine, _, _ = build_engine(
            core, fixture_context, adapter=FixtureAdapter(fail_with=failure)
        )
        assert engine.handle_request(request()).degraded


def test_12_the_failing_stage_is_recorded_for_the_operator(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    sink = RecordingSink()
    engine, _, _ = build_engine(
        core,
        fixture_context,
        adapter=FixtureAdapter(fail_with=RuntimeError("down")),
        observability=sink,
    )
    engine.handle_request(request())
    event, _, _, payload = sink.events[0]
    assert event == "runtime.turn_degraded"
    assert payload["failed_stage"] == "provider"


# =============================================================================
# 13-14. the tool seam
# =============================================================================
def test_13_the_tool_stage_no_ops_when_there_is_no_tool_request(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """TE-1: nothing in this runtime produces a ToolRequest."""
    executed: list[ToolRequest] = []

    class Watching(ToolExecutor):
        def execute(self, tool_request, resolved_context):
            del resolved_context
            executed.append(tool_request)
            return ToolResponse(success=True)

    engine, _, _ = build_engine(core, fixture_context, tools=Watching())
    response = engine.handle_request(request())
    assert response.text == ANSWER
    assert executed == [], "the tool stage must not invent work to do"


def test_13_the_tool_stage_is_present_and_ordered_after_the_workflow(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.2 orders workflow routing/state commit *before* tool execution."""
    engine, _, _ = build_engine(core, fixture_context)
    names = engine.stage_names
    assert names.index("workflow") < names.index("tool")
    assert names.index("tool") < names.index("delivery")


def test_14_no_tool_request_is_ever_constructed() -> None:
    """Structural: §14 must not fabricate its own input for Module 11."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "ToolRequest", f"{path.name} builds one"


def test_14_no_tool_is_inferred_from_workflow_or_markdown() -> None:
    parsing = {"raw_text", "splitlines", "findall", "search", "compile"}
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in parsing, f"{path.name} parses text"
            if isinstance(node, ast.Name):
                assert node.id != "re", path.name


# =============================================================================
# 15. workflow transition is committed
# =============================================================================
def test_15_the_first_turn_commits_the_discovery_transition(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    states = WorkflowStateManager()
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=states,
        tools=ToolExecutor(),
    )
    engine.handle_request(request())
    assert states.get_state("conv-1").active_workflow == "discovery"


def test_15_a_blocked_turn_commits_no_transition(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """A short-circuit stops the pipeline; nothing after it runs."""
    states = WorkflowStateManager()
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(CoreBundle()),
        token_budget=TokenBudgetManager(
            tokenizer=adapter.model_binding().tokenizer,
            capabilities=AdapterCapabilities(adapter),
        ),
        providers=registry,
        router=WorkflowRouter(),
        states=states,
        tools=ToolExecutor(),
    )
    engine.handle_request(request())
    assert states.get_state("conv-1").active_workflow is None


# =============================================================================
# 16-17. observability
# =============================================================================
def test_16_the_sink_is_invoked_once_per_turn(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    sink = RecordingSink()
    engine, _, _ = build_engine(core, fixture_context, observability=sink)
    engine.handle_request(request())
    assert len(sink.events) == 1
    event, project_id, conversation_id, payload = sink.events[0]
    assert event == "runtime.turn_completed"
    assert (project_id, conversation_id) == (FIXTURE_ID, "conv-1")
    assert payload["channel"] == "web"


def test_16_a_blocked_turn_is_still_recorded(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The turns most worth an audit record are the ones that did not complete."""
    sink = RecordingSink()
    inventing = FixtureAdapter(text="That costs $4,321.")
    engine, _, _ = build_engine(
        core, fixture_context, adapter=inventing, observability=sink
    )
    engine.handle_request(request())
    assert sink.events[0][0] == "runtime.turn_blocked"


def test_16_no_message_prompt_or_answer_is_ever_logged(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§15.3 forbids logging PII beyond an allowance nobody has written."""
    sink = RecordingSink()
    engine, _, _ = build_engine(core, fixture_context, observability=sink)
    engine.handle_request(request("my phone number is 555 0100"))
    payload = sink.events[0][3]
    joined = " ".join(payload.values())
    assert "555" not in joined
    assert ANSWER not in joined


def test_17_a_failing_sink_does_not_block_the_conversation(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§15.9: a logging failure is not a conversation failure."""
    engine, _, _ = build_engine(core, fixture_context, observability=ExplodingSink())
    response = engine.handle_request(request())
    assert response.text == ANSWER
    assert not response.degraded


def test_17_the_default_sink_records_nothing(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """RE-4: running on the default means keeping no audit trail."""
    engine, _, _ = build_engine(core, fixture_context)
    assert engine.handle_request(request()).text == ANSWER
    assert NullObservabilitySink().record("e", "p", "c", {}) is None


# =============================================================================
# 18-19. concurrency, credentials, network
# =============================================================================
def test_18_no_concurrency_machinery_exists() -> None:
    """RE-3: §14 establishes no concurrent runtime contract."""
    forbidden_modules = {"threading", "asyncio", "concurrent", "multiprocessing"}
    forbidden_attrs = {"Thread", "Lock", "RLock", "gather", "submit", "run_in_executor"}
    for path, tree in trees():
        for node in ast.walk(tree):
            assert not isinstance(node, ast.AsyncFunctionDef), path.name
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_modules, path.name
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden_modules
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden_attrs, path.name


def test_19_no_credentials_environment_or_network() -> None:
    forbidden = {
        "os", "socket", "requests", "httpx", "urllib", "smtplib", "http", "ssl",
        "subprocess", "pathlib",
    }
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, path.name
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden, path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"os", "environ", "getenv"}, path.name


def test_19_no_vendor_name_appears() -> None:
    for path in source_files():
        text = path.read_text(encoding="utf-8").casefold()
        for vendor in ("gemini", "google", "anthropic", "openai", "claude"):
            assert vendor not in text, f"{path.name} names {vendor}"


def test_19_the_engine_never_reads_provider_diagnostic_residue() -> None:
    """S-1: a shared adapter's `last_serialized_prompt` is not runtime state."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr != "last_serialized_prompt", path.name


# =============================================================================
# structure, models and recorded gaps
# =============================================================================
def test_the_runtime_response_has_exactly_the_ruled_four_fields() -> None:
    assert set(RuntimeResponse.__dataclass_fields__) == {
        "text",
        "blocked",
        "escalate",
        "degraded",
    }


def test_the_runtime_request_has_exactly_the_four_specified_fields() -> None:
    """§14.4: project_id, conversation_id, message, channel."""
    assert set(RuntimeRequest.__dataclass_fields__) == {
        "project_id",
        "conversation_id",
        "message",
        "channel",
    }


def test_both_runtime_models_are_frozen_with_slots() -> None:
    for model in (RuntimeRequest, RuntimeResponse):
        assert model.__dataclass_params__.frozen
        assert hasattr(model, "__slots__")


def test_the_pipeline_order_matches_the_frozen_sequence(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """§14.2's order, including workflow-before-tool."""
    engine, _, _ = build_engine(core, fixture_context)
    assert engine.stage_names == (
        "session",
        "workflow_state",
        "pre_flight_guardrail",
        "prompt_assembly",
        "provider",
        "post_response_guardrail",
        "workflow",
        "tool",
        "delivery",
    )


def test_nothing_in_the_runtime_imports_the_engine() -> None:
    """§14.7: nothing depends back on the root of the graph."""
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.is_relative_to(PACKAGE):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("runtime.runtime_engine"), (
                    f"{path} imports the Runtime Engine"
                )


@pytest.mark.parametrize(
    "issue", ["RE-1", "RE-2", "RE-3", "RE-4", "RE-5", "RE-6", "RE-7"]
)
def test_every_recorded_gap_is_in_the_register(issue: str) -> None:
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert issue in register


@pytest.mark.parametrize(
    "issue", ["TE-1", "TE-2", "TE-3", "TE-5", "TE-6", "TE-7", "PR-1", "V-5", "V-7", "R3-2"]
)
def test_no_prior_architecture_issue_was_silently_closed(issue: str) -> None:
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert issue in register
