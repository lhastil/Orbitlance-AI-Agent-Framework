"""Tool Executor tests — specification §11.

Covers the §11.12 scenarios that are implementable, and pins the ruled
decisions — including the ones expressed as *absences*: no retry, no timeout,
no Markdown parsing, no batching, no auto-discovery, no fabricated success.

**Two labels are used throughout, and they are not decoration.**

* Tests whose name or docstring cites a clause (§11.x) assert a **frozen
  requirement**.
* Tests marked *implementation decision* assert a choice made under the
  system owner's rulings for consistency and safety. §11 does not state them,
  and this file does not pretend otherwise.

Two §11.12 scenarios are **not** faked. (c) "retries per documented policy" has
no policy to retry per — the five contracts say only "retry when appropriate" —
so the tests below pin the *absence* of retry instead, and fail loudly the day
one appears without a policy behind it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from runtime.models.resolved_context import ResolvedContext
from runtime.models.tool import ToolErrorType, ToolRequest, ToolResponse
from runtime.tool_executor import DuplicateToolError, ToolExecutor, ToolPort

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "runtime" / "tool_executor"
MODEL_FILE = REPO_ROOT / "runtime" / "models" / "tool.py"

#: The five contracts §11.11 fixes as current. Transcribed from `core/tools/`
#: for use as test data only — this is a fixture, not a runtime constant.
CONTRACTS = ("crm", "calendar", "email", "consultation_form", "integrations")


class RecordingTool:
    """A `ToolPort` the test drives. Owns no credential and no client."""

    def __init__(self, response: ToolResponse | None = None) -> None:
        self.response = response if response is not None else ToolResponse(success=True)
        self.calls: list[tuple[ToolRequest, ResolvedContext]] = []

    def execute(
        self, tool_request: ToolRequest, resolved_context: ResolvedContext
    ) -> ToolResponse:
        self.calls.append((tool_request, resolved_context))
        return self.response


class RaisingTool:
    """Raises whatever it was given, as a real client eventually would."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error if error is not None else RuntimeError("upstream exploded")
        self.attempts = 0

    def execute(
        self, tool_request: ToolRequest, resolved_context: ResolvedContext
    ) -> ToolResponse:
        del tool_request, resolved_context
        self.attempts += 1
        raise self.error


def request(contract: str = "crm", **parameters: str) -> ToolRequest:
    return ToolRequest(
        tool_contract=contract,
        parameters=parameters,
        project_id="test_project",
        conversation_id="c1",
    )


def context() -> ResolvedContext:
    return ResolvedContext(project_id="test_project")


@pytest.fixture
def executor() -> ToolExecutor:
    return ToolExecutor()


def source_files() -> list[pathlib.Path]:
    return sorted(PACKAGE.glob("*.py")) + [MODEL_FILE]


def trees() -> list[tuple[pathlib.Path, ast.Module]]:
    return [(p, ast.parse(p.read_text(encoding="utf-8"))) for p in source_files()]


