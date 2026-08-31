"""Provider Registry tests — specification §10.

Covers all four §10.12 scenarios and pins every ruled decision (D-1 through
D-9), including the ones expressed as *absences*: no network in a lookup, no
placeholder vocabulary, no locks, no `ProviderResponse` written here, no
`ProviderRequest` built yet. An absence that nothing asserts is an absence that
returns quietly, so each is a test rather than a comment.

Every identity below is fake. No vendor is named, no SDK is imported, and the
registry is exercised against adapters shaped like the reference `GoodAdapter`
in `tests/provider/`.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from runtime.models.conversation import Turn, TurnRole
from runtime.models.project_config import LlmProviderSelection, ProjectConfig
from runtime.models.project_context import ProjectContext, ProjectDocument
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import (
    ProviderCapabilities,
    ProviderErrorType,
    ProviderMetadata,
    ProviderResponse,
)
from runtime.models.resolved_context import ResolvedConfig, ResolvedContext
from runtime.provider.binding import ModelBinding, ModelIdentity
from runtime.provider.errors import (
    ContextWindowExceededError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from runtime.provider_registry import (
    FAILOVER_ERROR_TYPES,
    AllProvidersFailedError,
    DuplicateProviderError,
    ProviderModelMismatchError,
    ProviderNotRegisteredError,
    ProviderRegistry,
    UnidentifiableProviderError,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "runtime" / "provider_registry"

#: Fake identities only. None is a real vendor or model.
ALPHA = ModelIdentity("alpha", "alpha-model-1")
ALPHA_V2 = ModelIdentity("alpha", "alpha-model-2")
BETA = ModelIdentity("beta", "beta-model-1")


class FakeTokenizer:
    def __init__(self, identity: ModelIdentity) -> None:
        self._identity = identity

    def count_tokens(self, text: str) -> int:
        return len(text)

    def model_identity(self) -> ModelIdentity:
        return self._identity


class FakeAdapter:
    """A `ProviderInterface` + `ModelBoundProvider`, driven by the test.

    `fail_with` makes it raise a chosen normalised error; `calls` records what
    it was handed, so pass-through can be asserted rather than assumed.
    """

    def __init__(
        self, identity: ModelIdentity, fail_with: ProviderError | None = None
    ) -> None:
        self._binding = ModelBinding(
            identity=identity,
            capabilities=ProviderCapabilities(10_000, 50),
            tokenizer=FakeTokenizer(identity),
        )
        self.fail_with = fail_with
        self.calls: list[tuple[PromptBundle, tuple[Turn, ...]]] = []

    def get_capabilities(self) -> ProviderCapabilities:
        return self._binding.capabilities

    def model_binding(self) -> ModelBinding:
        return self._binding

    def generate(
        self, prompt_bundle: PromptBundle, history: tuple[Turn, ...]
    ) -> ProviderResponse:
        self.calls.append((prompt_bundle, history))
        if self.fail_with is not None:
            raise self.fail_with
        return ProviderResponse(
            text=f"answered by {self._binding.identity}",
            metadata=ProviderMetadata(model=self._binding.identity.model_id),
        )


class UnboundAdapter:
    """Satisfies `ProviderInterface` but exposes no binding."""

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(1_000, 10)

    def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
        return ProviderResponse(text="")


def context(
    primary: str | None = "alpha",
    model: str | None = "alpha-model-1",
    secondary: str | None = None,
    project_id: str = "test_project",
) -> ResolvedContext:
    return ResolvedContext(
        project_id=project_id,
        config=ResolvedConfig(
            llm_provider=LlmProviderSelection(
                primary=primary, model=model, secondary=secondary
            )
        ),
    )


def bundle() -> PromptBundle:
    return PromptBundle(
        project_id="test_project",
        conversation_id="c1",
        conversation_history_window=(Turn(role=TurnRole.USER, content="earlier"),),
        latest_message="hello",
    )


def raw_history() -> tuple[Turn, ...]:
    return (Turn(role=TurnRole.USER, content="unbudgeted"),)


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry().register(FakeAdapter(ALPHA))


def source_files() -> list[pathlib.Path]:
    return sorted(PACKAGE.glob("*.py"))


def trees() -> list[tuple[pathlib.Path, ast.Module]]:
    return [(p, ast.parse(p.read_text(encoding="utf-8"))) for p in source_files()]


def docstring_nodes(tree: ast.Module) -> set[int]:
    """Ids of the `Constant` nodes that are docstrings.

    Identity, not text. `ast.get_docstring` returns a *cleaned* string, so
    comparing a raw `Constant.value` against it silently never matches — which
    would turn every "excludes docstrings" scan below into a scan of nothing.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            continue
        if body and isinstance(body[0], ast.Expr):
            first = body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.add(id(first))
    return found


