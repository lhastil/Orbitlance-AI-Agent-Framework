"""Gemini adapter — offline tests. No credential, no network, no live call.

These exercise the **real adapter**: the real serializer, the real tokenizer
wrapper, the real error mapping, the real binding and the real capability
derivation. Only the transport is stubbed, so everything the adapter actually
decides is under test. The one thing a stub cannot prove is what a live Gemini
returns — that belongs to the gated live tests, and is not claimed here.

Skipped entirely when the optional `gemini` extra is not installed, so the
baseline suite passes with or without it.
"""

from __future__ import annotations

import inspect
import json
import pathlib

import pytest

pytest.importorskip("google.genai", reason="optional [gemini] extra not installed")

from google.genai import types  # noqa: E402

from runtime.models.conversation import Turn, TurnRole  # noqa: E402
from runtime.models.prompt_bundle import (  # noqa: E402
    PromptBundle,
    PromptSection,
    PromptSlot,
)
from runtime.models.provider import ProviderCapabilities, ProviderResponse  # noqa: E402
from runtime.provider import (  # noqa: E402
    ContextWindowExceededError,
    ModelBinding,
    ModelBoundProvider,
    PromptInspectable,
    ProviderAuthenticationError,
    ProviderCapabilityUnavailableError,
    ProviderError,
    ProviderErrorType,
    ProviderInterface,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    run_conformance,
)
from runtime.provider.adapters.gemini import (  # noqa: E402
    GEMINI_IDENTITY,
    MODEL_ID,
    PROVIDER_ID,
    GeminiAdapter,
    GeminiSerializer,
    GeminiTokenizer,
    build_count_body,
)
from runtime.provider.adapters.gemini.errors import (  # noqa: E402
    normalise_api_error,
    redact,
    unparseable_response,
)

GEMINI_DIR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "runtime"
    / "provider"
    / "adapters"
    / "gemini"
)

#: Values the stub reports as if they came from `models.get`. Chosen to differ
#: from any published figure so a test can never accidentally pass because a
#: number was hard-coded somewhere.
STUB_INPUT_LIMIT = 500_000
STUB_OUTPUT_LIMIT = 40_000
STUB_ACTIONS = ("generateContent", "streamGenerateContent", "countTokens")


class StubApiError(Exception):
    """Shaped like `google.genai.errors.APIError`: carries an int `code`."""

    def __init__(self, code: int, message: str = "stub failure") -> None:
        super().__init__(message)
        self.code = code


class StubModels:
    """The transport boundary, and nothing else."""

    def __init__(
        self,
        *,
        input_limit: int = STUB_INPUT_LIMIT,
        output_limit: int = STUB_OUTPUT_LIMIT,
        actions: tuple[str, ...] = STUB_ACTIONS,
        token_count: int | None = None,
        get_raises: Exception | None = None,
        generate_raises: Exception | None = None,
        count_raises: Exception | None = None,
        response: object | None = None,
    ) -> None:
        self._input_limit = input_limit
        self._output_limit = output_limit
        self._actions = actions
        self.token_count = token_count
        self._get_raises = get_raises
        self._generate_raises = generate_raises
        self._count_raises = count_raises
        self._response = response
        self.generate_calls: list[dict] = []
        self.count_calls: list[dict] = []

    def get(self, *, model: str):
        if self._get_raises is not None:
            raise self._get_raises
        return types.Model(
            name=f"models/{model}",
            input_token_limit=self._input_limit,
            output_token_limit=self._output_limit,
            supported_actions=list(self._actions),
        )

    def count_tokens(self, *, model, contents, config=None):
        """Mirrors the Developer API, refusals included.

        `_CountTokensConfig_to_mldev` in google-genai rejects three Vertex-only
        fields client-side, before any request is sent. The stub must reject
        them too: a stub more permissive than the API is how an adapter passes
        offline and fails live, which is exactly what happened once already.
        """
        if config is not None:
            for field in ("system_instruction", "tools", "generation_config"):
                if getattr(config, field, None) is not None:
                    raise ValueError(
                        f"{field} parameter is only supported in Gemini "
                        "Enterprise Agent Platform mode, not in Gemini "
                        "Developer API mode."
                    )
        if self._count_raises is not None:
            raise self._count_raises
        self.count_calls.append({"model": model, "contents": contents, "config": config})
        total = self.token_count if self.token_count is not None else len(str(contents))
        return types.CountTokensResponse(total_tokens=total)

    def generate_content(self, *, model, contents, config=None):
        if self._generate_raises is not None:
            raise self._generate_raises
        self.generate_calls.append(
            {"model": model, "contents": contents, "config": config}
        )
        if self._response is not None:
            return self._response
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model", parts=[types.Part(text="hello back")]
                    )
                )
            ],
            model_version=MODEL_ID,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=11, candidates_token_count=3
            ),
        )