def docstring_nodes(tree: ast.Module) -> set[int]:
    """Ids of `Constant` nodes that are docstrings.

    Identity, not text: `ast.get_docstring` returns a *cleaned* string, so
    comparing a raw `Constant.value` against it never matches and would turn
    every scan below into a scan of nothing.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr):
            first = body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.add(id(first))
    return found


# =============================================================================
# 1. §11.12(a) — a configured tool executes and returns a normalised response
# =============================================================================
def test_a_a_configured_tool_executes(executor: ToolExecutor) -> None:
    tool = RecordingTool(ToolResponse(success=True, data={"contact_id": "42"}))
    executor.register("crm", tool)
    result = executor.execute(request("crm"), context())
    assert result.success
    assert result.data["contact_id"] == "42"
    assert result.error_type is None
    assert not result.capability_unavailable


def test_a_the_request_and_context_reach_the_tool_unchanged(
    executor: ToolExecutor,
) -> None:
    """§11.3: the executor executes what it is told, and edits nothing."""
    tool = RecordingTool()
    executor.register("email", tool)
    sent_request, sent_context = request("email", to="a@example.test"), context()
    executor.execute(sent_request, sent_context)
    seen_request, seen_context = tool.calls[0]
    assert seen_request is sent_request
    assert seen_context is sent_context


def test_a_the_tools_result_is_passed_through_unmodified(
    executor: ToolExecutor,
) -> None:
    returned = ToolResponse(success=True, data={"event_id": "e1"})
    executor.register("calendar", RecordingTool(returned))
    assert executor.execute(request("calendar"), context()) is returned


@pytest.mark.parametrize("contract", CONTRACTS)
def test_a_every_current_contract_can_be_served(
    executor: ToolExecutor, contract: str
) -> None:
    """§11.11 fixes the five current contracts; nothing here privileges any."""
    executor.register(contract, RecordingTool())
    assert executor.execute(request(contract), context()).success


# =============================================================================
# 2. §11.12(b) — an unconfigured contract declines without crashing
# =============================================================================
def test_b_an_unregistered_contract_is_capability_unavailable(
    executor: ToolExecutor,
) -> None:
    result = executor.execute(request("crm"), context())
    assert result.capability_unavailable
    assert not result.success
    assert result.error_type is ToolErrorType.CAPABILITY_UNAVAILABLE


@pytest.mark.parametrize("contract", [*CONTRACTS, "not_a_contract", ""])
def test_b_nothing_registered_never_raises(
    executor: ToolExecutor, contract: str
) -> None:
    """§11.9: 'rather than crashing' — for any name, known or not."""
    assert executor.execute(request(contract), context()).capability_unavailable


def test_b_an_unknown_contract_reaches_the_same_answer(
    executor: ToolExecutor,
) -> None:
    """A contract nothing serves is unavailable however the name arose.

    Implementation decision: §11 defines no separate 'unknown contract' outcome,
    and inventing one would require a canonical contract list this module is not
    permitted to import (§11.7 grants no edge to the Validation Layer).
    """
    executor.register("crm", RecordingTool())
    result = executor.execute(request("nonexistent"), context())
    assert result.capability_unavailable
    assert result.error_type is ToolErrorType.CAPABILITY_UNAVAILABLE


def test_b_availability_is_what_was_registered(executor: ToolExecutor) -> None:
    executor.register("email", RecordingTool())
    assert executor.is_available("email")
    assert not executor.is_available("crm")
    assert executor.registered_contracts() == frozenset({"email"})


# =============================================================================
# 3. Failure is surfaced on the first attempt — no retry (ruled)
# =============================================================================
def test_a_raising_tool_becomes_a_failed_response(executor: ToolExecutor) -> None:
    """§11.2 assigns normalisation here; §11.5 makes ToolResponse the output."""
    executor.register("crm", RaisingTool())
    result = executor.execute(request("crm"), context())
    assert not result.success
    assert result.error_type is ToolErrorType.EXECUTION_FAILED
    assert not result.capability_unavailable


def test_the_tool_is_called_exactly_once_on_failure(executor: ToolExecutor) -> None:
    """**No retry.** The five contracts say only 'retry when appropriate'.

    A retried side effect is a duplicated side effect — the same contracts
    forbid duplicate emails and duplicate CRM records. §11.12(c) is therefore
    unenforceable today; this pins the absence rather than faking the scenario.
    """
    tool = RaisingTool()
    executor.register("crm", tool)
    executor.execute(request("crm"), context())
    assert tool.attempts == 1


def test_a_failing_tool_result_is_not_retried_either(executor: ToolExecutor) -> None:
    calls = []

    class CountingTool:
        def execute(self, tool_request, resolved_context):  # noqa: ANN001, ARG002
            calls.append(1)
            return ToolResponse(success=False, error_type=ToolErrorType.TIMEOUT)

    executor.register("email", CountingTool())
    result = executor.execute(request("email"), context())
    assert calls == [1]
    assert result.error_type is ToolErrorType.TIMEOUT


def test_no_retry_machinery_exists_in_the_source() -> None:
    """Nothing loops, sleeps, backs off or counts attempts."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                raise AssertionError(f"{path.name} contains a loop over attempts")
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"sleep", "retry", "backoff"}, path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"sleep", "time", "retry", "backoff"}, path.name


