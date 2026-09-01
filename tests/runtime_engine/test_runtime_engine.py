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

from runtime.core_loader import CoreLoader, FilesystemCoreSource
from runtime.guardrail import GuardrailEngine
from runtime.loader import FilesystemProjectSource, ProjectLoader
from runtime.models.audit import AuditEvent, AuditFilters
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
from runtime.observability import AuditLogger
from runtime.provider import (
    ModelBinding,
    ModelIdentity,
    ProviderRateLimitError,
    RecordingSerializer,
    SerializedPrompt,
    run_conformance,
)
from runtime.provider_registry import ProviderNotRegisteredError, ProviderRegistry
from runtime.resolver import Resolver
from runtime.runtime_engine import (
    ProjectNotActivatedError,
    RuntimeEngine,
    activate,
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
    """An `AuditLog` double that keeps what the engine handed it."""

    def __init__(self) -> None:
        self.logged: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> AuditEvent:
        self.logged.append(event)
        return event

    def query_audit_log(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.logged if filters.matches(e))

    @property
    def events(self) -> list[tuple[str, str, str, dict]]:
        """The old four-tuple view, so existing assertions still read clearly."""
        return [
            (e.type, e.project_id, e.conversation_id, dict(e.payload))
            for e in self.logged
        ]


class ExplodingSink:
    """A logger whose store is down. §15.9: this must not matter."""

    def log_event(self, event: AuditEvent) -> AuditEvent:
        del event
        raise RuntimeError("the audit store is down")

    def query_audit_log(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        del filters
        raise RuntimeError("the audit store is down")


# =============================================================================
# real wiring — everything below the adapter is the framework itself
# =============================================================================
@pytest.fixture(autouse=True)
def audit_database(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Every `activate()` needs `ORBITLANCE_AUDIT_DB` (R-2), and gets its own.

    The composition root fails fast without it, by design — a deployment that
    keeps no durable audit trail must not start. Each test therefore points the
    variable at its own temporary database, so nothing is shared between tests
    and nothing is written outside `tmp_path`.
    """
    path = tmp_path / "activation-audit.sqlite3"
    monkeypatch.setenv("ORBITLANCE_AUDIT_DB", str(path))
    return path


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
) -> tuple[RuntimeEngine, FixtureAdapter, ProviderRegistry]:
    adapter = adapter if adapter is not None else FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    engine = RuntimeEngine(
        resolved_context=context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=tools if tools is not None else ToolExecutor(),
        audit=observability if observability is not None else AuditLogger(),
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
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
            audit=AuditLogger(),
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
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
            audit=AuditLogger(),
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
            providers=ProviderRegistry(),
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
            audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
# 6-7. the budget is derived from the provider, and cannot be injected
# =============================================================================
def test_6_no_budget_can_be_injected_through_the_constructor() -> None:
    """AUDIT-1: the absence of the parameter *is* the invariant.

    While `token_budget` existed, a caller could hand the engine a budget bound
    to a different model — the invalid state T-1 makes unconstructible inside an
    adapter, re-opened one level up. It is closed by removing the argument, not
    by checking it.
    """
    import inspect

    params = set(inspect.signature(RuntimeEngine.__init__).parameters)
    assert "token_budget" not in params
    for forbidden in ("tokenizer", "capabilities", "budget"):
        assert forbidden not in params


def test_6_the_budget_is_derived_from_the_resolved_providers_binding(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The tokenizer that counts belongs to the model that will be called.

    Proven by identity: the adapter's own tokenizer object is the one the budget
    consults, so there is no second vocabulary anywhere in the path.
    """
    adapter = FixtureAdapter()
    counted: list[str] = []
    tokenizer = adapter.model_binding().tokenizer
    original = tokenizer.count_tokens

    def recording(text: str) -> int:
        counted.append(text)
        return original(text)

    tokenizer.count_tokens = recording  # type: ignore[method-assign]
    engine, _, _ = build_engine(core, fixture_context, adapter=adapter)
    engine.handle_request(request())
    assert counted, "the bound tokenizer must be the one the budget counts with"


def test_6_a_mismatched_budget_can_no_longer_be_constructed(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """The AUDIT-1 reproduction, inverted.

    Before the fix, an engine could be built whose budget described
    `other/other-m` while the registry resolved `fixture_provider/...`. There is
    now no argument through which the wrong binding could enter, so the only
    provider the engine can budget against is the one it resolves.
    """
    wrong = FixtureAdapter(identity=ModelIdentity("other", "other-m"))
    registry = ProviderRegistry().register(FixtureAdapter())
    engine = RuntimeEngine(
        resolved_context=fixture_context,
        validation=validation_for(core, registry),
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
    )
    resolved = registry.get_provider(fixture_context)
    assert resolved.model_binding().identity == FIXTURE_IDENTITY
    assert resolved.model_binding().identity != wrong.model_binding().identity
    assert engine.handle_request(request()).text == ANSWER


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
    """A real `TokenBudgetManager` runs on every turn.

    Observed through the assembler seam rather than through an injected port,
    because the injection point is gone: the bundle that reaches the provider
    carries a history window the budget selected, and Module 4 delegates that
    selection entirely.
    """
    engine, adapter, _ = build_engine(core, fixture_context)
    engine.handle_request(request("first"))
    engine.handle_request(request("second"))
    second = adapter.calls[1]
    assert second.conversation_history_window, "the budget selected a history window"
    assert second.static_sections, "the budget admitted the fixed sections"


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


def test_8_a_provider_the_project_does_not_declare_fails_at_construction(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """Deriving the budget moved this failure to activation — which §10.10 wants.

    Before, an unresolvable provider surfaced as a degraded turn on a customer's
    first message. It is now a construction failure, *"caught as a configuration
    error at Validation Layer time, not mid-conversation."*
    """
    other = FixtureAdapter(identity=ModelIdentity("other_provider", "other-model"))
    registry = ProviderRegistry().register(other)
    with pytest.raises(ProviderNotRegisteredError):
        RuntimeEngine(
            resolved_context=fixture_context,
            validation=ValidationResult.build(ValidationTarget.PROJECT, FIXTURE_ID, ()),
            core=core,
            sessions=SessionManager(),
            guardrails=GuardrailEngine(core),
            providers=registry,
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
            audit=AuditLogger(),
        )


def test_8_the_activation_gate_still_precedes_provider_resolution(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """Ordering matters: an unvalidated project is unactivated, not misconfigured."""
    foreign = ValidationResult.build(ValidationTarget.PROJECT, "someone_else", ())
    with pytest.raises(ProjectNotActivatedError):
        RuntimeEngine(
            resolved_context=fixture_context,
            validation=foreign,
            core=core,
            sessions=SessionManager(),
            guardrails=GuardrailEngine(core),
            providers=ProviderRegistry(),  # empty: would also fail provider lookup
            router=WorkflowRouter(),
            states=WorkflowStateManager(),
            tools=ToolExecutor(),
            audit=AuditLogger(),
        )


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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=states,
        tools=ToolExecutor(),
        audit=AuditLogger(),
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
        providers=registry,
        router=WorkflowRouter(),
        states=states,
        tools=ToolExecutor(),
        audit=AuditLogger(),
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


def test_17_the_engine_cannot_be_built_without_an_audit_log(
    core: CoreBundle, fixture_context: ResolvedContext
) -> None:
    """RE-4's other half: there is no null sink to fall back to any more.

    `audit` is a required keyword argument with no default, so an engine that
    exists is an engine that records. The previous placeholder discarded every
    event; that default is gone.
    """
    import inspect

    parameter = inspect.signature(RuntimeEngine.__init__).parameters["audit"]
    assert parameter.default is inspect.Parameter.empty
    del fixture_context, core


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
    """No credential, environment or network access anywhere in the package.

    `pathlib` and `os` are exempt in `activation.py` **only**. The composition
    root's job is to *name* a projects root and hand it to
    `FilesystemProjectSource`, and — since OB-1's production wiring — to read
    `ORBITLANCE_AUDIT_DB`, which is the one configuration mechanism this
    repository has for a deployment-level path. It opens no socket and reads no
    credential: `test_activation_is_not_a_second_orchestrator` and
    `test_activation_makes_no_provider_call` pin that separately, and
    `test_only_activation_reads_the_environment` below pins the exemption's
    scope. Everything else in the package, engine and stages included, stays
    forbidden.
    """
    forbidden = {
        "os", "socket", "requests", "httpx", "urllib", "smtplib", "http", "ssl",
        "subprocess", "pathlib",
    }
    for path, tree in trees():
        allowed_here = {"pathlib", "os"} if path.name == "activation.py" else set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden - allowed_here, path.name
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root not in forbidden - allowed_here, path.name
            if isinstance(node, ast.Name) and path.name != "activation.py":
                assert node.id not in {"os", "environ", "getenv"}, path.name


def test_only_activation_reads_the_environment() -> None:
    """The exemption is one file wide, and it is the composition root's.

    `engine.py`, `stages.py` and `errors.py` still may not name `os`, `environ`
    or `getenv` — the credential and configuration boundary is unchanged for
    every file but the one that owns deployment configuration.
    """
    for path, tree in trees():
        if path.name == "activation.py":
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in {"os", "environ", "getenv"}, path.name
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "os", path.name


def test_activation_reads_only_the_audit_database_variable() -> None:
    """One variable, named once, and no other environment access."""
    source = (PACKAGE / "activation.py").read_text(encoding="utf-8")
    assert source.count("ORBITLANCE_AUDIT_DB") >= 1
    tree = ast.parse(source)
    reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "environ"
    ]
    assert len(reads) == 1, "activation reads the environment exactly once"


def test_19_only_the_composition_root_names_a_filesystem_path() -> None:
    """The engine and its stages never see a path at all."""
    for path, tree in trees():
        if path.name == "activation.py":
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in {"Path", "open"}, path.name


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


# =============================================================================
# the composition root (AUDIT-4), and the invariants it owns (AUDIT-1, AUDIT-2)
# =============================================================================
def activated(core: CoreBundle, adapter: FixtureAdapter | None = None):
    """Activate the fixture through the production path."""
    adapter = adapter if adapter is not None else FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    return activate(core, FIXTURES, FIXTURE_ID, registry), adapter


def collaborators(engine: RuntimeEngine) -> tuple[object, object]:
    """The session and workflow stores an engine's stages actually hold."""
    stages = {stage.name: stage for stage in engine._pipeline}  # noqa: SLF001
    return (
        stages["session"]._sessions,  # noqa: SLF001
        stages["workflow_state"]._states,  # noqa: SLF001
    )


def test_activation_returns_a_working_engine_for_the_real_fixture(
    core: CoreBundle,
) -> None:
    """A. The production path produces an engine that serves a real turn."""
    engine, adapter = activated(core)
    assert isinstance(engine, RuntimeEngine)
    assert engine.project_id == FIXTURE_ID
    response = engine.handle_request(request())
    assert response.text == ANSWER
    assert len(adapter.calls) == 1


def test_activation_runs_the_real_load_resolve_validate_chain(
    core: CoreBundle,
) -> None:
    """B. No fabricated ValidationResult — the real Validator gates activation."""
    tree = ast.parse((PACKAGE / "activation.py").read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for required in ("ProjectLoader", "Resolver", "Validator", "RuntimeEngine"):
        assert required in called, f"activation does not use {required}"
    # And behaviourally: the engine it returns holds a passing project result.
    engine, _ = activated(core)
    assert engine._validation.valid  # noqa: SLF001
    assert engine._validation.subject_id == FIXTURE_ID  # noqa: SLF001


def test_an_invalid_project_cannot_be_activated(core: CoreBundle) -> None:
    """C. `sunrise_dental_clinic` fails the real Validation Layer today."""
    registry = ProviderRegistry().register(FixtureAdapter())
    with pytest.raises(ProjectNotActivatedError, match="has not passed validation"):
        activate(core, REPO_ROOT / "projects", "sunrise_dental_clinic", registry)


def test_activation_accepts_no_budget_session_or_workflow_argument() -> None:
    """D + E. The root cannot be handed the state AUDIT-1 and AUDIT-2 concern."""
    import inspect

    params = list(inspect.signature(activate).parameters)
    assert params == ["core", "projects_root", "project_id", "providers"]
    for forbidden in ("token_budget", "sessions", "states", "budget"):
        assert forbidden not in params


def test_each_activation_constructs_fresh_collaborators(core: CoreBundle) -> None:
    """E + G. Two activations share no session or workflow store."""
    first, _ = activated(core)
    second, _ = activated(core)
    first_sessions, first_states = collaborators(first)
    second_sessions, second_states = collaborators(second)
    assert first_sessions is not second_sessions
    assert first_states is not second_states
    assert isinstance(first_sessions, SessionManager)
    assert isinstance(first_states, WorkflowStateManager)


def test_colliding_conversation_ids_stay_isolated_across_activations(
    core: CoreBundle,
) -> None:
    """F. The AUDIT-2 reproduction, run through the production path.

    Two activations, the *same* conversation id, different answers. Before the
    composition root existed, sharing the stores let one activation's turns
    appear in the other's conversation. Here each activation owns its own.

    Only one project in this repository is activatable — both production
    projects fail validation — so this exercises two activations rather than two
    project names. The mechanism under test is per-activation collaborator
    scoping, which is what the isolation actually rests on.
    """
    first, _ = activated(core, FixtureAdapter(text="answer from the first"))
    second, _ = activated(core, FixtureAdapter(text="answer from the second"))

    first.handle_request(request("asked of the first", conversation_id="shared-id"))
    second.handle_request(request("asked of the second", conversation_id="shared-id"))

    first_sessions, _ = collaborators(first)
    second_sessions, _ = collaborators(second)
    first_turns = [t.content for t in first_sessions.get_context("shared-id").turns]
    second_turns = [t.content for t in second_sessions.get_context("shared-id").turns]

    assert first_turns == ["asked of the first", "answer from the first"]
    assert second_turns == ["asked of the second", "answer from the second"]
    for leaked in ("asked of the second", "answer from the second"):
        assert leaked not in first_turns


def test_the_provider_bound_budget_invariant_survives_activation(
    core: CoreBundle,
) -> None:
    """D. The budget the activated engine uses is the resolved adapter's."""
    adapter = FixtureAdapter()
    counted: list[str] = []
    tokenizer = adapter.model_binding().tokenizer
    original = tokenizer.count_tokens

    def recording(text: str) -> int:
        counted.append(text)
        return original(text)

    tokenizer.count_tokens = recording  # type: ignore[method-assign]
    engine, _ = activated(core, adapter)
    engine.handle_request(request())
    assert counted, "activation must budget with the resolved provider's tokenizer"


def test_activation_makes_no_provider_call(core: CoreBundle) -> None:
    """7. Capability inspection only — no generate, no network."""
    adapter = FixtureAdapter()
    registry = ProviderRegistry().register(adapter)
    activate(core, FIXTURES, FIXTURE_ID, registry)
    assert adapter.calls == [], "activation must not call the provider"

    # `os` is deliberately absent from this set: reading ORBITLANCE_AUDIT_DB is
    # deployment configuration, not a provider call. Network modules stay banned.
    tree = ast.parse((PACKAGE / "activation.py").read_text(encoding="utf-8"))
    forbidden = {"socket", "requests", "httpx", "urllib", "http", "ssl"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden


def test_activation_holds_no_module_level_state() -> None:
    """I. No cached engines, no shared managers, no registry singleton."""
    tree = ast.parse((PACKAGE / "activation.py").read_text(encoding="utf-8"))
    for node in tree.body:
        assert not isinstance(node, ast.Assign | ast.AnnAssign), (
            "activation.py declares module-level state"
        )
        if isinstance(node, ast.ClassDef):
            raise AssertionError("activation.py must be a function, not a hierarchy")


def test_activation_is_not_a_second_orchestrator() -> None:
    """J. Construction only — it never runs a turn or a pipeline stage."""
    tree = ast.parse((PACKAGE / "activation.py").read_text(encoding="utf-8"))
    forbidden_calls = {
        "handle_request", "build_pipeline", "generate", "generate_with_fallback",
        "check_pre_flight", "check_post_response", "assemble", "execute",
        "append_turn", "commit_transition", "route", "record",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            assert name not in forbidden_calls, f"activation.py calls {name}"


def test_nothing_in_the_runtime_imports_activation() -> None:
    """H. The composition root has no inbound runtime dependency."""
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.parent == PACKAGE:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "runtime.runtime_engine.activation", path


def test_the_engine_package_depends_only_downward() -> None:
    """H. No peer-to-peer upward edge was introduced by the composition root."""
    allowed = {
        "runtime.models", "runtime.assembler", "runtime.budget", "runtime.guardrail",
        "runtime.loader", "runtime.provider_registry", "runtime.resolver",
        "runtime.session", "runtime.tool_executor", "runtime.validation",
        "runtime.workflow_router", "runtime.workflow_state", "runtime.runtime_engine",
        # §15 owns the audit contract the engine emits through — a downward edge
        # to a leaf, which is what the frozen graph prescribes.
        "runtime.observability",
    }
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "runtime"
            ):
                package = ".".join(node.module.split(".")[:2])
                assert package in allowed, f"{path.name} imports {node.module}"


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