class StubApiClient:
    """The raw HTTP boundary, mirroring `BaseApiClient.request`.

    Only `models/<id>:countTokens` with a `generateContentRequest` body is
    understood - the one shape the escape hatch sends. Anything else is a 400,
    so a malformed body fails here instead of passing silently.
    """

    def __init__(self, models: StubModels) -> None:
        self._models = models
        self.requests: list[dict] = []

    def request(self, http_method, path, request_dict, http_options=None):  # noqa: ARG002
        if self._models._count_raises is not None:
            raise self._models._count_raises
        if not path.endswith(":countTokens") or http_method != "post":
            raise StubApiError(404, f"unsupported path {path}")
        inner = request_dict.get("generateContentRequest")
        if inner is None:
            raise StubApiError(400, "countTokens body lacked generateContentRequest")
        self.requests.append(request_dict)
        total = (
            self._models.token_count
            if self._models.token_count is not None
            else self._measure(inner)
        )
        return types.HttpResponse(body=json.dumps({"totalTokens": total}))

    @staticmethod
    def _measure(inner: dict) -> int:
        """Deterministic stand-in for tokenization.

        Grows with the payload - a constant would let an oversized request look
        like it fits and the fail-closed check would never fire - and counts the
        system instruction, so a serializer that dropped it would be caught.
        """
        return len(json.dumps(inner.get("contents", []))) + len(
            json.dumps(inner.get("systemInstruction", {}))
        )


class StubClient:
    def __init__(self, **kwargs) -> None:
        self.models = StubModels(**kwargs)
        self._api_client = StubApiClient(self.models)


def an_adapter(**kwargs) -> GeminiAdapter:
    return GeminiAdapter(StubClient(**kwargs))


def a_bundle(
    *,
    history: tuple[Turn, ...] = (Turn(TurnRole.USER, "earlier question"),),
    latest: str = "the latest question",
) -> PromptBundle:
    return PromptBundle(
        project_id="p",
        conversation_id="c",
        static_sections=(
            PromptSection(
                slot=PromptSlot.CORE_PERSONALITY,
                sources=("core/prompts/01_core_personality.md",),
                content="PERSONALITY TEXT",
            ),
            PromptSection(
                slot=PromptSlot.MISSION,
                sources=("core/prompts/02_mission.md",),
                content="MISSION TEXT",
            ),
        ),
        conversation_history_window=history,
        latest_message=latest,
    )


# =============================================================================
# conformance — the authorized suite, unmodified, against the real adapter
# =============================================================================
def test_the_real_adapter_passes_the_full_conformance_suite() -> None:
    report = run_conformance(an_adapter())
    assert report.passed, report.failures
    assert len(report.checks_run) == 10


def test_the_adapter_satisfies_all_three_contracts() -> None:
    adapter = an_adapter()
    assert isinstance(adapter, ProviderInterface)
    assert isinstance(adapter, ModelBoundProvider)
    assert isinstance(adapter, PromptInspectable)


# =============================================================================
# model binding (§3) and CS-3
# =============================================================================
def test_the_adapter_is_bound_to_the_authorized_identity() -> None:
    assert PROVIDER_ID == "google"
    assert MODEL_ID == "gemini-3.6-flash"
    assert an_adapter().model_binding().identity == GEMINI_IDENTITY


def test_the_tokenizer_declares_the_same_identity_as_the_adapter() -> None:
    binding = an_adapter().model_binding()
    assert binding.identity_is_verified
    assert binding.tokenizer_identity == GEMINI_IDENTITY


def test_identity_is_stable_across_calls_and_generations() -> None:
    adapter = an_adapter()
    before = adapter.model_binding().identity
    adapter.generate(a_bundle(), ())
    assert adapter.model_binding().identity == before
    assert adapter.get_capabilities() == adapter.model_binding().capabilities


def test_a_tokenizer_for_another_model_fails_closed() -> None:
    """A different Gemini model, a different provider, an unknown model."""
    from runtime.provider.binding import ModelIdentity
    from runtime.provider.errors import ProviderBindingError

    for wrong in (
        ModelIdentity("google", "gemini-3.6-pro"),
        ModelIdentity("some-other-provider", "gemini-3.6-flash"),
        ModelIdentity("unknown", "unknown-model"),
    ):
        with pytest.raises(ProviderBindingError):
            ModelBinding(
                identity=GEMINI_IDENTITY,
                capabilities=ProviderCapabilities(1000, 10),
                tokenizer=GeminiTokenizer(StubClient(), wrong),
            )


def test_generate_takes_no_model_argument() -> None:
    import inspect

    params = list(inspect.signature(GeminiAdapter.generate).parameters)
    assert params == ["self", "prompt_bundle", "history"]