def test_no_timeout_is_defined_or_enforced() -> None:
    """Ruled: the framework states no value, so this module enforces none."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name | ast.Attribute):
                name = node.id if isinstance(node, ast.Name) else node.attr
                assert name not in {"timeout", "timeout_seconds", "deadline"}, path.name
    assert "timeout" not in ToolRequest.__dataclass_fields__


# =============================================================================
# 4. §11.12(d) — no credential-bearing fields (structural/security)
# =============================================================================
def test_d_tool_request_has_exactly_the_frozen_four_fields() -> None:
    assert set(ToolRequest.__dataclass_fields__) == {
        "tool_contract",
        "parameters",
        "project_id",
        "conversation_id",
    }


def test_d_tool_response_has_exactly_the_frozen_four_fields() -> None:
    assert set(ToolResponse.__dataclass_fields__) == {
        "success",
        "data",
        "error_type",
        "capability_unavailable",
    }


def test_d_no_credential_shaped_field_exists_on_either_model() -> None:
    """§11.3 and the frozen ToolRequest row: 'never contains credentials'."""
    forbidden = {
        "api_key", "apikey", "key", "secret", "token", "password", "credential",
        "credentials", "auth", "authorization", "bearer",
    }
    for model in (ToolRequest, ToolResponse):
        for field_name in model.__dataclass_fields__:
            assert field_name.casefold() not in forbidden


def test_d_the_executor_never_reads_the_environment() -> None:
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "os", path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"os", "environ", "getenv"}, path.name


def test_d_a_raising_tool_leaks_no_exception_detail(executor: ToolExecutor) -> None:
    """A vendor exception's message is a known credential-bearing channel.

    Implementation decision under §11.3: nothing from the exception crosses into
    the ToolResponse — the frozen four-field model has no diagnostic channel
    anyway, and `data` is not repurposed as one. Recorded as TE-4.
    """
    secret = "sk-abcdefghijklmnopqrstuvwx"  # noqa: S105 - a fake, for the assertion
    executor.register("crm", RaisingTool(RuntimeError(f"auth failed for {secret}")))
    result = executor.execute(request("crm"), context())
    assert secret not in str(result.data)
    assert result.data == {}
    assert secret not in repr(result)


# =============================================================================
# 5-6. Registration (implementation decisions, not §11)
# =============================================================================
def test_duplicate_registration_is_rejected_and_the_original_survives(
    executor: ToolExecutor,
) -> None:
    """Implementation decision: §11 specifies no registration semantics."""
    original = RecordingTool(ToolResponse(success=True, data={"which": "first"}))
    executor.register("crm", original)
    with pytest.raises(DuplicateToolError, match="already served by"):
        executor.register("crm", RecordingTool())
    assert executor.execute(request("crm"), context()).data["which"] == "first"


def test_register_returns_self_so_registrations_chain() -> None:
    executor = ToolExecutor()
    assert executor.register("crm", RecordingTool()) is executor


def test_an_empty_contract_name_is_refused() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ToolExecutor().register("  ", RecordingTool())


def test_executors_are_independent_instances() -> None:
    """Implementation decision: per-instance, no global registry."""
    first = ToolExecutor().register("crm", RecordingTool())
    assert first.is_available("crm")
    assert not ToolExecutor().is_available("crm")


def test_there_is_no_unregister_api() -> None:
    for name in ("unregister", "remove", "clear", "pop", "without"):
        assert not hasattr(ToolExecutor, name)


def test_registration_is_explicit_with_no_auto_discovery() -> None:
    """Nothing scans, globs or imports to find implementations."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    "iter_modules", "import_module", "glob", "rglob", "walk_packages",
                }, path.name


def test_a_fresh_executor_serves_nothing() -> None:
    """No built-in tools, and therefore no default integration."""
    assert ToolExecutor().registered_contracts() == frozenset()


def test_no_locks_and_no_thread_safety_claim() -> None:
    """§11 states no atomicity requirement, unlike §7.10.

    Implementation decision: building locks would manufacture a guarantee no
    specification made, which a later module could then rely on.
    """
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"Lock", "RLock", "acquire"}, path.name
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "threading", path.name


# =============================================================================
# 7. Success cannot be fabricated (§11.2, §11.10)
# =============================================================================
def test_a_successful_response_cannot_carry_an_error_type() -> None:
    with pytest.raises(ValueError, match="fabricating success"):
        ToolResponse(success=True, error_type=ToolErrorType.EXECUTION_FAILED)


