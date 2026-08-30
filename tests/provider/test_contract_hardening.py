"""Provider contract hardening — P-1, C-1a, T-1, P-2, E-1, CS-1, CS-3.

Every fake here stands in for an adapter that does not exist yet. No provider is
named, no SDK is imported, and every identity is explicitly fake. The point of
each test is the same: prove the suite *catches* the failure, not merely that a
correct implementation passes. A conformance check that has never failed
anything is a check nobody has tested.
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
    ContextWindowExceededError,
    ModelBinding,
    ModelBoundProvider,
    ModelIdentity,
    PromptInspectable,
    ProviderBindingError,
    ProviderError,
    ProviderInterface,
    RecordingSerializer,
    SerializedPrompt,
    run_conformance,
)
from runtime.provider.conformance import (
    BUNDLE_HISTORY_SENTINEL,
    RAW_HISTORY_SENTINEL,
    check_authoritative_history_is_serialized,
    check_tokenizer_and_capabilities_agree,
    history_probe_bundle,
    raw_history_probe,
    sample_bundle,
)
from runtime.provider.errors import ProviderInvalidRequestError

PROVIDER = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "provider"

#: Fake identities only. None of these is a real vendor or model.
MODEL_A = ModelIdentity("fake-provider-a", "fake-model-1")
MODEL_B = ModelIdentity("fake-provider-b", "fake-model-2")


class FakeTokenizer:
    """Counts characters. Bound to one identity. No tokenizer SDK."""

    def __init__(self, identity: ModelIdentity) -> None:
        self._identity = identity

    def count_tokens(self, text: str) -> int:
        return len(text)

    def model_identity(self) -> ModelIdentity:
        return self._identity


class AnonymousTokenizer:
    """Satisfies token counting but declares no identity."""

    def count_tokens(self, text: str) -> int:
        return len(text)


def a_binding(identity: ModelIdentity = MODEL_A, window: int = 10_000) -> ModelBinding:
    return ModelBinding(
        identity=identity,
        capabilities=ProviderCapabilities(window, 50),
        tokenizer=FakeTokenizer(identity),
    )


class GoodAdapter:
    """The reference shape: one binding, bundle-sourced history, neutral report."""

    def __init__(self, binding: ModelBinding | None = None) -> None:
        self._binding = binding if binding is not None else a_binding()
        self._last: SerializedPrompt | None = None

    def get_capabilities(self) -> ProviderCapabilities:
        return self._binding.capabilities

    def model_binding(self) -> ModelBinding:
        return self._binding

    def last_serialized_prompt(self) -> SerializedPrompt | None:
        return self._last

    def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
        # P-1: history is read from the bundle's window. `history` is ignored.
        snapshot = RecordingSerializer().record(prompt_bundle)
        # C-1a: the final fail-closed assertion, before the call, counted with
        # the bound tokenizer so the count and the window describe one model.
        caps = self._binding.capabilities
        cost = sum(
            self._binding.tokenizer.count_tokens(text) for text in snapshot.all_texts
        )
        if cost + caps.serialization_reserve > caps.context_window:
            raise ContextWindowExceededError(
                f"serialized payload of {cost} plus reserve "
                f"{caps.serialization_reserve} exceeds window {caps.context_window}"
            )
        self._last = snapshot
        return ProviderResponse(text="ok", metadata=ProviderMetadata(model="fake"))


# =============================================================================
# P-1 / CS-1 — the authoritative history contract
# =============================================================================
def test_the_two_history_sentinels_are_disjoint() -> None:
    """The probe is only meaningful if neither sentinel contains the other."""
    assert BUNDLE_HISTORY_SENTINEL != RAW_HISTORY_SENTINEL
    assert BUNDLE_HISTORY_SENTINEL not in RAW_HISTORY_SENTINEL
    assert RAW_HISTORY_SENTINEL not in BUNDLE_HISTORY_SENTINEL


def test_probes_deliver_the_sentinels_by_the_two_distinct_paths() -> None:
    bundle = history_probe_bundle()
    raw = raw_history_probe()
    assert bundle.conversation_history_window[0].content == BUNDLE_HISTORY_SENTINEL
    assert raw[0].content == RAW_HISTORY_SENTINEL
    # The raw sentinel must not be reachable through the bundle at all.
    assert all(
        RAW_HISTORY_SENTINEL not in turn.content
        for turn in bundle.conversation_history_window
    )


def test_cs1_passes_an_adapter_that_uses_the_bundle_window() -> None:
    check_authoritative_history_is_serialized(GoodAdapter())


def test_cs1_catches_an_adapter_that_serializes_the_raw_history_argument() -> None:
    """The exact defect P-1 exists to prevent: shipping uncounted turns."""

    class UsesRawHistory(GoodAdapter):
        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            self._last = SerializedPrompt(
                history_texts=tuple(turn.content for turn in history)
            )
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="raw `history` argument"):
        check_authoritative_history_is_serialized(UsesRawHistory())


def test_cs1_catches_an_adapter_that_serializes_both_histories() -> None:
    class UsesBoth(GoodAdapter):
        def generate(self, prompt_bundle, history) -> ProviderResponse:
            self._last = SerializedPrompt(
                history_texts=(
                    *(t.content for t in prompt_bundle.conversation_history_window),
                    *(t.content for t in history),
                )
            )
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="raw `history` argument"):
        check_authoritative_history_is_serialized(UsesBoth())


def test_cs1_catches_raw_history_smuggled_into_static_content() -> None:
    """Searching only `history_texts` would miss this. `all_texts` does not."""

    class Smuggler(GoodAdapter):
        def generate(self, prompt_bundle, history) -> ProviderResponse:
            self._last = SerializedPrompt(
                static_texts=tuple(t.content for t in history),
                history_texts=tuple(
                    t.content for t in prompt_bundle.conversation_history_window
                ),
            )
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="raw `history` argument"):
        check_authoritative_history_is_serialized(Smuggler())


def test_cs1_catches_an_adapter_that_drops_the_authoritative_history() -> None:
    class DropsHistory(GoodAdapter):
        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            self._last = SerializedPrompt(static_texts=("system",))
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="did not serialize"):
        check_authoritative_history_is_serialized(DropsHistory())


def test_cs1_fails_an_adapter_that_cannot_be_inspected() -> None:
    """Unprovable is not the same as passing — the V-1 principle."""

    class Opaque:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(1000, 10)

        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="inspection contract"):
        check_authoritative_history_is_serialized(Opaque())


def test_cs1_fails_an_adapter_reporting_no_serialization() -> None:
    class Forgetful(GoodAdapter):
        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="reported no serialization"):
        check_authoritative_history_is_serialized(Forgetful())


def test_the_recording_serializer_cannot_read_the_raw_history_argument() -> None:
    """Correct behaviour is structural: the helper is never given `history`."""
    snapshot = RecordingSerializer().record(history_probe_bundle())
    assert snapshot.contains(BUNDLE_HISTORY_SENTINEL)
    assert not snapshot.contains(RAW_HISTORY_SENTINEL)


def test_serialized_prompt_reports_every_framework_string() -> None:
    snapshot = SerializedPrompt(
        static_texts=("s",), history_texts=("h",), latest_message="m"
    )
    assert snapshot.all_texts == ("s", "h", "m")
    assert snapshot.contains("h") and not snapshot.contains("zzz")


def test_p1_is_documented_in_the_provider_interface() -> None:
    """The rule must be findable where an adapter author reads the contract."""
    src = (PROVIDER / "ports.py").read_text(encoding="utf-8")
    assert "conversation_history_window` is the sole authoritative" in src
    assert "must not" in src


# =============================================================================
# T-1 / CS-3 — tokenizer and capabilities describe one model
# =============================================================================
def test_a_matched_binding_constructs_and_verifies() -> None:
    binding = a_binding()
    assert binding.identity_is_verified
    assert binding.tokenizer_identity == MODEL_A


def test_a_mismatched_binding_cannot_be_constructed() -> None:
    """T-1's real enforcement: the invalid state is unconstructible."""
    with pytest.raises(ProviderBindingError, match="wrong vocabulary"):
        ModelBinding(
            identity=MODEL_A,
            capabilities=ProviderCapabilities(1000, 10),
            tokenizer=FakeTokenizer(MODEL_B),
        )