# =============================================================================
# capabilities (§7) — authoritative, never guessed
# =============================================================================
def test_capabilities_come_from_the_model_metadata_not_a_constant() -> None:
    caps = an_adapter().get_capabilities()
    assert caps.context_window == STUB_INPUT_LIMIT
    # C-1a: the reserve carries the completion allocation plus the envelope.
    assert caps.serialization_reserve > STUB_OUTPUT_LIMIT
    assert caps.serialization_reserve < caps.context_window


def test_a_different_reported_window_produces_different_capabilities() -> None:
    """Proves the value is read, not hard-coded."""
    other = GeminiAdapter(StubClient(input_limit=123_456, output_limit=1_000))
    assert other.get_capabilities().context_window == 123_456


def test_streaming_support_is_derived_from_supported_actions() -> None:
    assert an_adapter().get_capabilities().streaming_support is True
    without = GeminiAdapter(StubClient(actions=("generateContent", "countTokens")))
    assert without.get_capabilities().streaming_support is False


def test_tool_calling_support_is_reported_conservatively() -> None:
    """Not establishable from models.get; the adapter implements no tool path."""
    assert an_adapter().get_capabilities().tool_calling_support is False


def test_capabilities_are_answered_without_a_call() -> None:
    adapter = an_adapter()
    before = len(adapter._client.models.count_calls)  # noqa: SLF001
    adapter.get_capabilities()
    adapter.get_capabilities()
    assert len(adapter._client.models.count_calls) == before  # noqa: SLF001


def test_capabilities_are_stable_across_queries() -> None:
    adapter = an_adapter()
    assert adapter.get_capabilities() == adapter.get_capabilities()


def test_unavailable_metadata_fails_closed_rather_than_assuming_a_window() -> None:
    with pytest.raises(ProviderCapabilityUnavailableError):
        GeminiAdapter(StubClient(get_raises=StubApiError(503, "unavailable")))


def test_missing_token_limits_fail_closed() -> None:
    with pytest.raises(ProviderCapabilityUnavailableError, match="no usable token"):
        GeminiAdapter(StubClient(input_limit=None, output_limit=None))


def test_an_output_limit_that_fills_the_window_fails_closed() -> None:
    with pytest.raises(ProviderCapabilityUnavailableError, match="no room"):
        GeminiAdapter(StubClient(input_limit=1_000, output_limit=999))


def test_no_output_capability_field_was_introduced() -> None:
    caps = an_adapter().get_capabilities()
    assert set(type(caps).__dataclass_fields__) == {
        "context_window",
        "serialization_reserve",
        "streaming_support",
        "tool_calling_support",
    }


# =============================================================================
# serialization (§8, §9, §10) — counted content is shipped content
# =============================================================================
def test_history_comes_from_the_bundle_window_only() -> None:
    adapter = an_adapter()
    adapter.generate(
        a_bundle(history=(Turn(TurnRole.USER, "BUDGETED-TURN"),)),
        (Turn(TurnRole.USER, "RAW-ARGUMENT-TURN"),),
    )
    payload = str(adapter._client.models.generate_calls[0]["contents"])  # noqa: SLF001
    assert "BUDGETED-TURN" in payload
    assert "RAW-ARGUMENT-TURN" not in payload


def test_excluded_turns_cannot_reappear_through_the_raw_argument() -> None:
    """Module 5 truncated these; the adapter must not restore them."""
    adapter = an_adapter()
    excluded = (Turn(TurnRole.USER, "DROPPED-1"), Turn(TurnRole.AGENT, "DROPPED-2"))
    adapter.generate(a_bundle(history=()), excluded)
    payload = str(adapter._client.models.generate_calls[0]["contents"])  # noqa: SLF001
    assert "DROPPED-1" not in payload and "DROPPED-2" not in payload


def test_the_serializer_is_never_given_the_raw_history() -> None:
    """Structural: the correct behaviour is the only reachable one."""
    import inspect

    params = list(inspect.signature(GeminiSerializer.serialize).parameters)
    assert params == ["self", "prompt_bundle"]


def test_static_sections_are_preserved_exactly_and_in_order() -> None:
    request = GeminiSerializer(types).serialize(a_bundle())
    texts = [part.text for part in request.system_instruction.parts]
    assert texts == ["PERSONALITY TEXT", "MISSION TEXT"]


def test_static_sections_are_not_joined_into_one_string() -> None:
    """A join would add characters nothing counted — the v1.7 defect, one layer down."""
    request = GeminiSerializer(types).serialize(a_bundle())
    assert len(request.system_instruction.parts) == 2


def test_provenance_metadata_never_reaches_the_payload() -> None:
    request = GeminiSerializer(types).serialize(a_bundle())
    payload = str(request.system_instruction) + str(request.contents)
    for leaked in ("core/prompts/", "sources", "is_from_playbook", ".md"):
        assert leaked not in payload


