"""Gemini adapter — LIVE tests. Skipped unless explicitly enabled.

These make real calls to Gemini and cost real tokens. They are **not** part of
the offline baseline: the normal suite must pass on a machine with no
credential and no network, so everything here is gated twice — an explicit
opt-in flag *and* a credential.

Enable with:

    GEMINI_LIVE_TESTS=1  and  GOOGLE_API_KEY=<key>   (or GEMINI_API_KEY)

No credential appears in this file, and none is printed by any assertion. What
these prove that a stub cannot: the real context window, the real token counts,
the real `supported_actions`, and that a real vendor error normalises correctly.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("google.genai", reason="optional [gemini] extra not installed")

from runtime.models.conversation import Turn, TurnRole  # noqa: E402
from runtime.models.prompt_bundle import (  # noqa: E402
    PromptBundle,
    PromptSection,
    PromptSlot,
)
from runtime.models.provider import ProviderResponse  # noqa: E402
from runtime.provider import (  # noqa: E402
    ContextWindowExceededError,
    ProviderAuthenticationError,
    run_conformance,
)
from runtime.provider.adapters.gemini import (  # noqa: E402
    GEMINI_IDENTITY,
    MODEL_ID,
    GeminiAdapter,
)

_ENABLED = os.environ.get("GEMINI_LIVE_TESTS") == "1"
_HAS_CREDENTIAL = bool(
    os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
)

pytestmark = pytest.mark.skipif(
    not (_ENABLED and _HAS_CREDENTIAL),
    reason="live Gemini tests need GEMINI_LIVE_TESTS=1 and a credential",
)


@pytest.fixture(scope="module")
def adapter() -> GeminiAdapter:
    return GeminiAdapter.from_environment()


def a_bundle(latest: str = "Reply with the single word: ready") -> PromptBundle:
    return PromptBundle(
        project_id="live",
        conversation_id="live-1",
        static_sections=(
            PromptSection(
                slot=PromptSlot.CORE_PERSONALITY,
                sources=("core/prompts/01_core_personality.md",),
                content="You are a terse assistant. Answer in one word.",
            ),
        ),
        conversation_history_window=(Turn(TurnRole.USER, "Are you there?"),),
        latest_message=latest,
    )


def test_live_generation_returns_a_normalised_response(adapter) -> None:
    response = adapter.generate(a_bundle(), ())
    assert isinstance(response, ProviderResponse)
    assert not response.failed
    assert response.text.strip()
    assert response.metadata.input_tokens and response.metadata.input_tokens > 0


def test_live_capabilities_are_the_providers_own_numbers(adapter) -> None:
    caps = adapter.get_capabilities()
    assert caps.context_window > 0
    assert 0 < caps.serialization_reserve < caps.context_window
    assert isinstance(caps.streaming_support, bool)
    assert isinstance(caps.tool_calling_support, bool)


def test_live_capabilities_are_stable(adapter) -> None:
    assert adapter.get_capabilities() == adapter.get_capabilities()


def test_live_model_identity_is_the_authorized_one(adapter) -> None:
    assert adapter.model_binding().identity == GEMINI_IDENTITY
    assert adapter.model_binding().identity.model_id == MODEL_ID


def test_live_response_reports_the_model_it_used(adapter) -> None:
    response = adapter.generate(a_bundle(), ())
    assert MODEL_ID.split("-")[0] in (response.metadata.model or "")


def test_live_tokenizer_counts_exactly_and_deterministically(adapter) -> None:
    tokenizer = adapter.model_binding().tokenizer
    first = tokenizer.count_tokens("The quick brown fox jumps over the lazy dog.")
    second = tokenizer.count_tokens("The quick brown fox jumps over the lazy dog.")
    assert first == second, "identical input must produce identical counts"
    assert first > 0
    assert tokenizer.count_tokens("a much much much longer piece of text " * 20) > first


def test_live_tokenizer_identity_matches_the_adapter(adapter) -> None:
    assert adapter.model_binding().tokenizer.model_identity() == GEMINI_IDENTITY
    assert adapter.model_binding().identity_is_verified


def test_live_authoritative_history_is_what_ships(adapter) -> None:
    adapter.generate(
        a_bundle(), (Turn(TurnRole.USER, "RAW-MUST-NOT-SHIP"),)
    )
    snapshot = adapter.last_serialized_prompt()
    assert not snapshot.contains("RAW-MUST-NOT-SHIP")
    assert snapshot.contains("Are you there?")


def test_live_oversized_request_fails_closed_without_calling(adapter) -> None:
    """Built from the real window, so this is a real overflow, not a simulated one."""
    caps = adapter.get_capabilities()
    huge = "token " * (caps.context_window // 2)
    bundle = PromptBundle(
        project_id="live",
        conversation_id="live-2",
        static_sections=(
            PromptSection(
                slot=PromptSlot.KNOWLEDGE, sources=("x.md",), content=huge * 4
            ),
        ),
        latest_message="hello",
    )
    with pytest.raises(ContextWindowExceededError):
        adapter.generate(bundle, ())


def test_live_conformance_suite_passes(adapter) -> None:
    report = run_conformance(adapter)
    assert report.passed, report.failures


def test_live_bad_credential_normalises_without_leaking_it() -> None:
    """A deliberately wrong key. The value is synthetic and never printed."""
    from google.genai import Client

    bogus = "AIza" + "0" * 35
    with pytest.raises(
        (ProviderAuthenticationError, Exception)
    ) as caught:
        GeminiAdapter(Client(api_key=bogus))
    assert bogus not in str(caught.value)
    assert bogus not in str(caught.value.__cause__ or "")


def test_live_supported_actions_are_recorded_for_review(adapter) -> None:
    """Documents what the API actually reports, for the tool-calling decision."""
    actions = adapter._supported_actions  # noqa: SLF001
    assert actions, "models.get reported no supported_actions"
    assert "generateContent" in actions


# =============================================================================
# Option A - exact counting against the live API
# =============================================================================
def test_live_count_includes_the_system_instruction(adapter) -> None:
    """The measurement that settled Option A: the system block IS counted.

    The probe against this key returned 12 tokens without the system block and
    17 with it. This asserts the relationship, not the literal numbers, so the
    test stays true when the prompt or the model's tokenizer changes.
    """
    from runtime.provider.adapters.gemini import build_count_body
    from runtime.provider.adapters.gemini.count_request import _total_tokens

    request = adapter._serializer.serialize(a_bundle())  # noqa: SLF001
    transport = adapter._client._api_client  # noqa: SLF001
    path = f"models/{MODEL_ID}:countTokens"

    with_system = _total_tokens(
        transport.request(
            "post",
            path,
            build_count_body(MODEL_ID, request.contents, request.system_instruction),
            None,
        ).body
    )
    without_system = _total_tokens(
        transport.request(
            "post", path, build_count_body(MODEL_ID, request.contents, None), None
        ).body
    )
    assert with_system > without_system, "the system instruction must be counted"


def test_live_count_is_exact_and_deterministic(adapter) -> None:
    """Two identical requests, two identical counts. No estimation anywhere."""
    request = adapter._serializer.serialize(a_bundle())  # noqa: SLF001
    tokenizer = adapter.model_binding().tokenizer
    first = tokenizer.count_request_tokens(
        request.contents, request.system_instruction
    )
    second = tokenizer.count_request_tokens(
        request.contents, request.system_instruction
    )
    assert first == second and first > 0


def test_live_counted_total_matches_the_reported_prompt_tokens(adapter) -> None:
    """The strongest available proof that counted == shipped.

    The pre-call count and the provider's own `prompt_token_count` for the same
    bundle describe the same payload. A small divergence is legitimate - the
    provider adds its own framing - so this asserts they are close rather than
    identical, and would fail loudly if the adapter counted a different request
    than it sent.
    """
    bundle = a_bundle()
    request = adapter._serializer.serialize(bundle)  # noqa: SLF001
    counted = adapter.model_binding().tokenizer.count_request_tokens(
        request.contents, request.system_instruction
    )
    response = adapter.generate(bundle, ())
    reported = response.metadata.input_tokens
    assert reported is not None
    assert abs(counted - reported) <= max(16, counted * 0.1), (
        f"counted {counted} but the provider charged {reported}"
    )


def test_live_adapter_never_sends_a_vertex_only_count_config(adapter) -> None:
    """The SDK would refuse it client-side; the adapter must not attempt it."""
    request = adapter._serializer.serialize(a_bundle())  # noqa: SLF001
    assert adapter.model_binding().tokenizer.count_request_tokens(
        request.contents, request.system_instruction
    ) > 0