# =============================================================================
# §10.12(a) — routes to the correct provider for a given project
# =============================================================================
def test_a_routes_to_the_declared_provider(registry: ProviderRegistry) -> None:
    assert registry.get_provider(context()).model_binding().identity == ALPHA


def test_a_routes_by_project_not_by_registration_order() -> None:
    registry = ProviderRegistry().register(FakeAdapter(ALPHA)).register(
        FakeAdapter(BETA)
    )
    resolved = context(primary="beta", model="beta-model-1")
    assert registry.get_provider(resolved).model_binding().identity == BETA


def test_a_generate_with_fallback_returns_the_primarys_response(
    registry: ProviderRegistry,
) -> None:
    response = registry.generate_with_fallback(context(), bundle(), raw_history())
    assert response.text == f"answered by {ALPHA}"
    assert response.error_type is None


def test_a_an_unregistered_provider_is_refused(registry: ProviderRegistry) -> None:
    with pytest.raises(ProviderNotRegisteredError, match="not registered"):
        registry.get_provider(context(primary="gamma", model="gamma-1"))


def test_a_the_refusal_lists_what_is_registered(registry: ProviderRegistry) -> None:
    """§10.10 is an operator-facing configuration error; it must be actionable."""
    with pytest.raises(ProviderNotRegisteredError) as raised:
        registry.get_provider(context(primary="gamma", model="gamma-1"))
    assert "Registered providers: alpha" in str(raised.value)
    assert "10.10" in str(raised.value)


# =============================================================================
# D-1(b) — route by provider_id, then assert the bound model
# =============================================================================
def test_d1_a_matching_model_resolves(registry: ProviderRegistry) -> None:
    assert registry.get_provider(context(model="alpha-model-1")) is not None


def test_d1_a_different_model_of_the_same_vendor_is_refused(
    registry: ProviderRegistry,
) -> None:
    """The registry key is coarser than identity; this is what keeps it honest."""
    with pytest.raises(ProviderModelMismatchError) as raised:
        registry.get_provider(context(model="alpha-model-2"))
    assert "'alpha-model-2'" in str(raised.value)
    assert "'alpha-model-1'" in str(raised.value)


def test_d1_an_undeclared_model_is_refused(registry: ProviderRegistry) -> None:
    """Fail-closed: an unstated model is not agreement.

    Consequence worth seeing plainly — this makes the declared Model effectively
    required at routing time, while the Validation Layer requires only the
    Primary. Recorded as PR-2 in docs/known-issues-runtime.md.
    """
    with pytest.raises(ProviderModelMismatchError):
        registry.get_provider(context(model=None))


def test_d1_a_placeholder_model_is_refused(registry: ProviderRegistry) -> None:
    """No placeholder vocabulary needed — a placeholder simply is not the model."""
    with pytest.raises(ProviderModelMismatchError):
        registry.get_provider(context(model="_(not yet selected)_"))


def test_d1_the_model_check_also_guards_generate_with_fallback(
    registry: ProviderRegistry,
) -> None:
    with pytest.raises(ProviderModelMismatchError):
        registry.generate_with_fallback(
            context(model="alpha-model-2"), bundle(), raw_history()
        )


def test_d1_two_models_of_one_vendor_cannot_both_register() -> None:
    """A consequence of provider_id keying, asserted rather than discovered."""
    registry = ProviderRegistry().register(FakeAdapter(ALPHA))
    with pytest.raises(DuplicateProviderError):
        registry.register(FakeAdapter(ALPHA_V2))