def test_no_hidden_instruction_is_injected() -> None:
    request = GeminiSerializer(types).serialize(a_bundle())
    shipped = "".join(part.text for part in request.system_instruction.parts)
    assert shipped == "PERSONALITY TEXTMISSION TEXT"


def test_the_latest_message_is_authoritative_and_appears_once() -> None:
    adapter = an_adapter()
    adapter.generate(a_bundle(latest="THE-LATEST"), (Turn(TurnRole.USER, "OTHER"),))
    payload = str(adapter._client.models.generate_calls[0]["contents"])  # noqa: SLF001
    assert payload.count("THE-LATEST") == 1
    assert "OTHER" not in payload


def test_the_latest_message_is_the_final_turn() -> None:
    request = GeminiSerializer(types).serialize(a_bundle(latest="FINAL"))
    assert request.contents[-1].parts[0].text == "FINAL"
    assert request.contents[-1].role == "user"


def test_roles_map_to_geminis_vocabulary_inside_the_adapter_only() -> None:
    request = GeminiSerializer(types).serialize(
        a_bundle(history=(Turn(TurnRole.USER, "u"), Turn(TurnRole.AGENT, "a")))
    )
    assert [c.role for c in request.contents] == ["user", "model", "user"]


def test_the_caller_bundle_is_not_mutated() -> None:
    adapter = an_adapter()
    bundle = a_bundle()
    before = (
        bundle.static_sections,
        bundle.conversation_history_window,
        bundle.latest_message,
    )
    adapter.generate(bundle, (Turn(TurnRole.USER, "raw"),))
    assert (
        bundle.static_sections,
        bundle.conversation_history_window,
        bundle.latest_message,
    ) == before


def test_an_empty_history_window_serializes_only_the_latest_message() -> None:
    request = GeminiSerializer(types).serialize(a_bundle(history=()))
    assert len(request.contents) == 1


# =============================================================================
# CS-1 / PromptInspectable (§15)
# =============================================================================
def test_the_inspection_report_matches_what_was_serialized() -> None:
    adapter = an_adapter()
    adapter.generate(a_bundle(), (Turn(TurnRole.USER, "RAW"),))
    snapshot = adapter.last_serialized_prompt()
    assert snapshot.static_texts == ("PERSONALITY TEXT", "MISSION TEXT")
    assert snapshot.history_texts == ("earlier question",)
    assert snapshot.latest_message == "the latest question"
    assert not snapshot.contains("RAW")


def test_the_inspection_report_exposes_no_sdk_object_or_secret() -> None:
    adapter = an_adapter()
    adapter.generate(a_bundle(), ())
    rendered = repr(adapter.last_serialized_prompt())
    for leaked in ("Content(", "Part(", "google", "genai", "api_key", "role="):
        assert leaked not in rendered


def test_nothing_is_reported_before_the_first_call() -> None:
    assert an_adapter().last_serialized_prompt() is None


def test_a_failed_call_reports_no_serialization() -> None:
    """A request that never shipped must not be reported as one that did."""
    adapter = an_adapter(generate_raises=StubApiError(429, "slow down"))
    with pytest.raises(ProviderRateLimitError):
        adapter.generate(a_bundle(), ())
    assert adapter.last_serialized_prompt() is None


# =============================================================================
# the final pre-call assertion (§7) — fail closed, never truncate
# =============================================================================
def test_an_oversized_request_raises_before_the_call() -> None:
    adapter = an_adapter(token_count=STUB_INPUT_LIMIT)
    with pytest.raises(ContextWindowExceededError):
        adapter.generate(a_bundle(), ())
    assert adapter._client.models.generate_calls == []  # noqa: SLF001


def test_the_assertion_includes_the_declared_reserve() -> None:
    """Just inside the window on content alone, but over once reserve is added."""
    caps = an_adapter().get_capabilities()
    just_under = caps.context_window - caps.serialization_reserve + 1
    adapter = an_adapter(token_count=just_under)
    with pytest.raises(ContextWindowExceededError):
        adapter.generate(a_bundle(), ())


def test_a_request_that_exactly_fits_is_sent() -> None:
    caps = an_adapter().get_capabilities()
    adapter = an_adapter(token_count=caps.context_window - caps.serialization_reserve)
    assert adapter.generate(a_bundle(), ()).text == "hello back"


def test_the_assertion_counts_the_assembled_request_not_a_sum_of_parts() -> None:
    """Tokenization is not additive; a sum would understate the payload.

    One countTokens call carrying the whole request - never one per piece.
    """
    adapter = an_adapter()
    adapter.generate(a_bundle(), ())
    sent = adapter._client._api_client.requests  # noqa: SLF001
    assert len(sent) == 1, "the request is counted once, as a whole"
    inner = sent[0]["generateContentRequest"]
    assert isinstance(inner["contents"], list)
    assert "systemInstruction" in inner, "the system block must be counted too"