def test_a_response_cannot_be_successful_and_unavailable() -> None:
    with pytest.raises(ValueError, match="capability"):
        ToolResponse(success=True, capability_unavailable=True)


def test_the_executor_constructs_no_successful_response() -> None:
    """§11.10: a success claim is the implementation's to make.

    Every `ToolResponse` the executor builds is a decline or a failure. Checked
    structurally so a future edit cannot quietly add an optimistic path.
    """
    tree = ast.parse((PACKAGE / "executor.py").read_text(encoding="utf-8"))
    constructions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ToolResponse"
    ]
    assert constructions, "the executor must build its own decline/failure results"
    for call in constructions:
        for keyword in call.keywords:
            if keyword.arg == "success":
                assert isinstance(keyword.value, ast.Constant)
                assert keyword.value.value is False


def test_a_failing_tool_cannot_be_upgraded(executor: ToolExecutor) -> None:
    declined = ToolResponse(success=False, error_type=ToolErrorType.INVALID_REQUEST)
    executor.register("crm", RecordingTool(declined))
    result = executor.execute(request("crm"), context())
    assert result is declined
    assert not result.success


# =============================================================================
# 8. Error normalisation
# =============================================================================
def test_the_tool_error_vocabulary_is_exactly_four_members() -> None:
    """Ruled: small, tool-scoped, and deliberately not ProviderErrorType."""
    assert {member.value for member in ToolErrorType} == {
        "execution_failed",
        "invalid_request",
        "capability_unavailable",
        "timeout",
    }


def test_provider_error_type_is_not_reused() -> None:
    """§9.9's set is scoped to LLM vendor adapters and stays there."""
    from runtime.models.provider import ProviderErrorType

    assert ToolErrorType is not ProviderErrorType
    assert not issubclass(ToolErrorType, ProviderErrorType)
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "ProviderErrorType", path.name


@pytest.mark.parametrize("error", list(ToolErrorType))
def test_every_error_type_survives_a_round_trip(error: ToolErrorType) -> None:
    assert ToolResponse(success=False, error_type=error).error_type is error


def test_a_tool_may_report_a_timeout_the_framework_does_not_define(
    executor: ToolExecutor,
) -> None:
    """The vocabulary carries TIMEOUT so an implementation can report its own."""
    executor.register(
        "integrations",
        RecordingTool(ToolResponse(success=False, error_type=ToolErrorType.TIMEOUT)),
    )
    result = executor.execute(request("integrations"), context())
    assert result.error_type is ToolErrorType.TIMEOUT


# =============================================================================
# 10-12. Security and import boundary
# =============================================================================
def test_the_package_imports_only_models() -> None:
    """§11.7 grants the Resolver; ResolvedContext arrives as a parameter, so
    even that edge is unnecessary — matching all ten prior modules."""
    allowed = {"runtime.models", "runtime.tool_executor"}
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "runtime"
            ):
                package = ".".join(node.module.split(".")[:2])
                assert package in allowed, f"{path.name} imports {node.module}"


@pytest.mark.parametrize(
    "forbidden",
    [
        "runtime.validation",
        "runtime.workflow_state",
        "runtime.workflow_router",
        "runtime.provider",
        "runtime.provider_registry",
        "runtime.guardrail",
        "runtime.core_loader",
        "runtime.loader",
        "runtime.resolver",
        "runtime.assembler",
        "runtime.budget",
        "runtime.session",
    ],
)
def test_no_forbidden_module_is_imported(forbidden: str) -> None:
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(forbidden), (
                    f"{path.name} imports {forbidden}"
                )


def test_no_sdk_network_or_filesystem_access() -> None:
    forbidden = {
        "requests", "httpx", "urllib", "socket", "asyncio", "subprocess",
        "pathlib", "smtplib", "http", "ssl", "json",
    }
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, path.name
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden, path.name


