"""Normalised provider failures.

Specification §9.9 requires every concrete adapter to translate its vendor's
errors — rate limits, auth failures, timeouts — into a small, normalised set, so
that no other module ever needs provider-specific error handling. These are that
set.

An adapter that lets a raw SDK exception escape has not met the contract: the
conformance suite checks for exactly that. Wrapping preserves the original as
`__cause__`, so debugging keeps the vendor detail while the runtime above sees
only these types.

Nothing here imports a provider SDK, and nothing here is provider-specific. A
vendor error that fits no category maps to `UNKNOWN` rather than earning a new
class — growing this hierarchy per provider would defeat the normalisation it
exists to provide.
"""

from __future__ import annotations

from runtime.models.provider import ProviderErrorType


class ProviderError(Exception):
    """Base for every normalised provider failure.

    `error_type` lets a caller branch on the failure class without catching a
    specific subclass, which is what makes retry and fallback policy expressible
    without vendor knowledge.
    """

    error_type: ProviderErrorType = ProviderErrorType.UNKNOWN


class ProviderAuthenticationError(ProviderError):
    """Credentials were missing, malformed or rejected.

    Never carries the credential itself, in either the message or the cause.
    """

    error_type = ProviderErrorType.AUTHENTICATION


class ProviderRateLimitError(ProviderError):
    """The provider throttled the request.

    Retry policy is the Provider Registry's decision, not the adapter's — §9.3
    puts fallback squarely outside this boundary.
    """

    error_type = ProviderErrorType.RATE_LIMIT


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the adapter's limit."""

    error_type = ProviderErrorType.TIMEOUT


class ContextWindowExceededError(ProviderError):
    """The serialized payload would not fit the provider's context window.

    Raised by the adapter's final assertion, before the call. The adapter must
    not resolve this by trimming: the budget was decided by the Token Budget
    Manager against counted content, and silently sending less than was budgeted
    would make a second, hidden budget decision the runtime cannot see.
    """

    error_type = ProviderErrorType.CONTEXT_WINDOW_EXCEEDED


class ProviderInvalidRequestError(ProviderError):
    """The provider rejected the request as malformed or unsupported.

    **The provider rejected it.** This class is for a request the provider
    refused to process — not for a request the provider accepted and answered
    with something the adapter could not read. See E-1 below: a response the
    adapter cannot parse is not evidence that the request was invalid, and
    classifying it here would blame the caller for the provider's output and
    make retry policy wrong (an invalid request should not be retried; a garbled
    response reasonably may be).
    """

    error_type = ProviderErrorType.INVALID_REQUEST


class ProviderUnavailableError(ProviderError):
    """The provider was unreachable or returned a server-side failure."""

    error_type = ProviderErrorType.SERVICE_UNAVAILABLE


class ProviderCapabilityUnavailableError(ProviderError):
    """Capability metadata could not be established.

    §9.2 requires capabilities to be queryable without a live call, so this is a
    configuration failure rather than a transient one. No window size is
    assumed: guessing here would hand the Token Budget Manager an authoritative
    number that nothing measured.
    """

    error_type = ProviderErrorType.INVALID_REQUEST


class ProviderBindingError(ProviderError):
    """An adapter's tokenizer and capabilities describe different models (T-1).

    A construction failure, like `ProviderCapabilityUnavailableError`, not a
    transient one: it means the adapter was assembled from parts that do not
    belong together. Raised by `ModelBinding` before any call is made, because
    the damage a mismatched pair does is silent — Module 5 would count every
    string precisely against the wrong vocabulary and report success.

    `INVALID_REQUEST` rather than a new normalised type: the small error set is
    the contract, and this is a misconfiguration the caller must fix.
    """

    error_type = ProviderErrorType.INVALID_REQUEST


# --- E-1: what a malformed provider response normalises to --------------------
#
# A provider that accepts a request and answers with a body the adapter cannot
# parse has produced an **unclassifiable** failure, and it maps to
# `ProviderErrorType.UNKNOWN` — the base `ProviderError`.
#
# Not `INVALID_REQUEST`: the request was accepted, so nothing about it was
# invalid, and saying otherwise misattributes the failure to the caller.
# Not a new exception class either: growing this hierarchy per failure shape is
# how normalisation erodes, and `UNKNOWN` exists precisely so that an honest
# "this does not fit a category" needs no new type. The original vendor
# exception is preserved as `__cause__`, so the detail survives for debugging
# while the runtime above still sees only the normalised set.
#
# The one case that *is* `INVALID_REQUEST` is a failure genuinely attributable
# to the request — the provider said the request was bad, rather than the
# adapter finding the answer unreadable.

#: Maps a normalised type back to its exception class, for adapters translating
#: a vendor error they have already classified.
ERROR_BY_TYPE: dict[ProviderErrorType, type[ProviderError]] = {
    ProviderErrorType.AUTHENTICATION: ProviderAuthenticationError,
    ProviderErrorType.RATE_LIMIT: ProviderRateLimitError,
    ProviderErrorType.TIMEOUT: ProviderTimeoutError,
    ProviderErrorType.CONTEXT_WINDOW_EXCEEDED: ContextWindowExceededError,
    ProviderErrorType.INVALID_REQUEST: ProviderInvalidRequestError,
    ProviderErrorType.SERVICE_UNAVAILABLE: ProviderUnavailableError,
    ProviderErrorType.UNKNOWN: ProviderError,
}