def test_overflow_never_truncates_or_retries() -> None:
    adapter = an_adapter(token_count=STUB_INPUT_LIMIT)
    with pytest.raises(ContextWindowExceededError, match="fails rather than sending"):
        adapter.generate(a_bundle(), ())
    assert adapter._client.models.generate_calls == []  # noqa: SLF001


# =============================================================================
# tokenizer (§6) — exact, deterministic, no fallback
# =============================================================================
def test_the_tokenizer_returns_the_providers_exact_count() -> None:
    tokenizer = GeminiTokenizer(StubClient(token_count=4242), GEMINI_IDENTITY)
    assert tokenizer.count_tokens("anything") == 4242


def test_the_tokenizer_is_deterministic_for_identical_input() -> None:
    tokenizer = GeminiTokenizer(StubClient(token_count=17), GEMINI_IDENTITY)
    assert tokenizer.count_tokens("same") == tokenizer.count_tokens("same")


def test_a_tokenizer_failure_propagates_rather_than_estimating() -> None:
    tokenizer = GeminiTokenizer(
        StubClient(count_raises=StubApiError(503, "down")), GEMINI_IDENTITY
    )
    with pytest.raises(ProviderUnavailableError):
        tokenizer.count_tokens("text")


def test_an_unusable_count_is_not_silently_replaced() -> None:
    class BadCount(StubClient):
        def __init__(self) -> None:
            super().__init__()
            self.models.count_tokens = lambda **kw: types.CountTokensResponse()  # noqa: ARG005

    with pytest.raises(ProviderError, match="rather than a token count"):
        GeminiTokenizer(BadCount(), GEMINI_IDENTITY).count_tokens("x")


def test_no_character_ratio_or_fallback_appears_in_the_tokenizer() -> None:
    src = (GEMINI_DIR / "tokenizer.py").read_text(encoding="utf-8")
    for forbidden in ("len(text) /", "len(text)//", "* 0.", "/ 4", "// 4", "except:"):
        assert forbidden not in src


def test_module_five_can_use_the_tokenizer_without_knowing_the_provider() -> None:
    from runtime.budget.ports import TokenizerPort

    assert isinstance(GeminiTokenizer(StubClient(), GEMINI_IDENTITY), TokenizerPort)


# =============================================================================
# error normalization (§12)
# =============================================================================
@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (429, ProviderRateLimitError),
        (408, ProviderTimeoutError),
        (504, ProviderTimeoutError),
        (400, ProviderInvalidRequestError),
        (404, ProviderInvalidRequestError),
        (500, ProviderUnavailableError),
        (503, ProviderUnavailableError),
    ],
)
def test_status_codes_map_to_the_normalised_set(code, expected) -> None:
    assert isinstance(normalise_api_error(StubApiError(code)), expected)


def test_a_token_limit_rejection_maps_to_context_window_exceeded() -> None:
    error = normalise_api_error(
        StubApiError(400, "input token count exceeds the maximum number of tokens")
    )
    assert isinstance(error, ContextWindowExceededError)


def test_an_unmapped_status_maps_to_unknown_not_a_new_class() -> None:
    error = normalise_api_error(StubApiError(418))
    assert type(error) is ProviderError
    assert error.error_type is ProviderErrorType.UNKNOWN


def test_an_unparseable_response_maps_to_unknown_not_invalid_request() -> None:
    """E-1: Gemini accepted the request; only its answer was unreadable."""
    error = unparseable_response("not json")
    assert error.error_type is ProviderErrorType.UNKNOWN
    assert error.error_type is not ProviderErrorType.INVALID_REQUEST


def test_a_broken_response_object_normalises_rather_than_crashing() -> None:
    class Exploding:
        @property
        def text(self):
            raise ValueError("cannot decode")

    adapter = an_adapter(response=Exploding())
    with pytest.raises(ProviderError) as caught:
        adapter.generate(a_bundle(), ())
    assert caught.value.error_type is ProviderErrorType.UNKNOWN


def test_no_raw_sdk_exception_escapes_generate() -> None:
    adapter = an_adapter(generate_raises=StubApiError(500, "boom"))
    with pytest.raises(ProviderError):
        adapter.generate(a_bundle(), ())


def test_a_normalised_error_keeps_a_redacted_diagnostic_cause() -> None:
    error = None
    try:
        an_adapter(generate_raises=StubApiError(429, "quota")).generate(a_bundle(), ())
    except ProviderError as exc:
        error = exc
    assert error is not None
    assert error.__cause__ is not None
    assert "quota" in str(error.__cause__)


# =============================================================================
# credential policy (§4)
# =============================================================================
def test_credentials_are_redacted_from_vendor_diagnostics() -> None:
    for secret, text in (
        ("AIzaSyA1234567890abcdefgh", "failed with key AIzaSyA1234567890abcdefgh"),
        ("s3cret", "api_key=s3cret rejected"),
        ("tok123", "Bearer tok123 invalid"),
        ("abc987", "https://host/v1?key=abc987&alt=json"),
    ):
        assert secret not in redact(text)
        assert "[redacted-credential]" in redact(text)


