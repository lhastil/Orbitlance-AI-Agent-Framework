"""Provider-independent foundation tests.

Verifies the boundary itself: the shared capability model, the neutral
`ProviderInterface`, the normalised error set, and the conformance suite that
every future adapter must pass. No provider is named, no SDK is imported, and no
concrete adapter exists — the fakes here stand in for adapters that do not yet
exist and prove the suite is usable before one is written.
"""

from __future__ import annotations

import pathlib

import pytest

from runtime.models.conversation import Turn, TurnRole
from runtime.models.provider import (
    ProviderCapabilities,
    ProviderErrorType,
    ProviderMetadata,
    ProviderResponse,
)
from runtime.provider import (
    ConformanceError,
    ContextWindowExceededError,
    ModelBinding,
    ModelIdentity,
    ProviderError,
    ProviderInterface,
    RecordingSerializer,
    SerializedPrompt,
    assert_conforms,
    run_conformance,
)
from runtime.provider.conformance import sample_bundle, sample_history
from runtime.provider.errors import (
    ERROR_BY_TYPE,
    ProviderAuthenticationError,
    ProviderCapabilityUnavailableError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

RUNTIME = pathlib.Path(__file__).resolve().parents[2] / "runtime"
PROVIDER = RUNTIME / "provider"


class FakeTokenizer:
    """A token counter bound to one fake identity. No tokenizer SDK involved."""

    def __init__(self, identity: ModelIdentity) -> None:
        self._identity = identity

    def count_tokens(self, text: str) -> int:
        return len(text)

    def model_identity(self) -> ModelIdentity:
        return self._identity


#: Fake identities. Deliberately not any real vendor or model name.
FAKE_A = ModelIdentity("fake-provider-a", "fake-model-1")
FAKE_B = ModelIdentity("fake-provider-b", "fake-model-2")


class ConformingProvider:
    """A minimal adapter that meets the contract. Names no vendor.

    Also demonstrates the two contracts a real adapter must satisfy: it builds a
    single `ModelBinding` (T-1/P-2) and reports its serialization neutrally
    (P-1/CS-1), reading history only from the bundle's authoritative window.
    """

    def __init__(self, window: int = 1000, reserve: int = 50, **flags) -> None:
        self._caps = ProviderCapabilities(window, reserve, **flags)
        self._binding = ModelBinding(
            identity=FAKE_A, capabilities=self._caps, tokenizer=FakeTokenizer(FAKE_A)
        )
        self._last: SerializedPrompt | None = None
        self._serializer = RecordingSerializer()

    def get_capabilities(self) -> ProviderCapabilities:
        return self._caps

    def model_binding(self) -> ModelBinding:
        return self._binding

    def last_serialized_prompt(self) -> SerializedPrompt | None:
        return self._last

    def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
        cost = sum(len(s.content) for s in prompt_bundle.static_sections)
        if cost + self._caps.serialization_reserve > self._caps.context_window:
            raise ContextWindowExceededError(
                f"payload of {cost} exceeds the declared window"
            )
        # P-1: history comes from the bundle's window. `history` is never read.
        self._last = self._serializer.record(prompt_bundle)
        return ProviderResponse(
            text="ok", metadata=ProviderMetadata(model="fake", input_tokens=cost)
        )


# --- the shared capability model ----------------------------------------------
def test_capabilities_live_in_the_shared_model_layer() -> None:
    import runtime.budget.ports as budget_ports
    import runtime.models.provider as models_provider

    assert budget_ports.ProviderCapabilities is models_provider.ProviderCapabilities
    src = pathlib.Path(budget_ports.__file__).read_text(encoding="utf-8")
    assert "class ProviderCapabilities" not in src, "no second definition"


def test_capabilities_carry_the_provider_interface_fields() -> None:
    caps = ProviderCapabilities(1000, 50, streaming_support=True, tool_calling_support=True)
    assert (caps.context_window, caps.serialization_reserve) == (1000, 50)
    assert caps.streaming_support and caps.tool_calling_support


def test_capability_feature_flags_default_conservatively() -> None:
    caps = ProviderCapabilities(1000, 50)
    assert caps.streaming_support is False
    assert caps.tool_calling_support is False


def test_capabilities_reject_impossible_values() -> None:
    with pytest.raises(ValueError):
        ProviderCapabilities(0, 0)
    with pytest.raises(ValueError):
        ProviderCapabilities(100, -1)


def test_capabilities_are_immutable() -> None:
    import dataclasses

    caps = ProviderCapabilities(1000, 50)
    with pytest.raises(dataclasses.FrozenInstanceError):
        caps.context_window = 1  # type: ignore[misc]


# --- the normalised response ---------------------------------------------------
def test_response_implements_the_frozen_data_model() -> None:
    r = ProviderResponse(
        text="hi",
        metadata=ProviderMetadata(model="m", input_tokens=1, output_tokens=2, latency_ms=3.0),
        error_type=None,
        raw_payload={"debug": True},
    )
    assert r.text == "hi" and not r.failed
    assert (r.metadata.model, r.metadata.input_tokens) == ("m", 1)
    assert r.raw_payload["debug"] is True


def test_response_raw_payload_is_read_only() -> None:
    r = ProviderResponse(raw_payload={"a": 1})
    with pytest.raises(TypeError):
        r.raw_payload["b"] = 2  # type: ignore[index]


def test_metadata_reports_none_rather_than_inventing_numbers() -> None:
    m = ProviderMetadata()
    assert (m.model, m.input_tokens, m.output_tokens, m.latency_ms) == (None,) * 4


def test_failed_reflects_the_error_type() -> None:
    assert ProviderResponse(error_type=ProviderErrorType.TIMEOUT).failed
    assert not ProviderResponse().failed


# --- normalised errors ----------------------------------------------------------
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderAuthenticationError, ProviderErrorType.AUTHENTICATION),
        (ProviderRateLimitError, ProviderErrorType.RATE_LIMIT),
        (ProviderTimeoutError, ProviderErrorType.TIMEOUT),
        (ContextWindowExceededError, ProviderErrorType.CONTEXT_WINDOW_EXCEEDED),
        (ProviderUnavailableError, ProviderErrorType.SERVICE_UNAVAILABLE),
    ],
)
def test_each_error_carries_its_normalised_type(error, expected) -> None:
    assert error("x").error_type is expected
    assert isinstance(error("x"), ProviderError)


