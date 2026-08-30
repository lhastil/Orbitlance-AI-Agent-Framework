"""The one place this repository bypasses the Gemini SDK's typed surface.

**Why this exists.** Counting a `PromptBundle` exactly requires counting the
system instruction along with the conversation, because tokenization is not
additive — `count(system) + count(contents)` is not `count(system + contents)`.
The Gemini Developer API supports this. The Python SDK does not:

* `models.countTokens` accepts either `contents` **or** `generateContentRequest`,
  and only the latter carries `systemInstruction` (REST reference: the two are
  *"mutually exclusive… but never both"*);
* `google-genai` 2.20.0 contains **zero** references to `generateContentRequest`,
  so `client.models.count_tokens()` cannot build that shape at all;
* passing `CountTokensConfig(system_instruction=…)` is refused **client-side**,
  before any network call, by `_CountTokensConfig_to_mldev`:
  *"system_instruction parameter is only supported in Gemini Enterprise Agent
  Platform mode, not in Gemini Developer API mode."* It is a Vertex-only field.

Every alternative violates a rule the framework does not bend:

* **Estimate locally.** No local Gemini tokenizer exists, and an estimate makes
  an approximate budget indistinguishable from an exact one.
* **Count the parts and add them.** Non-additive: the Module 4 v1.7 defect,
  one layer down.
* **Count `contents` and skip the system block.** Silently under-counts by the
  entire static prompt — ~26k characters on the sunrise corpus.
* **Fold static sections into `contents`.** Works, but destroys true
  system-instruction semantics: the model would be told the same words in a
  different role.

So the escape hatch is the honest option, and it is confined to this module and
to the single function below. `BaseApiClient.request` is a public method reached
through the private `_api_client` attribute; that is the whole extent of the
unsupported surface, and it is the reason this module exists separately rather
than being spread through the tokenizer.

**Fidelity is the point.** The body is built from the *same* SDK objects the
adapter is about to ship, dumped through the SDK's own alias-aware serializer.
The request that is counted is therefore the request that is sent, which is the
guarantee the whole render-then-count seam exists to provide.

**Revisit when:** the SDK gains `generateContentRequest` support, or
`CountTokensConfig.system_instruction` becomes valid on the Developer API. At
that point this module should collapse into a plain `models.count_tokens` call.
"""

from __future__ import annotations

import json
from typing import Any

from runtime.provider.adapters.gemini.errors import (
    raise_normalised,
    unparseable_response,
)


def build_count_body(
    model_id: str, contents: list[Any], system_instruction: Any
) -> dict[str, Any]:
    """The exact `countTokens` request body for a bundle, in wire form.

    Separated from the call so a test can assert that what gets counted matches
    what gets shipped, without a network round-trip.

    `by_alias=True` is required, not cosmetic: the SDK's Python field names are
    snake_case and the wire protocol is camelCase (`inline_data` versus
    `inlineData`). Dumping without aliases would send field names the API does
    not recognise, and text-only payloads would hide the bug until the first
    non-text part appeared.
    """
    request: dict[str, Any] = {
        "model": f"models/{model_id}",
        "contents": [_wire(content) for content in contents],
    }
    if system_instruction is not None:
        request["systemInstruction"] = _wire(system_instruction)
    return {"generateContentRequest": request}


def count_request_tokens(
    client: Any, model_id: str, contents: list[Any], system_instruction: Any
) -> int:
    """Exact token cost of the assembled request, system instruction included.

    Raises a normalised `ProviderError` on any failure. Never estimates, never
    falls back to a partial count: a budget that cannot be measured must fail
    closed rather than proceed on a number nothing verified.
    """
    body = build_count_body(model_id, contents, system_instruction)
    transport = getattr(client, "_api_client", None)
    if transport is None or not hasattr(transport, "request"):
        raise unparseable_response(
            "the Gemini client exposes no request transport, so the exact "
            "countTokens request shape cannot be sent"
        )

    failure = None
    try:
        response = transport.request(
            "post", f"models/{model_id}:countTokens", body, None
        )
    except Exception as exc:  # noqa: BLE001 - every vendor failure normalises
        failure = raise_normalised(exc)
    if failure is not None:
        # Raised outside the except block so the raw SDK exception - whose
        # message and request URL can carry the credential - is not attached to
        # the traceback through `__context__`.
        raise failure from failure.__cause__

    return _total_tokens(getattr(response, "body", None))


def _wire(value: Any) -> Any:
    """One SDK object as the API's JSON, or a plain dict passed through."""
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if dump is None:
        raise unparseable_response(
            f"cannot serialize {type(value).__name__} into a countTokens request"
        )
    return dump(mode="json", exclude_none=True, by_alias=True)


def _total_tokens(body: Any) -> int:
    if not body:
        raise unparseable_response("countTokens returned an empty response body")
    try:
        payload = json.loads(body)
    except (TypeError, ValueError) as exc:
        raise unparseable_response(f"countTokens response was not JSON: {exc}") from None

    total = payload.get("totalTokens") if isinstance(payload, dict) else None
    if not isinstance(total, int) or total < 0:
        raise unparseable_response(
            f"countTokens returned {total!r} rather than a token count"
        )
    return total