def test_an_auth_failure_carries_no_credential_anywhere() -> None:
    leaked = "AIzaSyLEAKED0000000000000"
    adapter = an_adapter(
        generate_raises=StubApiError(401, f"invalid key {leaked} for request")
    )
    with pytest.raises(ProviderAuthenticationError) as caught:
        adapter.generate(a_bundle(), ())
    assert leaked not in str(caught.value)
    assert leaked not in str(caught.value.__cause__)
    assert leaked not in repr(caught.value.__cause__)


def test_the_adapter_never_stores_a_credential() -> None:
    adapter = an_adapter()
    for slot in type(adapter).__slots__:
        rendered = repr(getattr(adapter, slot, None)).lower()
        assert "api_key" not in rendered
        assert "aiza" not in rendered


def test_no_credential_literal_exists_in_the_adapter_source() -> None:
    """A real key, not the redaction pattern that exists to catch one."""
    import re

    for path in GEMINI_DIR.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        found = re.search(r"AIza[0-9A-Za-z_\-]{20,}", src)
        assert found is None, f"{path.name} contains a key-shaped literal"


def test_a_missing_credential_fails_before_any_network_call(monkeypatch) -> None:
    for variable in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ProviderCapabilityUnavailableError, match="no Gemini credential"):
        GeminiAdapter.from_environment()


def test_capabilities_and_response_carry_no_credential_field() -> None:
    adapter = an_adapter()
    response = adapter.generate(a_bundle(), ())
    assert isinstance(response, ProviderResponse)
    for rendered in (repr(adapter.get_capabilities()), repr(response)):
        assert "key" not in rendered.lower() or "api_key" not in rendered.lower()


# =============================================================================
# response normalization (§12)
# =============================================================================
def test_a_successful_response_normalises_to_provider_response() -> None:
    response = an_adapter().generate(a_bundle(), ())
    assert isinstance(response, ProviderResponse)
    assert response.text == "hello back"
    assert not response.failed
    assert response.metadata.model == MODEL_ID
    assert response.metadata.input_tokens == 11


def test_no_sdk_type_crosses_the_boundary() -> None:
    response = an_adapter().generate(a_bundle(), ())
    assert type(response).__module__.startswith("runtime.models")
    assert "google" not in repr(type(response.metadata))


def test_an_empty_candidate_is_an_empty_string_not_a_crash() -> None:
    adapter = an_adapter(response=types.GenerateContentResponse(candidates=[]))
    assert adapter.generate(a_bundle(), ()).text == ""


# =============================================================================
# streaming and tool calling (§13, §14) — capability reporting only
# =============================================================================
def test_no_streaming_implementation_was_added() -> None:
    adapter = an_adapter()
    assert not hasattr(adapter, "generate_stream")
    src = (GEMINI_DIR / "adapter.py").read_text(encoding="utf-8")
    assert "generate_content_stream" not in src


def test_no_streaming_protocol_was_created() -> None:
    import runtime.provider as provider_pkg

    assert not hasattr(provider_pkg, "StreamingProviderInterface")


def test_no_tool_execution_or_tool_models_were_added() -> None:
    src = " ".join(p.read_text(encoding="utf-8") for p in GEMINI_DIR.glob("*.py"))
    for forbidden in ("function_call", "ToolCall", "ToolDefinition", "ToolExecutor"):
        assert forbidden not in src


def test_provider_response_was_not_modified() -> None:
    assert set(ProviderResponse.__dataclass_fields__) == {
        "text",
        "metadata",
        "error_type",
        "raw_payload",
    }


# =============================================================================
# containment (§1, §17) — nothing Gemini escapes the subtree
# =============================================================================
def test_the_adapter_subtree_is_the_only_place_naming_gemini() -> None:
    runtime_root = GEMINI_DIR.parents[2]
    for path in runtime_root.rglob("*.py"):
        if "__pycache__" in str(path) or GEMINI_DIR in path.parents:
            continue
        src = path.read_text(encoding="utf-8").lower()
        if path == runtime_root / "provider" / "adapters" / "__init__.py":
            continue  # names the subpackage in prose; imports nothing
        assert "gemini" not in src, f"{path.name} names gemini"
        assert "google" not in src, f"{path.name} names google"


def test_the_adapter_imports_no_framework_module_it_should_not() -> None:
    for path in GEMINI_DIR.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for forbidden in (
            "runtime.validation",
            "runtime.loader",
            "runtime.resolver",
            "runtime.assembler",
        ):
            assert forbidden not in src, f"{path.name} imports {forbidden}"


def test_the_framework_imports_without_the_gemini_sdk() -> None:
    """The base install must not need the extra."""
    import importlib

    for module in ("runtime.provider", "runtime.budget.manager", "runtime.models"):
        assert importlib.import_module(module) is not None