def test_binding_error_is_a_normalised_provider_error() -> None:
    error = ProviderBindingError("x")
    assert isinstance(error, ProviderError)
    assert error.error_type is ProviderErrorType.INVALID_REQUEST


def test_an_anonymous_tokenizer_binds_but_is_recorded_unverified() -> None:
    """Not assumed to match — recorded as unproven, and CS-3 fails it."""
    binding = ModelBinding(
        identity=MODEL_A,
        capabilities=ProviderCapabilities(1000, 10),
        tokenizer=AnonymousTokenizer(),
    )
    assert binding.tokenizer_identity is None
    assert not binding.identity_is_verified


def test_cs3_passes_a_correctly_bound_adapter() -> None:
    check_tokenizer_and_capabilities_agree(GoodAdapter())


def test_cs3_catches_a_mismatched_identity() -> None:
    """A duck-typed binding that bypassed ModelBinding's own validation."""

    class FakeBinding:
        identity = MODEL_A
        capabilities = ProviderCapabilities(1000, 10)
        tokenizer_identity = MODEL_B

    class Bypasser(GoodAdapter):
        def get_capabilities(self) -> ProviderCapabilities:
            return FakeBinding.capabilities

        def model_binding(self):
            return FakeBinding()

    with pytest.raises(Exception, match="ModelBinding"):
        check_tokenizer_and_capabilities_agree(Bypasser())


