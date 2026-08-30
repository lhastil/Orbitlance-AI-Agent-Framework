"""Gemini token counting — exact, from the provider, never estimated.

Gemini publishes no local tokenizer. The authoritative count comes from the
`countTokens` endpoint, which returns the same number the model itself will
charge. That is what this module calls, and it is the *only* honest option:

* no character-per-token ratio;
* no heuristic;
* no fallback tokenizer for when the call fails;
* no cached approximation.

Module 5's `TokenizerPort` says raising is the correct response to an
unavailable tokenizer, because an estimate would make an approximate budget
indistinguishable from an exact one. That rule is followed literally here — a
failed count propagates as a normalised `ProviderError` and the budget fails
closed rather than proceeding on a guess.

**The cost this imposes is real and worth stating plainly:** every count is a
network round-trip, so budgeting a turn with this tokenizer makes several calls
and requires a credential. That is inherent to Gemini, not a choice this
adapter made, and the alternative — estimating locally — is exactly what the
authorization forbids.
"""

from __future__ import annotations

from typing import Any

from runtime.provider.adapters.gemini.count_request import count_request_tokens
from runtime.provider.adapters.gemini.errors import raise_normalised
from runtime.provider.binding import ModelIdentity


class GeminiTokenizer:
    """Counts tokens for one specific Gemini model, via the provider's own API.

    Bound to a `ModelIdentity` at construction and immutable thereafter. The
    identity it reports is what CS-3 compares against the adapter's capabilities:
    a tokenizer for a different Gemini model would count precisely against the
    wrong vocabulary, which is a wrong answer that looks exact.
    """

    __slots__ = ("_client", "_identity", "_model")

    def __init__(self, client: Any, identity: ModelIdentity) -> None:
        self._client = client
        self._identity = identity
        self._model = identity.model_id

    def model_identity(self) -> ModelIdentity:
        return self._identity

    def count_tokens(self, text: str) -> int:
        """The exact token cost of `text` for this model.

        Deterministic: identical input against the same model returns the same
        count. Raises rather than approximating if the provider cannot answer.
        """
        return self._count(contents=text)

    def count_request_tokens(self, contents: Any, system_instruction: Any) -> int:
        """The exact cost of a whole serialized request, system block included.

        Used for the adapter's final pre-call assertion. Counting the assembled
        request rather than summing its pieces is deliberate: tokenization is
        not additive, so a sum would understate the real payload — the defect
        Module 4 v1.7 was written to eliminate, reappearing one layer down.

        Delegates to `count_request`, which sends the Developer API's
        `generateContentRequest` shape. That shape is the only one carrying
        `systemInstruction`, and the SDK cannot build it — see that module for
        why the escape hatch is necessary and why every alternative is worse.
        """
        return count_request_tokens(
            self._client, self._model, list(contents), system_instruction
        )

    def _count(self, *, contents: Any, config: Any = None) -> int:
        failure = None
        try:
            response = self._client.models.count_tokens(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001 - every vendor failure normalises
            failure = raise_normalised(exc)
        if failure is not None:
            # Outside the except block: no raw SDK exception in `__context__`,
            # so nothing credential-bearing rides along in the traceback.
            raise failure from failure.__cause__

        total = getattr(response, "total_tokens", None)
        if not isinstance(total, int) or total < 0:
            from runtime.provider.adapters.gemini.errors import unparseable_response

            raise unparseable_response(
                f"countTokens returned {total!r} rather than a token count"
            )
        return total
