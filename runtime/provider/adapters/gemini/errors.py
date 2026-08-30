"""Gemini error translation — vendor exceptions into the normalised set (§9.9).

This module is the *only* place in the repository that knows what a Gemini
error looks like. Everything above `ProviderInterface` sees the normalised
hierarchy from `runtime.provider.errors` and never branches on vendor identity.

Two rules govern everything here:

* **Never let a credential escape.** Messages and causes are redacted before
  they are attached to a normalised error, because an authentication failure is
  exactly the moment a key is most likely to appear in a diagnostic string.
* **A request the provider accepted is not an invalid request.** E-1: a response
  the adapter cannot parse normalises to `UNKNOWN`, never `INVALID_REQUEST` —
  blaming the caller for the provider's own output would misroute retry policy.
"""

from __future__ import annotations

import re

from runtime.provider.errors import (
    ContextWindowExceededError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

#: Anything resembling a key in a vendor message is removed before the text is
#: re-raised. Deliberately broad: over-redacting a diagnostic costs clarity,
#: under-redacting one leaks a secret into logs that may outlive the process.
_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"AIza[0-9A-Za-z_\-]{10,}"), "[redacted-credential]"),
    (re.compile(r"(?i)(api[_\- ]?key\s*[=:]\s*)\S+"), r"\1[redacted-credential]"),
    (re.compile(r"(?i)(bearer\s+)\S+"), r"\1[redacted-credential]"),
    (re.compile(r"(?i)(authorization\s*[=:]\s*)\S+"), r"\1[redacted-credential]"),
    (re.compile(r"(?i)([?&]key=)[^&\s]+"), r"\1[redacted-credential]"),
)

#: Substrings that identify a 400 as a token/context failure rather than a
#: malformed request. Matched case-insensitively against the redacted message.
_WINDOW_MARKERS: tuple[str, ...] = (
    "token count",
    "exceeds the maximum number of tokens",
    "input token count",
    "context length",
    "too many tokens",
    "request payload size",
)


def redact(text: str) -> str:
    """Strip anything credential-shaped from a vendor diagnostic."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class _RedactedCauseError(Exception):
    """A vendor exception's detail, with credentials removed.

    The original SDK exception is deliberately **not** chained: its `args`,
    attributes and repr may carry the request URL, which carries the key. This
    preserves the diagnostic content the contract asks for while guaranteeing
    the credential cannot travel with it.
    """


def _cause(exc: BaseException) -> _RedactedCauseError:
    return _RedactedCauseError(f"{type(exc).__name__}: {redact(str(exc))}")


def _status_code(exc: BaseException) -> int | None:
    """The HTTP status of a Gemini `APIError`, if this is one.

    Read structurally rather than by isinstance so this function stays usable
    when the SDK is absent, and so a wrapped or subclassed error still maps.
    """
    code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def normalise_api_error(exc: BaseException) -> ProviderError:
    """Translate a Gemini SDK exception into the normalised set.

    Unmapped statuses fall to `UNKNOWN` rather than earning a new class —
    growing the hierarchy per vendor is what normalisation exists to prevent.
    """
    message = redact(str(exc))
    status = _status_code(exc)

    if status in (401, 403):
        return ProviderAuthenticationError(
            "Gemini rejected the credential"
        ).with_traceback(None)
    if status == 429:
        return ProviderRateLimitError(f"Gemini throttled the request: {message}")
    if status in (408, 504):
        return ProviderTimeoutError(f"Gemini timed out: {message}")
    if status == 400:
        lowered = message.lower()
        if any(marker in lowered for marker in _WINDOW_MARKERS):
            return ContextWindowExceededError(
                f"Gemini reported a token-limit failure: {message}"
            )
        return ProviderInvalidRequestError(f"Gemini rejected the request: {message}")
    if status == 404:
        return ProviderInvalidRequestError(f"Gemini resource not found: {message}")
    if status is not None and 500 <= status < 600:
        return ProviderUnavailableError(f"Gemini service failure: {message}")
    if _is_transport_timeout(exc):
        return ProviderTimeoutError(f"Gemini transport timed out: {message}")
    if _is_transport_failure(exc):
        return ProviderUnavailableError(f"Gemini was unreachable: {message}")

    if _is_client_side_refusal(exc):
        # The SDK rejected the call before sending anything. Still UNKNOWN --
        # the normalised set is fixed and `INVALID_REQUEST` means the *provider*
        # rejected a request, which did not happen here. Only the wording
        # improves, so an operator can tell a local misuse from a remote fault.
        return ProviderError(
            "Gemini SDK rejected the call locally; no request was sent "
            f"(client-side misuse, not a provider failure): {message}"
        )

    # E-1: unclassifiable, and honestly labelled as such.
    return ProviderError(f"Unclassified Gemini failure: {message}")


def unparseable_response(detail: str) -> ProviderError:
    """E-1: the request succeeded; the answer could not be read.

    `UNKNOWN`, not `INVALID_REQUEST`. Gemini accepted the request, so nothing
    about the request was invalid, and a caller that retried an "invalid
    request" would be following the wrong policy for the wrong reason.
    """
    return ProviderError(f"Gemini response could not be interpreted: {redact(detail)}")


def raise_normalised(exc: BaseException) -> ProviderError:
    """Build the normalised error with a redacted cause attached."""
    normalised = normalise_api_error(exc)
    normalised.__cause__ = _cause(exc)
    return normalised


def _is_client_side_refusal(exc: BaseException) -> bool:
    """A `ValueError`/`TypeError` from the SDK, raised before any network call.

    The Developer API transformers refuse Vertex-only fields this way -- see
    `_CountTokensConfig_to_mldev`. Such a failure carries no HTTP status because
    nothing was ever sent.
    """
    return isinstance(exc, (ValueError, TypeError)) and _status_code(exc) is None


def _is_transport_timeout(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    return "timeout" in name or isinstance(exc, TimeoutError)


def _is_transport_failure(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    return any(marker in name for marker in ("connect", "network", "transport"))