def test_cs3_catches_a_real_binding_whose_tokenizer_identity_drifted() -> None:
    """Constructed valid, then mutated — the check re-verifies rather than trusts."""
    binding = a_binding()
    object.__setattr__(binding.tokenizer, "_identity", MODEL_B)
    with pytest.raises(Exception, match="bound to"):
        check_tokenizer_and_capabilities_agree(GoodAdapter(binding))


def test_cs3_catches_an_anonymous_tokenizer() -> None:
    binding = ModelBinding(
        identity=MODEL_A,
        capabilities=ProviderCapabilities(1000, 10),
        tokenizer=AnonymousTokenizer(),
    )
    with pytest.raises(Exception, match="declares no model identity"):
        check_tokenizer_and_capabilities_agree(GoodAdapter(binding))


def test_cs3_catches_capabilities_that_bypass_the_binding() -> None:
    """If get_capabilities disagrees with the binding, it is not one origin."""

    class TwoSources(GoodAdapter):
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(999_999, 1)

    with pytest.raises(Exception, match="single origin"):
        check_tokenizer_and_capabilities_agree(TwoSources())


def test_cs3_fails_an_adapter_exposing_no_binding() -> None:
    class Unbound:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(1000, 10)

        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            return ProviderResponse(text="ok")

    with pytest.raises(Exception, match="model_binding"):
        check_tokenizer_and_capabilities_agree(Unbound())


def test_model_identity_rejects_empty_parts() -> None:
    with pytest.raises(ValueError):
        ModelIdentity("", "m")
    with pytest.raises(ValueError):
        ModelIdentity("p", "   ")


def test_model_identity_equality_is_exact() -> None:
    assert ModelIdentity("p", "m") == ModelIdentity("p", "m")
    assert ModelIdentity("p", "m") != ModelIdentity("p", "M")
    assert str(ModelIdentity("p", "m")) == "p/m"


# =============================================================================
# P-2 — construction-time model binding
# =============================================================================
def test_generate_takes_no_model_parameter() -> None:
    """The frozen §9.6 signature is unchanged: bundle and history only."""
    import inspect

    params = list(inspect.signature(ProviderInterface.generate).parameters)
    assert params == ["self", "prompt_bundle", "history"]


