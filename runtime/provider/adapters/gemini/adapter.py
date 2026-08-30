"""The Gemini adapter — a concrete `ProviderInterface` for gemini-3.6-flash.

The first concrete adapter. It is **not** a default: nothing selects it, no
project configuration names it, and the framework above `ProviderInterface`
cannot tell it apart from any future adapter.

**Capabilities come from the provider, not from documentation.** `models.get`
returns `input_token_limit`, `output_token_limit` and `supported_actions` for
the exact model; those are read once at construction and cached, so
`get_capabilities()` afterwards answers without a live call as §9.2 requires.
If the metadata cannot be fetched, construction fails with
`ProviderCapabilityUnavailableError` — no window size is assumed, because a
guessed number would reach the Token Budget Manager wearing the authority of a
measured one.

**Credentials never enter this class.** It is constructed with an already-built
client. `from_environment()` is the one place a key is read, straight from the
environment into the SDK, never stored on the adapter, never logged, never
placed in an exception.

**On the model bound here.** `gemini-2.5-flash` was the first choice and proved
unusable: for this credential the API serves its metadata but refuses inference.
`models.get` succeeded while `countTokens` and `generateContent` both returned
404. That is worth recording because of what it implies — **metadata
availability is not proof of usability on this provider.** A construction-time
usability probe is the obvious answer and is deliberately *not* built here; it
is a separate architectural decision, and until it is taken, a catalogue-visible
but gated model would construct cleanly and fail at first use.
"""

from __future__ import annotations

import os
from typing import Any

from runtime.models.conversation import Turn
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import (
    ProviderCapabilities,
    ProviderMetadata,
    ProviderResponse,
)
from runtime.provider.adapters.gemini.errors import (
    raise_normalised,
    unparseable_response,
)
from runtime.provider.adapters.gemini.serializer import GeminiSerializer
from runtime.provider.adapters.gemini.tokenizer import GeminiTokenizer
from runtime.provider.binding import ModelBinding, ModelIdentity
from runtime.provider.errors import (
    ContextWindowExceededError,
    ProviderCapabilityUnavailableError,
    ProviderError,
)
from runtime.provider.inspection import SerializedPrompt

#: This adapter's permanent identity. Not configurable: a context window and a
#: tokenizer vocabulary are facts about one specific model, so an adapter that
#: could be re-pointed could not answer a capability query honestly.
PROVIDER_ID = "google"
MODEL_ID = "gemini-3.6-flash"
GEMINI_IDENTITY = ModelIdentity(PROVIDER_ID, MODEL_ID)

#: Environment names checked, in order, by `from_environment()`.
CREDENTIAL_VARIABLES: tuple[str, ...] = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

#: Declared allowance for Gemini's request envelope — role markers and JSON
#: framing around content this framework never sees. Declared rather than
#: measured because §9 assigns serialization to the adapter, and backed by an
#: exact pre-call assertion: if this proves too small, `generate` fails closed
#: rather than overflowing. Deliberately generous; the window is ~1M tokens, so
#: conservatism here costs nothing worth optimising.
DEFAULT_ENVELOPE_RESERVE = 2_048