# =============================================================================
# D-2(a) — absent/placeholder primary is uniformly "not registered"
# =============================================================================
@pytest.mark.parametrize(
    "primary", [None, "", "_(placeholder)_", "_(not yet selected)_", "TBD"]
)
def test_d2_every_unusable_primary_raises_the_same_error(
    registry: ProviderRegistry, primary: str | None
) -> None:
    with pytest.raises(ProviderNotRegisteredError):
        registry.get_provider(context(primary=primary))


def test_d2_the_module_holds_no_placeholder_vocabulary() -> None:
    """Placeholder semantics stay in the Validation Layer, in one copy.

    A second copy would drift from the first with nothing to detect it — the
    class ADR 0002 exists to warn about. Checked against the syntax tree so
    prose in a docstring explaining this is not mistaken for logic.
    """
    forbidden = ("PLACEHOLDER_MARKERS", "_is_placeholder", "casefold")
    for path, tree in trees():
        docstrings = docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name | ast.Attribute):
                name = node.id if isinstance(node, ast.Name) else node.attr
                assert name not in forbidden, f"{path.name} uses {name}"
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                for marker in ("placeholder", "not yet", "tbd"):
                    assert marker not in node.value.casefold(), path.name


# =============================================================================
# §10.12(b) + D-4(c) — failover, and only on the named classes
# =============================================================================
def two_providers(failure: ProviderError) -> tuple[ProviderRegistry, FakeAdapter]:
    secondary = FakeAdapter(BETA)
    registry = (
        ProviderRegistry()
        .register(FakeAdapter(ALPHA, fail_with=failure))
        .register(secondary)
    )
    return registry, secondary


@pytest.mark.parametrize(
    "failure",
    [ProviderRateLimitError("throttled"), ProviderTimeoutError("slow"),
     ProviderUnavailableError("down")],
)
def test_b_a_transient_primary_failure_falls_back(failure: ProviderError) -> None:
    registry, secondary = two_providers(failure)
    response = registry.generate_with_fallback(
        context(secondary="beta"), bundle(), raw_history()
    )
    assert response.text == f"answered by {BETA}"
    assert len(secondary.calls) == 1


@pytest.mark.parametrize(
    "failure",
    [ProviderAuthenticationError("rejected"), ProviderInvalidRequestError("bad"),
     ContextWindowExceededError("too big"), ProviderError("unclassifiable")],
)
def test_d4_a_non_transient_failure_never_falls_back(failure: ProviderError) -> None:
    """The whole reason for naming a subset.

    A rotated primary credential answered by a working secondary would hide the
    misconfiguration for as long as the secondary held out.
    """
    registry, secondary = two_providers(failure)
    with pytest.raises(type(failure)):
        registry.generate_with_fallback(
            context(secondary="beta"), bundle(), raw_history()
        )
    assert secondary.calls == []


def test_d4_the_failover_set_is_exactly_three_named_classes() -> None:
    named = {
        ProviderErrorType.RATE_LIMIT,
        ProviderErrorType.TIMEOUT,
        ProviderErrorType.SERVICE_UNAVAILABLE,
    }
    assert set(FAILOVER_ERROR_TYPES) == named


def test_d4_every_other_normalised_class_is_excluded() -> None:
    """Pins the complement too, so a new enum member cannot join by default."""
    excluded = set(ProviderErrorType) - FAILOVER_ERROR_TYPES
    assert excluded == {
        ProviderErrorType.AUTHENTICATION,
        ProviderErrorType.CONTEXT_WINDOW_EXCEEDED,
        ProviderErrorType.INVALID_REQUEST,
        ProviderErrorType.UNKNOWN,
    }


def test_b_the_propagated_failure_is_the_original_object() -> None:
    failure = ProviderAuthenticationError("rejected")
    registry, _ = two_providers(failure)
    with pytest.raises(ProviderAuthenticationError) as raised:
        registry.generate_with_fallback(
            context(secondary="beta"), bundle(), raw_history()
        )
    assert raised.value is failure


# =============================================================================
# §10.12(c) + D-5(c) — terminal exhaustion
# =============================================================================
def test_c_no_secondary_configured_exhausts() -> None:
    registry = ProviderRegistry().register(
        FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow"))
    )
    with pytest.raises(AllProvidersFailedError) as raised:
        registry.generate_with_fallback(context(), bundle(), raw_history())
    assert "No usable secondary is configured" in str(raised.value)


def test_c_an_unregistered_secondary_exhausts() -> None:
    registry = ProviderRegistry().register(
        FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow"))
    )
    with pytest.raises(AllProvidersFailedError):
        registry.generate_with_fallback(
            context(secondary="never_registered"), bundle(), raw_history()
        )


def test_c_both_failing_exhausts() -> None:
    registry = (
        ProviderRegistry()
        .register(FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow")))
        .register(FakeAdapter(BETA, fail_with=ProviderUnavailableError("down")))
    )
    with pytest.raises(AllProvidersFailedError) as raised:
        registry.generate_with_fallback(
            context(secondary="beta"), bundle(), raw_history()
        )
    assert raised.value.attempts == (("alpha", "timeout"), ("beta", "service_unavailable"))


def test_c_any_secondary_failure_is_exhaustion_not_propagation() -> None:
    """§10.9: the secondary is the last hop, so its class decides nothing further."""
    registry = (
        ProviderRegistry()
        .register(FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow")))
        .register(FakeAdapter(BETA, fail_with=ProviderAuthenticationError("rejected")))
    )
    with pytest.raises(AllProvidersFailedError):
        registry.generate_with_fallback(
            context(secondary="beta"), bundle(), raw_history()
        )


def test_d5_exhaustion_is_a_provider_error_subclass() -> None:
    """So §14.9's handler catches it without knowing this module exists."""
    assert issubclass(AllProvidersFailedError, ProviderError)


def test_d5_exhaustion_stays_unknown_rather_than_claiming_a_class() -> None:
    assert AllProvidersFailedError("x").error_type is ProviderErrorType.UNKNOWN


def test_d5_exhaustion_names_the_providers_and_their_failure_classes() -> None:
    registry = ProviderRegistry().register(
        FakeAdapter(ALPHA, fail_with=ProviderRateLimitError("throttled"))
    )
    with pytest.raises(AllProvidersFailedError) as raised:
        registry.generate_with_fallback(context(), bundle(), raw_history())
    message = str(raised.value)
    assert "'alpha'" in message and "rate_limit" in message
    assert "test_project" in message


def test_d5_the_registry_never_constructs_a_provider_response() -> None:
    """The frozen data model names the adapter `ProviderResponse`'s sole writer."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "ProviderResponse", (
                    f"{path.name} constructs a ProviderResponse"
                )


def test_d5_no_user_facing_fallback_text_is_invented() -> None:
    """§10.9's phrase is §14's wording to compose, never a string emitted here.

    It may appear in a docstring citing the clause — quoting a specification is
    not shipping a customer-facing message — but never in a runtime string.
    """
    for path, tree in trees():
        docstrings = docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                assert "technical difficult" not in node.value.casefold(), path.name


# =============================================================================
# D-3(a) — pass-through, and the adapter's own C-1a is the capacity check
# =============================================================================
def test_d3_the_bundle_and_history_reach_the_adapter_unchanged() -> None:
    adapter = FakeAdapter(ALPHA)
    registry = ProviderRegistry().register(adapter)
    sent_bundle, sent_history = bundle(), raw_history()
    registry.generate_with_fallback(context(), sent_bundle, sent_history)
    seen_bundle, seen_history = adapter.calls[0]
    assert seen_bundle is sent_bundle
    assert seen_history is sent_history


def test_d3_the_secondary_receives_the_same_bundle_object() -> None:
    """No re-assembly and no re-budgeting: §10.3 forbids deciding prompt content."""
    secondary = FakeAdapter(BETA)
    registry = (
        ProviderRegistry()
        .register(FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow")))
        .register(secondary)
    )
    sent = bundle()
    registry.generate_with_fallback(context(secondary="beta"), sent, raw_history())
    assert secondary.calls[0][0] is sent


def test_d3_a_secondary_that_cannot_fit_the_bundle_fails_closed_itself() -> None:
    """The capacity guarantee is the adapter's C-1a, not a registry algorithm.

    `ContextWindowExceededError` is outside the failover set, so it propagates
    from the secondary as exhaustion rather than being retried or trimmed.
    """
    registry = (
        ProviderRegistry()
        .register(FakeAdapter(ALPHA, fail_with=ProviderTimeoutError("slow")))
        .register(FakeAdapter(BETA, fail_with=ContextWindowExceededError("too big")))
    )
    with pytest.raises(AllProvidersFailedError) as raised:
        registry.generate_with_fallback(
            context(secondary="beta"), bundle(), raw_history()
        )
    assert raised.value.attempts[-1] == ("beta", "context_window_exceeded")


def test_d3_no_compatibility_comparison_exists() -> None:
    """No capability or window arithmetic anywhere in the package."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {
                    "context_window",
                    "serialization_reserve",
                    "count_tokens",
                }, f"{path.name} inspects {node.attr}"


# =============================================================================
# D-6(a) — instances only; lookup is offline
# =============================================================================
def test_d6_register_takes_a_constructed_instance() -> None:
    registry = ProviderRegistry()
    assert registry.register(FakeAdapter(ALPHA)) is registry


def test_d6_an_adapter_without_a_binding_cannot_register() -> None:
    with pytest.raises(UnidentifiableProviderError, match="model_binding"):
        ProviderRegistry().register(UnboundAdapter())


def test_d6_the_key_comes_from_the_adapter_not_from_the_caller() -> None:
    registry = ProviderRegistry().register(FakeAdapter(BETA))
    assert registry.registered_providers() == frozenset({"beta"})


def test_d6_no_network_credentials_or_environment_access() -> None:
    """Checked against the syntax tree, excluding docstrings.

    The module docstring explains that credentials are read in exactly one place
    and that this is not a second; explaining that is not doing it.
    """
    forbidden = {
        "os", "socket", "requests", "httpx", "urllib", "asyncio", "google",
        "openai", "anthropic", "threading", "pathlib", "subprocess",
    }
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"{path.name} imports {alias.name}"
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module.split(".")[0] not in forbidden, f"{path.name}: {module}"
                assert not module.startswith("runtime.provider.adapters"), path.name
                assert not module.startswith("runtime.validation"), path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"os", "environ", "getenv"}, path.name


def test_d6_no_adapter_or_vendor_name_appears() -> None:
    """§10.8 gives this module no external dependencies, and there is no default."""
    for path in source_files():
        text = path.read_text(encoding="utf-8").casefold()
        for vendor in ("gemini", "anthropic", "openai", "claude", "gpt"):
            assert vendor not in text, f"{path.name} names {vendor}"


# =============================================================================
# D-7 — registration semantics
# =============================================================================
def test_d7_registries_are_independent_instances() -> None:
    first = ProviderRegistry().register(FakeAdapter(ALPHA))
    second = ProviderRegistry()
    assert first.is_registered("alpha")
    assert not second.is_registered("alpha")


def test_d7_a_duplicate_is_rejected_and_the_original_survives() -> None:
    original = FakeAdapter(ALPHA)
    registry = ProviderRegistry().register(original)
    with pytest.raises(DuplicateProviderError, match="already registered"):
        registry.register(FakeAdapter(ALPHA))
    assert registry.get_provider(context()) is original


def test_d7_there_is_no_unregister() -> None:
    """Absence is reversible; a removed method is not."""
    for name in ("unregister", "remove", "clear", "without", "pop"):
        assert not hasattr(ProviderRegistry, name)


def test_d7_no_locks_and_no_atomicity_claim() -> None:
    """§10 has no atomicity clause, unlike §7.10.

    Building locks would manufacture a guarantee no specification made, which a
    later module could then rely on.
    """
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"Lock", "RLock", "acquire"}, path.name
            if isinstance(node, ast.With | ast.AsyncWith):
                for item in node.items:
                    assert not isinstance(item.context_expr, ast.Attribute), path.name


def test_d7_conformance_is_documented_but_not_executed_by_register() -> None:
    """Running `generate()` as a side effect of wiring a process is not wiring."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"run_conformance", "assert_conforms"}, (
                    path.name
                )
    registration = (PACKAGE / "registry.py").read_text(encoding="utf-8")
    assert "9.10" in registration, "the requirement must at least be stated"


def test_d7_registration_is_explicit_with_no_auto_discovery() -> None:
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"iter_modules", "import_module", "glob"}, (
                    path.name
                )


# =============================================================================
# §10.12(d) — the Validation Layer seam, with the real registry
# =============================================================================
def project_declaring(primary: str, model: str = "m") -> ProjectContext:
    return ProjectContext(
        project_id="seam_project",
        root_path="/seam_project",
        root_exists=True,
        config=ProjectDocument(
            name="config.md",
            relative_path="projects/seam_project/config.md",
            exists=True,
            raw_text="# config",
        ),
        config_data=ProjectConfig(
            declared_sections=frozenset({"LLM Provider"}),
            llm_provider=LlmProviderSelection(primary=primary, model=model),
        ),
    )


def test_d_the_real_registry_satisfies_the_validation_port() -> None:
    """Structurally — this module does not import the Validation Layer."""
    from runtime.validation.ports import ProviderRegistryPort

    assert isinstance(ProviderRegistry(), ProviderRegistryPort)


def test_d_an_unregistered_provider_is_flagged_at_validation_time() -> None:
    """§10.12(d): caught before activation, not at the first request."""
    from runtime.validation.rule import ProjectRuleContext
    from runtime.validation.rules.config import ConfigProviderRegisteredRule

    registry = ProviderRegistry().register(FakeAdapter(ALPHA))
    rule = ConfigProviderRegisteredRule()
    ctx = ProjectRuleContext(
        project=project_declaring("gamma"), provider_registry=registry
    )
    issues = list(rule.evaluate(ctx))
    assert len(issues) == 1
    assert issues[0].code == "CONF005"
    assert "alpha" in issues[0].recommendation


def test_d_a_registered_provider_raises_no_validation_issue() -> None:
    from runtime.validation.rule import ProjectRuleContext
    from runtime.validation.rules.config import ConfigProviderRegisteredRule

    registry = ProviderRegistry().register(FakeAdapter(ALPHA))
    ctx = ProjectRuleContext(
        project=project_declaring("alpha"), provider_registry=registry
    )
    assert list(ConfigProviderRegisteredRule().evaluate(ctx)) == []


def test_d9_the_secondary_is_not_validated_and_the_gap_is_recorded() -> None:
    """The committed rule reads `primary` only; §10.10 covers any routed-to
    provider. Not fixed here — Module 13 is out of scope — so the contradiction
    is pinned to the register rather than left to be rediscovered."""
    from runtime.validation.rules import config as config_rules

    source = pathlib.Path(config_rules.__file__).read_text(encoding="utf-8")
    assert "llm_provider.secondary" not in source

    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert "PR-1" in register
    assert "secondary" in register.casefold()


# =============================================================================
# D-8(b) — ProviderRequest is deferred, and its ownership stays reserved
# =============================================================================
def test_d8_provider_request_is_not_implemented() -> None:
    assert not (REPO_ROOT / "runtime" / "models" / "provider_request.py").exists()
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "ProviderRequest", path.name


def test_d8_the_deferral_is_recorded_with_its_reserved_ownership() -> None:
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert "PR-3" in register
    assert "ProviderRequest" in register


# =============================================================================
# Structural independence
# =============================================================================
def test_the_package_depends_only_on_models_and_the_provider_interface() -> None:
    allowed = {"runtime.models", "runtime.provider", "runtime.provider_registry"}
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "runtime"
            ):
                package = ".".join(node.module.split(".")[:2])
                assert package in allowed, f"{path.name} imports {node.module}"


def test_nothing_in_the_runtime_imports_this_module() -> None:
    """Module 10 is a leaf below the Runtime Engine; nothing may depend back."""
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.is_relative_to(PACKAGE):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("runtime.provider_registry"), (
                    f"{path} imports the Provider Registry"
                )