def test_no_default_provider_was_introduced() -> None:
    import runtime.provider.adapters as adapters_pkg

    assert not hasattr(adapters_pkg, "GeminiAdapter")
    assert not hasattr(adapters_pkg, "DEFAULT_PROVIDER")


def test_the_gemini_sdk_is_an_optional_extra_only() -> None:
    pyproject = (GEMINI_DIR.parents[3] / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject
    assert 'gemini = ["google-genai' in pyproject


# =============================================================================
# Gemini 3.6 Flash metadata and identity
# =============================================================================
def test_the_bound_model_is_gemini_3_6_flash() -> None:
    assert MODEL_ID == "gemini-3.6-flash"
    assert GEMINI_IDENTITY.provider_id == "google"
    assert GEMINI_IDENTITY.model_id == "gemini-3.6-flash"


def test_no_reference_to_the_abandoned_model_remains() -> None:
    """2.5-flash serves metadata but refuses inference on this credential."""
    for path in GEMINI_DIR.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in src.splitlines() if not line.strip().startswith("#")
        )
        assert '"gemini-2.5-flash"' not in code, f"{path.name} still binds 2.5-flash"


def test_metadata_is_requested_for_the_bound_model() -> None:
    adapter = an_adapter()
    assert adapter.model_binding().identity.model_id == MODEL_ID


def test_capabilities_derive_from_the_reported_limits() -> None:
    """Live 3.6-flash reports 1,048,576 / 65,536; the adapter must read, not assume."""
    real = GeminiAdapter(StubClient(input_limit=1_048_576, output_limit=65_536))
    caps = real.get_capabilities()
    assert caps.context_window == 1_048_576
    assert caps.serialization_reserve == 65_536 + 2_048
    assert caps.streaming_support is True


# =============================================================================
# ISSUE 2 / Option A - exact countTokens request serialization
# =============================================================================
def test_the_count_body_uses_the_generate_content_request_shape() -> None:
    body = build_count_body(MODEL_ID, [], None)
    assert set(body) == {"generateContentRequest"}
    assert body["generateContentRequest"]["model"] == f"models/{MODEL_ID}"


def test_the_count_body_carries_the_system_instruction() -> None:
    request = GeminiSerializer(types).serialize(a_bundle())
    body = build_count_body(MODEL_ID, request.contents, request.system_instruction)
    inner = body["generateContentRequest"]
    assert inner["systemInstruction"]["parts"] == [
        {"text": "PERSONALITY TEXT"},
        {"text": "MISSION TEXT"},
    ]


def test_the_count_body_omits_system_instruction_when_there_is_none() -> None:
    body = build_count_body(MODEL_ID, [], None)
    assert "systemInstruction" not in body["generateContentRequest"]


def test_the_count_body_uses_wire_field_names() -> None:
    """camelCase, not the SDK's snake_case. Text-only payloads would hide this."""
    part = types.Part(inline_data=types.Blob(mime_type="text/plain", data=b"x"))
    body = build_count_body(MODEL_ID, [types.Content(role="user", parts=[part])], None)
    rendered = json.dumps(body)
    assert "inlineData" in rendered and "inline_data" not in rendered
    assert "mimeType" in rendered and "mime_type" not in rendered


def test_the_counted_request_is_exactly_the_shipped_request() -> None:
    """The whole point of Option A: count what ships, not something like it."""
    adapter = an_adapter()
    adapter.generate(a_bundle(), ())

    counted = adapter._client._api_client.requests[0]["generateContentRequest"]  # noqa: SLF001
    shipped = adapter._client.models.generate_calls[0]  # noqa: SLF001

    shipped_contents = [
        c.model_dump(mode="json", exclude_none=True, by_alias=True)
        for c in shipped["contents"]
    ]
    shipped_system = shipped["config"].system_instruction.model_dump(
        mode="json", exclude_none=True, by_alias=True
    )
    assert counted["contents"] == shipped_contents
    assert counted["systemInstruction"] == shipped_system
    assert counted["model"] == f"models/{MODEL_ID}"


def test_counting_happens_before_the_call_it_measures() -> None:
    adapter = an_adapter(token_count=10**9)
    with pytest.raises(ContextWindowExceededError):
        adapter.generate(a_bundle(), ())
    assert adapter._client._api_client.requests, "the request was counted"  # noqa: SLF001
    assert adapter._client.models.generate_calls == []  # noqa: SLF001


def test_the_system_block_changes_the_counted_total() -> None:
    """Live proof was 12 tokens without, 17 with. The stub must agree in kind."""
    request = GeminiSerializer(types).serialize(a_bundle())
    client = StubClient()
    with_sys = client._api_client._measure(  # noqa: SLF001
        build_count_body(MODEL_ID, request.contents, request.system_instruction)[
            "generateContentRequest"
        ]
    )
    without_sys = client._api_client._measure(  # noqa: SLF001
        build_count_body(MODEL_ID, request.contents, None)["generateContentRequest"]
    )
    assert with_sys > without_sys, "the system instruction must be counted"