def test_no_vendor_name_appears() -> None:
    """No default integration, and no vendor the framework has chosen.

    The repository already enforces this for two vendor names across all of
    `runtime/`; this extends the same rule to the integration vendors the tool
    contracts merely list as examples.
    """
    vendors = (
        "hubspot", "salesforce", "zoho", "pipedrive", "sendgrid", "mailgun",
        "twilio", "stripe", "slack", "notion", "zapier", "calendly", "outlook",
    )
    for path in source_files():
        text = path.read_text(encoding="utf-8").casefold()
        for vendor in vendors:
            assert vendor not in text, f"{path.name} names {vendor}"


def test_the_executor_does_not_parse_integration_markdown() -> None:
    """L-4 and ADR 0004: interpreting integrations/ text is not this module's.

    Availability comes from what was registered (TE-3), never from document
    text. Checked against the syntax tree, excluding docstrings — the module
    docstring explains this restriction, and explaining it is not doing it.
    """
    parsing = {"raw_text", "casefold", "splitlines", "findall", "search", "compile"}
    for path, tree in trees():
        docstrings = docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in parsing, f"{path.name} uses {node.attr}"
            if isinstance(node, ast.Name):
                assert node.id not in {"re", "ProjectDocument"}, path.name
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                assert "integrations/" not in node.value, path.name


def test_the_executor_never_touches_resolved_context_internals() -> None:
    """It forwards the context; it does not read the project's documents."""
    tree = ast.parse((PACKAGE / "executor.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {
                "integrations", "knowledge", "branding", "degraded_capabilities",
                "is_capability_available", "config",
            }, "the executor inspected ResolvedContext"


# =============================================================================
# 13. One call, one execution
# =============================================================================
def test_execute_takes_one_request_and_returns_one_response() -> None:
    """§11.6's frozen signature: no batch, no list, no generator."""
    import inspect

    signature = inspect.signature(ToolExecutor.execute)
    assert list(signature.parameters) == ["self", "tool_request", "resolved_context"]


def test_one_execute_call_invokes_the_tool_once(executor: ToolExecutor) -> None:
    tool = RecordingTool()
    executor.register("crm", tool)
    executor.execute(request("crm"), context())
    assert len(tool.calls) == 1


def test_no_async_batching_or_parallel_surface_exists() -> None:
    for path, tree in trees():
        for node in ast.walk(tree):
            assert not isinstance(node, ast.AsyncFunctionDef), path.name
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"gather", "submit", "map", "Thread"}, path.name
    for name in ("execute_all", "execute_many", "execute_batch", "execute_async"):
        assert not hasattr(ToolExecutor, name)


def test_the_executor_never_constructs_a_tool_request() -> None:
    """The Workflow State Manager is ToolRequest's frozen sole writer.

    A module that could manufacture its own input could manufacture the work it
    claims to have done.
    """
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "ToolRequest", f"{path.name} builds a request"


# =============================================================================
# 14. Repository conventions and recorded gaps
# =============================================================================
def test_both_models_are_frozen_with_slots() -> None:
    for model in (ToolRequest, ToolResponse):
        assert model.__dataclass_params__.frozen
        assert hasattr(model, "__slots__")


def test_mappings_are_read_only() -> None:
    with pytest.raises(TypeError):
        request().parameters["injected"] = "x"  # type: ignore[index]
    with pytest.raises(TypeError):
        ToolResponse().data["injected"] = "x"  # type: ignore[index]


def test_the_port_is_a_runtime_checkable_protocol() -> None:
    assert isinstance(RecordingTool(), ToolPort)
    assert not isinstance(object(), ToolPort)


def test_nothing_in_the_runtime_imports_this_module() -> None:
    """Module 11 is a leaf below the Runtime Engine; nothing depends back."""
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.is_relative_to(PACKAGE):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("runtime.tool_executor"), (
                    f"{path} imports the Tool Executor"
                )


@pytest.mark.parametrize(
    "issue",
    ["TE-1", "TE-2", "TE-3", "TE-4", "TE-5", "TE-6", "TE-7"],
)
def test_every_recorded_gap_is_in_the_register(issue: str) -> None:
    """The absences above are documented, not merely omitted."""
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert issue in register


def test_the_core_tools_dependency_cycle_is_recorded() -> None:
    """Found during this audit; recorded, not fixed (core/ is out of scope)."""
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert "TE-6" in register
    assert "consultation_form" in register