def test_get_capabilities_takes_no_model_parameter() -> None:
    import inspect

    assert list(inspect.signature(ProviderInterface.get_capabilities).parameters) == [
        "self"
    ]


def test_the_prompt_bundle_carries_no_provider_configuration() -> None:
    """A model name in the bundle would make every upstream module provider-aware."""
    bundle = sample_bundle()
    fields = set(vars(type(bundle)).get("__slots__", ()))
    for forbidden in ("model", "provider", "temperature", "max_tokens", "api_key"):
        assert forbidden not in fields


def test_an_adapter_is_bound_to_one_identity_for_its_lifetime() -> None:
    adapter = GoodAdapter()
    first = adapter.model_binding().identity
    adapter.generate(sample_bundle(), ())
    assert adapter.model_binding().identity == first


def test_p2_is_documented_in_the_provider_interface() -> None:
    src = (PROVIDER / "ports.py").read_text(encoding="utf-8")
    assert "P-2" in src and "construction" in src


def test_the_bound_provider_protocol_is_separate_from_the_frozen_interface() -> None:
    """Satisfying ProviderInterface must not require the binding protocol."""

    class InterfaceOnly:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(1000, 10)

        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            return ProviderResponse()

    assert isinstance(InterfaceOnly(), ProviderInterface)
    assert not isinstance(InterfaceOnly(), ModelBoundProvider)
    assert isinstance(GoodAdapter(), ProviderInterface)
    assert isinstance(GoodAdapter(), ModelBoundProvider)
    assert isinstance(GoodAdapter(), PromptInspectable)


# =============================================================================
# C-1a — the scalar reserve also covers output
# =============================================================================
def test_capabilities_still_expose_exactly_the_four_phase_one_fields() -> None:
    """C-1a adds no field. max_output_tokens must not have appeared."""
    fields = set(ProviderCapabilities.__dataclass_fields__)
    assert fields == {
        "context_window",
        "serialization_reserve",
        "streaming_support",
        "tool_calling_support",
    }


def test_no_output_token_capability_was_introduced() -> None:
    for forbidden in ("max_output_tokens", "output_reserve", "output_tokens"):
        assert not hasattr(ProviderCapabilities(100, 1), forbidden)


def test_c1a_policy_is_documented_where_the_reserve_is_defined() -> None:
    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "runtime"
        / "models"
        / "provider.py"
    ).read_text(encoding="utf-8")
    assert "C-1a" in src
    assert "completion allocation" in src


def test_c1a_assertion_is_stated_in_the_provider_interface() -> None:
    src = (PROVIDER / "ports.py").read_text(encoding="utf-8")
    assert "output allocation <= context_window" in src


def test_module_five_arithmetic_was_not_changed() -> None:
    """The reserve enters the budget exactly once, as one scalar term."""
    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "runtime"
        / "budget"
        / "manager.py"
    ).read_text(encoding="utf-8")
    assert "reserved = caps.serialization_reserve + fixed_tokens + latest_tokens" in src
    for forbidden in ("max_output_tokens", "output_reserve", "runtime.provider"):
        assert forbidden not in src


# =============================================================================
# E-1 — malformed provider responses normalise to UNKNOWN
# =============================================================================
def test_an_unparseable_response_normalises_to_unknown() -> None:
    """The provider accepted the request; only its answer was unreadable."""
    vendor_failure = ValueError("response body was not valid JSON")
    try:
        try:
            raise vendor_failure
        except ValueError as exc:
            raise ProviderError("provider response could not be parsed") from exc
    except ProviderError as exc:
        assert exc.error_type is ProviderErrorType.UNKNOWN
        assert exc.__cause__ is vendor_failure


def test_a_malformed_response_is_not_an_invalid_request() -> None:
    """Blaming the caller for the provider's output would misroute retry policy."""
    assert (
        ProviderInvalidRequestError.error_type is ProviderErrorType.INVALID_REQUEST
    )
    assert ProviderError.error_type is not ProviderErrorType.INVALID_REQUEST