def test_a_bad_count_response_is_not_silently_accepted() -> None:
    class BadBody(StubClient):
        def __init__(self) -> None:
            super().__init__()
            self._api_client.request = lambda *a, **k: types.HttpResponse(body="{}")  # noqa: ARG005

    with pytest.raises(ProviderError, match="rather than a token count"):
        GeminiAdapter(BadBody()).generate(a_bundle(), ())


def test_a_non_json_count_response_fails_closed() -> None:
    class NotJson(StubClient):
        def __init__(self) -> None:
            super().__init__()
            self._api_client.request = lambda *a, **k: types.HttpResponse(  # noqa: ARG005
                body="<html>"
            )

    with pytest.raises(ProviderError, match="not JSON"):
        GeminiAdapter(NotJson()).generate(a_bundle(), ())


def test_a_client_without_a_transport_fails_closed() -> None:
    """No transport means no exact count - and never an estimated one."""
    from runtime.provider.adapters.gemini.count_request import count_request_tokens

    class NoTransport:
        pass

    with pytest.raises(ProviderError, match="no request transport"):
        count_request_tokens(NoTransport(), MODEL_ID, [], None)


# =============================================================================
# D - the escape hatch is isolated and documented
# =============================================================================
def test_the_escape_hatch_lives_in_exactly_one_module() -> None:
    users = [
        path.name
        for path in GEMINI_DIR.glob("*.py")
        if "_api_client" in path.read_text(encoding="utf-8")
    ]
    assert users == ["count_request.py"], f"raw transport reached from {users}"


def test_the_escape_hatch_documents_why_it_is_required() -> None:
    src = (GEMINI_DIR / "count_request.py").read_text(encoding="utf-8")
    assert "generateContentRequest" in src
    assert "2.20.0" in src
    assert "additive" in src, "the non-additivity rationale must be recorded"
    assert "Revisit when" in src, "the exit condition must be recorded"


def test_no_estimation_or_fallback_entered_the_counting_path() -> None:
    src = (GEMINI_DIR / "count_request.py").read_text(encoding="utf-8")
    for forbidden in ("len(text)", "* 0.", "/ 4", "// 4", "except:", "return 0"):
        assert forbidden not in src


# =============================================================================
# F - the stub refuses what the real SDK refuses
# =============================================================================
@pytest.mark.parametrize(
    "field", ["system_instruction", "tools", "generation_config"]
)
def test_the_stub_rejects_vertex_only_count_config_fields(field) -> None:
    """A stub more permissive than the API is how live-only bugs survive."""
    kwargs = {
        "system_instruction": types.Content(parts=[types.Part(text="s")]),
        "tools": [types.Tool()],
        "generation_config": types.GenerationConfig(),
    }
    config = types.CountTokensConfig(**{field: kwargs[field]})
    with pytest.raises(ValueError, match="Developer API mode"):
        StubClient().models.count_tokens(model=MODEL_ID, contents="x", config=config)


def test_the_stub_matches_the_real_sdk_refusal() -> None:
    """Pinned against the SDK itself, so a version bump that relaxes it shows up."""
    from google.genai import models as sdk_models

    src = inspect.getsource(sdk_models._CountTokensConfig_to_mldev)
    for field in ("system_instruction", "tools", "generation_config"):
        assert field in src
    assert "not in Gemini Developer API mode" in src


def test_the_adapter_never_sends_a_vertex_only_count_config() -> None:
    adapter = an_adapter()
    adapter.generate(a_bundle(), ())
    for call in adapter._client.models.count_calls:  # noqa: SLF001
        assert call["config"] is None


# =============================================================================
# G - client-side SDK misuse is distinguishable from a provider fault
# =============================================================================
def test_a_client_side_refusal_is_labelled_as_such() -> None:
    error = normalise_api_error(
        ValueError(
            "system_instruction parameter is only supported in Gemini "
            "Enterprise Agent Platform mode, not in Gemini Developer API mode."
        )
    )
    assert "no request was sent" in str(error)
    assert "client-side misuse" in str(error)


def test_a_client_side_refusal_keeps_the_unknown_error_type() -> None:
    """Only the wording improved. The normalised set is unchanged."""
    error = normalise_api_error(ValueError("local refusal"))
    assert error.error_type is ProviderErrorType.UNKNOWN
    assert type(error) is ProviderError


def test_a_server_error_is_not_mislabelled_as_client_side() -> None:
    assert "client-side" not in str(normalise_api_error(StubApiError(500, "boom")))
    assert "client-side" not in str(normalise_api_error(StubApiError(400, "bad")))