class GeminiAdapter:
    """`ProviderInterface` + `ModelBoundProvider` + `PromptInspectable`."""

    __slots__ = ("_binding", "_client", "_last", "_serializer", "_supported_actions")

    def __init__(
        self,
        client: Any,
        *,
        envelope_reserve: int = DEFAULT_ENVELOPE_RESERVE,
        sdk_types: Any = None,
    ) -> None:
        if envelope_reserve < 0:
            raise ValueError("envelope_reserve cannot be negative")
        self._client = client
        self._serializer = GeminiSerializer(sdk_types)
        self._last: SerializedPrompt | None = None

        model = self._fetch_model_metadata()
        self._supported_actions = tuple(getattr(model, "supported_actions", None) or ())
        capabilities = self._capabilities_from(model, envelope_reserve)

        # T-1: one construction is the single origin of identity, capabilities
        # and tokenizer. A mismatched pair cannot survive this line.
        self._binding = ModelBinding(
            identity=GEMINI_IDENTITY,
            capabilities=capabilities,
            tokenizer=GeminiTokenizer(client, GEMINI_IDENTITY),
        )

    # --- construction helpers -------------------------------------------------
    @classmethod
    def from_environment(cls, **kwargs: Any) -> GeminiAdapter:
        """Build a live adapter, reading the credential from the environment.

        The key is passed straight to the SDK and never retained here. If it is
        absent this raises before any network call, naming the variables that
        were checked and never their contents.
        """
        from google.genai import Client  # noqa: PLC0415

        for variable in CREDENTIAL_VARIABLES:
            key = os.environ.get(variable)
            if key:
                return cls(Client(api_key=key), **kwargs)
        raise ProviderCapabilityUnavailableError(
            "no Gemini credential in the environment; set one of "
            + ", ".join(CREDENTIAL_VARIABLES)
        )

    def _fetch_model_metadata(self) -> Any:
        normalised: ProviderError | None = None
        try:
            return self._client.models.get(model=MODEL_ID)
        except Exception as exc:  # noqa: BLE001 - normalised, never leaked raw
            normalised = raise_normalised(exc)
        raise ProviderCapabilityUnavailableError(
            f"Gemini model metadata for {MODEL_ID} could not be established: "
            f"{normalised}"
        ) from normalised.__cause__

    def _capabilities_from(
        self, model: Any, envelope_reserve: int
    ) -> ProviderCapabilities:
        window = getattr(model, "input_token_limit", None)
        output_limit = getattr(model, "output_token_limit", None)
        if not isinstance(window, int) or not isinstance(output_limit, int):
            raise ProviderCapabilityUnavailableError(
                f"Gemini reported no usable token limits for {MODEL_ID} "
                f"(input={window!r}, output={output_limit!r}); this adapter does "
                "not assume a window size"
            )
        # C-1a: one scalar reserve covering the envelope *and* the completion
        # allocation, since nothing upstream reserves room for output.
        reserve = output_limit + envelope_reserve
        if reserve >= window:
            raise ProviderCapabilityUnavailableError(
                f"Gemini's declared output limit ({output_limit}) plus envelope "
                f"({envelope_reserve}) leaves no room in a {window}-token window"
            )
        return ProviderCapabilities(
            context_window=window,
            serialization_reserve=reserve,
            streaming_support="streamGenerateContent" in self._supported_actions,
            # Not establishable from `models.get`: Gemini publishes no
            # tool-calling field there. This adapter implements no tool path, so
            # declaring True would be a claim it cannot honour (§9.10 makes
            # misreporting a conformance failure). Recorded as an owner decision.
            tool_calling_support=False,
        )

    # --- ProviderInterface ----------------------------------------------------
    def get_capabilities(self) -> ProviderCapabilities:
        """Cached from construction. Makes no call, per §9.2."""
        return self._binding.capabilities

    def generate(
        self, prompt_bundle: PromptBundle, history: tuple[Turn, ...]
    ) -> ProviderResponse:
        """Serialize, assert the payload fits, call Gemini, normalise the reply.

        `history` is deliberately unused. P-1: the only authoritative history is
        `prompt_bundle.conversation_history_window`, which the Token Budget
        Manager selected and counted. Serializing the raw argument would ship
        turns nothing measured.
        """
        del history  # observability/audit only — never serialized (P-1)

        request = self._serializer.serialize(prompt_bundle)
        self._assert_fits(request)

        failure: ProviderError | None = None
        try:
            response = self._client.models.generate_content(
                model=MODEL_ID,
                contents=request.contents,
                config=self._generation_config(request),
            )
        except Exception as exc:  # noqa: BLE001 - normalised, never leaked raw
            failure = raise_normalised(exc)
        if failure is not None:
            # Raised outside the except block on purpose: that leaves
            # `__context__` empty, so the raw SDK exception - whose message and
            # request URL may carry the credential - is not attached to the
            # traceback at all. The redacted cause carries the diagnostic.
            raise failure from failure.__cause__

        self._last = request.neutral
        return self._normalise_response(response)

    # --- ModelBoundProvider / PromptInspectable -------------------------------
    def model_binding(self) -> ModelBinding:
        return self._binding

    def last_serialized_prompt(self) -> SerializedPrompt | None:
        return self._last

    # --- internals ------------------------------------------------------------
    def _generation_config(self, request: Any) -> Any:
        if request.system_instruction is None:
            return None
        from google.genai import types  # noqa: PLC0415

        return types.GenerateContentConfig(
            system_instruction=request.system_instruction
        )

    def _assert_fits(self, request: Any) -> None:
        """C-1a's final assertion, before the call. Fails closed, never trims.

        The count is of the *assembled* request, not a sum of its parts:
        tokenization is not additive, and a sum would understate the payload.
        """
        capabilities = self._binding.capabilities
        counted = self._binding.tokenizer.count_request_tokens(
            request.contents, request.system_instruction
        )
        total = counted + capabilities.serialization_reserve
        if total > capabilities.context_window:
            raise ContextWindowExceededError(
                f"serialized request is {counted} tokens; with the declared "
                f"reserve of {capabilities.serialization_reserve} that is "
                f"{total}, exceeding the {capabilities.context_window}-token "
                "window. The budget was decided upstream against counted "
                "content, so this adapter fails rather than sending less."
            )

    def _normalise_response(self, response: Any) -> ProviderResponse:
        """Gemini's reply into `ProviderResponse`. No SDK type escapes."""
        try:
            text = response.text
        except Exception as exc:  # noqa: BLE001 - E-1: unreadable, not invalid
            raise unparseable_response(f"reading response text failed: {exc}") from None
        if text is None:
            # A blocked or empty candidate is a real outcome, not a crash: the
            # Guardrail Engine and Runtime Engine decide what to do with it.
            text = ""
        if not isinstance(text, str):
            raise unparseable_response(f"response text was {type(text).__name__}")

        usage = getattr(response, "usage_metadata", None)
        return ProviderResponse(
            text=text,
            metadata=ProviderMetadata(
                model=getattr(response, "model_version", None) or MODEL_ID,
                input_tokens=getattr(usage, "prompt_token_count", None),
                output_tokens=getattr(usage, "candidates_token_count", None),
            ),
        )