def test_a_genuinely_rejected_request_still_maps_to_invalid_request() -> None:
    """E-1 narrows INVALID_REQUEST; it does not empty it."""
    assert (
        ProviderInvalidRequestError("provider rejected the request").error_type
        is ProviderErrorType.INVALID_REQUEST
    )


def test_no_class_was_added_for_malformed_responses() -> None:
    """UNKNOWN exists so this needs no new type; per-shape classes erode the set."""
    import runtime.provider.errors as errors

    names = {n for n in dir(errors) if n.endswith("Error")}
    for forbidden in ("MalformedResponseError", "ProviderParseError", "ResponseError"):
        assert forbidden not in names


def test_the_normalised_error_set_did_not_grow_a_new_type() -> None:
    assert len(ProviderErrorType) == 7


def test_e1_rule_is_documented_in_the_error_module() -> None:
    src = (PROVIDER / "errors.py").read_text(encoding="utf-8")
    assert "E-1" in src
    assert "UNKNOWN" in src


# =============================================================================
# suite-level integration
# =============================================================================
def test_the_full_suite_runs_ten_checks_and_a_good_adapter_passes() -> None:
    report = run_conformance(GoodAdapter())
    assert report.passed, report.failures
    assert len(report.checks_run) == 10
    assert "check_authoritative_history_is_serialized" in report.checks_run
    assert "check_tokenizer_and_capabilities_agree" in report.checks_run


def test_the_suite_reports_both_new_failures_together() -> None:
    """An author sees every problem in one run, not the first one only."""

    class DoublyBroken:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(1000, 10)

        def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
            return ProviderResponse(text="ok")

    failures = " ".join(run_conformance(DoublyBroken()).failures)
    assert "inspection contract" in failures
    assert "model_binding" in failures


# =============================================================================
# diagnostics and ordering (conformance-suite robustness)
# =============================================================================
def test_a_failure_records_the_underlying_cause() -> None:
    """"declined with ProviderUnavailableError" does not say why.

    The first live run reduced a transient provider fault to an exception name,
    which is not enough to tell a 503 from a connection that never opened. The
    cause is chained already; the report must not discard it.
    """

    class Declining(GoodAdapter):
        def generate(self, prompt_bundle, history):  # noqa: ARG002
            error = ProviderError("Gemini service failure: 503 model overloaded")
            error.__cause__ = RuntimeError("APIError: upstream detail")
            raise error

    failures = " ".join(run_conformance(Declining()).failures)
    assert "503 model overloaded" in failures
    assert "caused by RuntimeError: APIError: upstream detail" in failures


def test_the_whole_cause_chain_is_recorded() -> None:
    """The innermost link is usually the informative one."""

    class Nested(GoodAdapter):
        def generate(self, prompt_bundle, history):  # noqa: ARG002
            inner = OSError("connection reset by peer")
            middle = RuntimeError("transport failed")
            middle.__cause__ = inner
            outer = ProviderError("provider declined")
            outer.__cause__ = middle
            raise outer

    failures = " ".join(run_conformance(Nested()).failures)
    assert "provider declined" in failures
    assert "caused by RuntimeError: transport failed" in failures
    assert "caused by OSError: connection reset by peer" in failures


def test_a_failure_without_a_cause_reads_unchanged() -> None:
    """Existing semantics preserved: no cause, no added noise."""

    class Unbound:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(1000, 10)

        def generate(self, prompt_bundle, history):  # noqa: ARG002
            return ProviderResponse(text="ok")

    failures = run_conformance(Unbound()).failures
    assert any("model_binding" in f for f in failures)
    assert not any("caused by" in f for f in failures)


def test_a_cause_cycle_does_not_hang_the_report() -> None:
    error = ProviderError("outer")
    error.__cause__ = error
    from runtime.provider.conformance import _with_cause

    assert _with_cause(error) == "outer"


