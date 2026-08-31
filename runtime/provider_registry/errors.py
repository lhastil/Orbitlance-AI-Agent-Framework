"""Provider Registry failures.

Two families, deliberately separated by *when* they can happen.

**Registration-time** failures (`DuplicateProviderError`,
`UnidentifiableProviderError`) are assembly errors: they occur while a process
is being wired together, before any conversation exists. They subclass
`ValueError`, following the precedent `runtime.validation.registry` set with
`DuplicateRuleError` — *labelled as precedent, not as specification.* No clause
of §10 describes them, because §10 does not describe registration at all.

**Lookup- and call-time** failures subclass `ProviderError`, the normalised set
§9.9 defines. That is not a stylistic choice: the Runtime Engine's provider
stage will already be catching `ProviderError`, and a registry failure arriving
as something else would escape the handler §14.9 requires.

**No error here carries a provider SDK exception.** The one concrete adapter in
this repository goes to deliberate lengths to keep a raw vendor exception —
"whose message and request URL may carry the credential" — off the traceback.
Everything this module ever chains is an already-normalised `ProviderError`,
which has been through that redaction. Nothing widens it back.
"""

from __future__ import annotations

from runtime.models.provider import ProviderErrorType
from runtime.provider.errors import ProviderError


class DuplicateProviderError(ValueError):
    """Two adapters claim the same `provider_id`.

    Registration rejects rather than overwrites (ruled). A silent overwrite
    would let the adapter behind a provider id change *after* the Validation
    Layer confirmed that id was registered, which defeats §10.10's whole point:
    the check is done at activation time precisely so nothing changes underneath
    it mid-conversation.

    Because the registry is keyed by `provider_id` alone (ruled), two adapters
    for the same vendor at different models collide here. That is a real
    consequence of the key, not an oversight — see `ProviderRegistry` for where
    the declared model is then checked.
    """


class UnidentifiableProviderError(ValueError):
    """A candidate adapter does not expose the binding its identity lives in.

    Registration derives the key from the adapter's own
    `model_binding().identity` rather than accepting a caller-supplied name. A
    caller-supplied key could disagree with the adapter behind it, and nothing
    would ever notice — the registry would answer `is_registered` truthfully
    about a name while holding an adapter that name does not describe.

    Requiring `ModelBoundProvider` costs nothing an adapter does not already
    owe: §9.10 requires every adapter to pass the shared conformance suite
    before registration, and that suite's CS-3 check fails outright for an
    adapter without `model_binding()`.
    """


class ProviderNotRegisteredError(ProviderError):
    """The project's declared provider is not in this registry.

    `INVALID_REQUEST` rather than a new normalised type, matching how
    `ProviderBindingError` and `ProviderCapabilityUnavailableError` already
    classify themselves: a misconfiguration the caller must fix, not a transient
    condition worth retrying.

    §10.10 states this must be "caught as a configuration error at Validation
    Layer time, not mid-conversation", and §14.10 makes passing validation a
    hard precondition for accepting any request. So reaching this exception
    means an activation gate was bypassed, not that a conversation hit a normal
    edge. It is raised rather than absorbed for exactly that reason.
    """

    error_type = ProviderErrorType.INVALID_REQUEST


class ProviderModelMismatchError(ProviderError):
    """The registered adapter is bound to a different model than config declares.

    The registry routes on `provider_id`; this is the second half of that
    ruling. `ModelIdentity` is a *pair*, and the framework's own note on it is
    that "tokenizers and context windows vary across a vendor's own model
    families" — so resolving a vendor name and shipping whichever of that
    vendor's models happens to be registered would send a project's traffic to a
    model it never selected, with a different window and a different vocabulary,
    silently.

    An **absent or placeholder** declared model raises this too. It is the same
    comparison, not a special case: neither `None` nor a template placeholder
    equals the model string an adapter is bound to. Treating an unstated model as
    agreement would be "could not be checked" counting as "passed", which this
    framework has refused everywhere else. It does mean the declared Model is
    effectively required at routing time while the Validation Layer requires
    only the Primary — recorded in `docs/known-issues-runtime.md` as PR-2.
    """

    error_type = ProviderErrorType.INVALID_REQUEST


class AllProvidersFailedError(ProviderError):
    """Every configured provider failed (§10.9).

    §10.9's terminal outcome: "if none configured or it also fails, surface a
    clear 'technical difficulties' outcome to Runtime Engine." This is that
    outcome, expressed as a raised exception.

    **Not** a `ProviderResponse` carrying an `error_type`. The frozen Data
    Models table names the "Provider Interface implementation" the *sole writer*
    of `ProviderResponse`; this module is named sole writer of `ProviderRequest`
    and of nothing else. Constructing a response here would make a second
    writer of a type whose ownership is frozen.

    **It carries no user-facing text.** The phrase "technical difficulties"
    appears exactly once in this repository — in §10.9 itself — and
    `core/prompts/09_fallback_responses.md` has no technical-failure entry to
    draw from. Composing what the customer reads is §14's degraded-response
    job, informed by this exception; inventing wording here would put a
    user-visible string in a module that owns none.

    `error_type` stays `UNKNOWN`, inherited. Exhaustion is not itself a rate
    limit, a timeout or an outage — it is the aggregate of whatever the
    attempts were — and `runtime.provider.errors` states that `UNKNOWN` "exists
    precisely so that an honest 'this does not fit a category' needs no new
    type". Picking one of the attempted classes would misreport the aggregate as
    a single cause.
    """

    def __init__(self, message: str, attempts: tuple[tuple[str, str], ...] = ()) -> None:
        super().__init__(message)
        #: `(provider_id, error_type_value)` per attempt, in the order tried.
        #: Values only — never an SDK exception, never a credential.
        self.attempts = attempts