def test_error_hierarchy_is_catchable_as_one() -> None:
    for error in (ProviderAuthenticationError, ProviderTimeoutError, ContextWindowExceededError):
        with pytest.raises(ProviderError):
            raise error("boom")


def test_every_error_type_maps_to_an_exception() -> None:
    assert set(ERROR_BY_TYPE) == set(ProviderErrorType)


def test_capability_unavailable_is_a_configuration_failure() -> None:
    assert ProviderCapabilityUnavailableError("x").error_type is ProviderErrorType.INVALID_REQUEST


def test_errors_preserve_the_vendor_cause_for_debugging() -> None:
    original = RuntimeError("vendor detail")
    try:
        try:
            raise original
        except RuntimeError as exc:
            raise ProviderRateLimitError("throttled") from exc
    except ProviderRateLimitError as exc:
        assert exc.__cause__ is original


# --- the conformance suite ------------------------------------------------------
def test_a_conforming_provider_passes() -> None:
    report = run_conformance(ConformingProvider())
    assert report.passed, report.failures
    # 8 foundation checks + CS-1 (authoritative history) + CS-3 (binding).
    assert len(report.checks_run) == 10


def test_assert_conforms_is_silent_on_success() -> None:
    assert_conforms(ConformingProvider())


def test_suite_runs_without_any_real_provider() -> None:
    """The whole point: no SDK, no network, no vendor."""
    assert run_conformance(ConformingProvider(window=200, reserve=10)).passed


def test_suite_reports_every_failure_not_just_the_first() -> None:
    class Broken:
        def get_capabilities(self):
            return ProviderCapabilities(10, 0)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            return ProviderResponse(text="truncated anyway")

    report = run_conformance(Broken())
    assert not report.passed
    assert len(report.failures) >= 1
    with pytest.raises(ConformanceError):
        report.raise_if_failed()


def test_suite_catches_an_adapter_that_truncates_instead_of_failing() -> None:
    class Truncating:
        def get_capabilities(self):
            return ProviderCapabilities(100, 10)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            return ProviderResponse(text="I shortened it")

    failures = " ".join(run_conformance(Truncating()).failures)
    assert "fails_closed" in failures