def test_the_cheap_checks_run_before_the_oversized_ones() -> None:
    """`oversized_bundle` scales with the window: megabytes on a 1M model.

    CS-1 failed live purely because it ran straight after that traffic. Order
    carries no meaning here - the module documents every check as independent -
    so the small probes go first and the expensive pair goes last.
    """
    from runtime.provider.conformance import CHECKS

    order = [c.__name__ for c in CHECKS]
    cs1 = order.index("check_authoritative_history_is_serialized")
    cs3 = order.index("check_tokenizer_and_capabilities_agree")
    oversized = order.index("check_oversized_payload_fails_closed")
    normalised = order.index("check_errors_are_normalised")

    assert cs1 < oversized, "CS-1 must not run in the wake of a multi-MB upload"
    assert cs1 < normalised
    assert cs3 < oversized
    assert {oversized, normalised} == {len(order) - 2, len(order) - 1}


def test_the_oversized_checks_were_not_weakened() -> None:
    """Only their position changed. Same probe, same assertions."""
    from runtime.provider.conformance import (
        CHECKS,
        check_errors_are_normalised,
        check_oversized_payload_fails_closed,
        oversized_bundle,
    )

    assert len(CHECKS) == 10
    assert check_oversized_payload_fails_closed in CHECKS
    assert check_errors_are_normalised in CHECKS

    # still sized from the declared window, still genuinely oversized
    small = oversized_bundle(ProviderCapabilities(100, 0))
    large = oversized_bundle(ProviderCapabilities(100_000, 0))
    assert len(large.static_sections[0].content) > len(small.static_sections[0].content)

    class Truncating(GoodAdapter):
        def generate(self, prompt_bundle, history):  # noqa: ARG002
            return ProviderResponse(text="I shortened it")

    assert "fails_closed" in " ".join(run_conformance(Truncating()).failures)


def test_cs2_boundary_is_recorded_not_silently_assumed() -> None:
    """The suite must not imply it proved a real provider's window."""
    src = (PROVIDER / "conformance.py").read_text(encoding="utf-8")
    assert "CS-2" in src
    assert "live call" in src


def test_no_live_call_tier_was_implemented() -> None:
    src = (PROVIDER / "conformance.py").read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "http", "socket", "api_key"):
        assert f"import {forbidden}" not in src


# =============================================================================
# independence — the new modules must stay provider-neutral
# =============================================================================
def test_the_new_modules_name_no_vendor() -> None:
    for name in ("binding.py", "inspection.py"):
        src = (PROVIDER / name).read_text(encoding="utf-8").lower()
        for vendor in ("openai", "anthropic", "gemini", "claude", "gpt-", "mistral", "cohere"):
            assert vendor not in src, f"{name} names {vendor}"


def test_the_new_modules_import_no_sdk() -> None:
    for name in ("binding.py", "inspection.py"):
        src = (PROVIDER / name).read_text(encoding="utf-8")
        for sdk in ("import openai", "import anthropic", "import tiktoken"):
            assert sdk not in src


def test_the_provider_layer_still_depends_only_on_shared_models() -> None:
    """Extends the existing scan to the two modules added this phase."""
    for path in PROVIDER.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for forbidden in (
            "runtime.validation",
            "runtime.loader",
            "runtime.resolver",
            "runtime.assembler",
            "runtime.budget",
        ):
            assert forbidden not in src, f"{path.name} references {forbidden}"


def test_identities_used_anywhere_in_tests_are_fake() -> None:
    """No real provider or model name may enter the repository via a fixture."""
    for identity in (MODEL_A, MODEL_B):
        assert identity.provider_id.startswith("fake-")
        assert identity.model_id.startswith("fake-")


def test_history_probe_turns_are_ordinary_provider_neutral_turns() -> None:
    for turn in (*history_probe_bundle().conversation_history_window, *raw_history_probe()):
        assert isinstance(turn, Turn)
        assert turn.role in (TurnRole.USER, TurnRole.AGENT)