def test_suite_catches_an_adapter_leaking_a_raw_exception() -> None:
    class Leaky:
        def get_capabilities(self):
            return ProviderCapabilities(100, 10)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            raise ValueError("raw vendor error")

    failures = " ".join(run_conformance(Leaky()).failures)
    assert "non-normalised" in failures or "ValueError" in failures


def test_suite_catches_unstable_capabilities() -> None:
    class Drifting:
        def __init__(self):
            self.n = 0

        def get_capabilities(self):
            self.n += 1
            return ProviderCapabilities(100 + self.n, 10)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            raise ContextWindowExceededError("x")

    failures = " ".join(run_conformance(Drifting()).failures)
    assert "not stable" in failures


def test_suite_catches_an_adapter_that_mutates_the_bundle() -> None:
    class Mutating:
        def get_capabilities(self):
            return ProviderCapabilities(100_000, 10)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            object.__setattr__(prompt_bundle, "latest_message", "rewritten")
            return ProviderResponse(text="ok")

    failures = " ".join(run_conformance(Mutating()).failures)
    assert "mutated" in failures


def test_suite_catches_non_boolean_capability_flags() -> None:
    class Sloppy:
        def get_capabilities(self):
            caps = ProviderCapabilities(100, 10)
            object.__setattr__(caps, "streaming_support", "yes")
            return caps

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            raise ContextWindowExceededError("x")

    failures = " ".join(run_conformance(Sloppy()).failures)
    assert "streaming_support" in failures


def test_oversized_fixture_scales_with_the_declared_window() -> None:
    from runtime.provider.conformance import oversized_bundle

    small = oversized_bundle(ProviderCapabilities(100, 0))
    large = oversized_bundle(ProviderCapabilities(100_000, 0))
    assert len(large.static_sections[0].content) > len(small.static_sections[0].content)


def test_conformance_fixtures_are_provider_neutral() -> None:
    bundle = sample_bundle()
    assert bundle.static_sections and bundle.latest_message
    assert all(isinstance(t, Turn) for t in sample_history())
    assert sample_history()[0].role is TurnRole.USER


# --- the interface ---------------------------------------------------------------
def test_conforming_provider_satisfies_the_protocol() -> None:
    assert isinstance(ConformingProvider(), ProviderInterface)


def test_an_incomplete_adapter_does_not_satisfy_the_protocol() -> None:
    class Partial:
        def get_capabilities(self):
            return ProviderCapabilities(100, 10)

    assert not isinstance(Partial(), ProviderInterface)


# --- provider independence ---------------------------------------------------------
def test_no_provider_sdk_anywhere_in_the_runtime() -> None:
    for path in RUNTIME.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        src = path.read_text(encoding="utf-8").lower()
        for sdk in ("import openai", "import anthropic", "import tiktoken", "from openai", "from anthropic"):
            assert sdk not in src, f"{path.name} imports a provider SDK"


def test_no_concrete_adapter_exists() -> None:
    adapters = [p for p in (PROVIDER / "adapters").iterdir() if p.name != "__init__.py"]
    assert adapters == [], f"unexpected adapter: {adapters}"


def test_provider_package_names_no_vendor() -> None:
    for path in PROVIDER.glob("*.py"):
        src = path.read_text(encoding="utf-8").lower()
        for vendor in ("openai", "anthropic", "gemini", "claude", "gpt-4", "mistral", "cohere"):
            assert vendor not in src, f"{path.name} names {vendor}"


def test_no_hard_coded_context_window_in_the_provider_layer() -> None:
    for path in PROVIDER.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for window in ("128000", "200000", "8192", "32768", "1048576"):
            assert window not in src, f"{path.name} hard-codes a window"


def test_modules_one_to_five_do_not_import_the_provider_package() -> None:
    for package in ("validation", "loader", "resolver", "assembler", "budget"):
        for path in (RUNTIME / package).glob("*.py"):
            src = path.read_text(encoding="utf-8")
            assert "runtime.provider" not in src, f"{package}/{path.name} imports runtime.provider"


def test_provider_layer_depends_only_on_shared_models() -> None:
    for path in PROVIDER.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for forbidden in ("runtime.validation", "runtime.loader", "runtime.resolver", "runtime.assembler", "runtime.budget"):
            assert forbidden not in src, f"{path.name} imports {forbidden}"


def test_no_third_party_dependency_was_added() -> None:
    pyproject = (RUNTIME.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject
