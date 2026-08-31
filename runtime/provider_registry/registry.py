"""Provider Registry — specification §10.

Looks up the `ProviderInterface` implementation a project is configured for, and
routes one turn to it with the configured secondary as failover. It never calls
an LLM itself and never touches prompt content (§10.3): both members end in
delegation to an adapter that was built elsewhere.

**No provider SDK, no vendor name, no network, no environment.** This module
imports `runtime.provider` (the interface, the binding, the normalised errors)
and `runtime.models`, and nothing else from the runtime. It deliberately imports
no adapter subpackage: `runtime/provider/adapters/__init__.py` states that doing
so "would make every provider SDK a hard import of the provider layer, and would
give the framework a de facto default", and §10.8 gives this module no external
dependencies of its own. Credentials are read in exactly one place in this
repository — a concrete adapter's `from_environment()` — and this module does
not become a second.

---

## What this module stores, and why it is instances

`register()` takes an **already-constructed** `ProviderInterface`. It does not
take a class, a factory or a descriptor.

That follows from §9.10: every adapter "must pass a shared conformance test
suite before registration", and `runtime.provider.conformance` runs against a
*live object* — it calls `get_capabilities()`, calls `generate()`, and requires
`model_binding()`. An instance therefore already exists at the moment
registration is legal. Storing a factory instead would mean constructing one
adapter to prove conformance, discarding it, and constructing another later.

It also keeps `get_provider()` **total and offline**. Adapter construction is
not cheap or safe: the one concrete adapter in this repository fetches model
metadata over the network in its constructor, and raises if the provider will
not answer. Behind a factory that cost would land
inside a lookup — a Runtime Engine stage that §14.2 orders *before* the provider
call, which would then have a network failure mode nothing expects there.

## Registration semantics, and where they come from

§10 specifies **none** of them: it has no clause on duplicates, mutability,
scope, unregistration, timing or atomicity. All of the following are ruled
decisions recorded here so nothing reads as discovered:

* **Per-instance.** A registry is constructed and passed, the way the Validation
  Layer already receives one (`Validator(provider_registry=...)`). No global.
* **Explicit registration only, never auto-discovery.** The one existing
  registry in this repository states the reason directly: registration is
  explicit "rather than auto-discovered by import side effects: a rule that
  silently stops running because a module was not imported is exactly the kind
  of failure a fail-closed validator must not have." Here the same import side
  effect would additionally pull in a vendor SDK.
* **Add-only, and duplicates are rejected**, never overwritten. There is no
  `unregister`: §10 asks for none, and an absent method can be added later
  without breaking anyone, while a removed one cannot.
* **Not thread-safe, and no atomicity is claimed.** §10 contains nothing like
  §7.10's explicit atomicity requirement, which is the clause the Workflow State
  Manager's locks were built to satisfy. Adding locks here would manufacture a
  guarantee no specification made and that a later module might rely on.
  Registration is expected to complete during process assembly, before requests
  are served — which is also what §9.10 and §10.10 already imply by ordering
  registration ahead of validation, and validation ahead of activation (§14.10).

**§9.10 conformance is a registration requirement this module documents but does
not execute.** Running `run_conformance()` inside `register()` would call
`generate()` — a live provider call — as a side effect of wiring a process
together. The requirement is stated here and in `register()`'s docstring; proving
it is the adapter author's obligation, as it has been since the suite was built.
"""

from __future__ import annotations

from runtime.models.conversation import Turn
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import ProviderErrorType, ProviderResponse
from runtime.models.resolved_context import ResolvedContext
from runtime.provider.binding import ModelBoundProvider
from runtime.provider.errors import ProviderError
from runtime.provider.ports import ProviderInterface
from runtime.provider_registry.errors import (
    AllProvidersFailedError,
    DuplicateProviderError,
    ProviderModelMismatchError,
    ProviderNotRegisteredError,
    UnidentifiableProviderError,
)

#: The normalised failure classes that make the registry try the configured
#: secondary. §10.9 says only "Primary fails" and never says which failures
#: count, so this set is a ruled decision, not a reading of the clause.
#:
#: These three are the transient classes — the provider was reachable and
#: refused *this attempt*. Everything outside the set propagates untouched, and
#: that is the point of naming a subset at all: an `AUTHENTICATION` failure on a
#: rotated primary credential must reach an operator, not be absorbed by a
#: working secondary that makes the misconfiguration invisible indefinitely.
#: `CONTEXT_WINDOW_EXCEEDED`, `INVALID_REQUEST`, `UNKNOWN` and the
#: binding/capability failures are all either the caller's to fix or
#: unclassifiable, and none is improved by asking a second provider.
FAILOVER_ERROR_TYPES: frozenset[ProviderErrorType] = frozenset(
    {
        ProviderErrorType.RATE_LIMIT,
        ProviderErrorType.TIMEOUT,
        ProviderErrorType.SERVICE_UNAVAILABLE,
    }
)


class ProviderRegistry:
    """§10.6's two members, plus the two the Validation Layer requires.

    `is_registered` and `registered_providers` are not decoration: they are the
    complete `ProviderRegistryPort` the Validation Layer already declares and a
    committed rule already consults. That Protocol is satisfied **structurally**
    — this module does not import `runtime.validation`, which would invert the
    dependency direction §10.7 sets out.
    """

    __slots__ = ("_providers",)

    def __init__(self) -> None:
        self._providers: dict[str, ProviderInterface] = {}

    # -- registration ---------------------------------------------------------
    def register(self, provider: ProviderInterface) -> ProviderRegistry:
        """Add one already-constructed adapter, keyed by its own identity.

        **The caller is required to have run `runtime.provider.conformance`
        against this adapter first** (§9.10: the shared suite must pass "before
        registration"). This method does not run it — see the module docstring
        for why a live `generate()` call has no business happening during
        process assembly.

        The key is taken from the adapter's `model_binding().identity`, never
        from an argument. A caller-supplied name could disagree with the adapter
        it names, and the disagreement would be undetectable: the registry would
        answer `is_registered` truthfully about a string while holding something
        else behind it.

        Returns `self`, so a caller can chain registrations. Rejects a duplicate
        `provider_id` rather than replacing it.
        """
        if not isinstance(provider, ModelBoundProvider):
            raise UnidentifiableProviderError(
                f"{type(provider).__name__} does not expose model_binding(), so "
                "the registry cannot derive which provider and model it is. An "
                "adapter that passes the conformance suite exposes it (CS-3); "
                "see runtime.provider.binding.ModelBoundProvider."
            )
        identity = provider.model_binding().identity
        existing = self._providers.get(identity.provider_id)
        if existing is not None:
            raise DuplicateProviderError(
                f"provider id {identity.provider_id!r} is already registered "
                f"({type(existing).__name__}); registration rejects rather than "
                "overwrites, so an id the Validation Layer has already approved "
                "cannot change what it resolves to."
            )
        self._providers[identity.provider_id] = provider
        return self

    # -- the Validation Layer's port (satisfied structurally) -----------------
    def is_registered(self, provider_id: str) -> bool:
        """True when `provider_id` maps to a registered adapter.

        Exact, case-sensitive membership, matching `ModelIdentity`'s stated
        equality: "Equality is exact and case-sensitive." No normalisation is
        applied, because a rule for normalising a provider name is one the
        framework has not defined, and inventing one here would make two
        spellings of a name silently equivalent in routing but not in identity.
        """
        return provider_id in self._providers

    def registered_providers(self) -> frozenset[str]:
        """Every known provider id, for building an actionable error message."""
        return frozenset(self._providers)

    # -- §10.6 ---------------------------------------------------------------
    def get_provider(self, resolved_context: ResolvedContext) -> ProviderInterface:
        """The adapter this project is configured for (§10.6).

        Two checks, in order: the declared **Primary** must be registered, and
        the registered adapter's bound model must be the declared **Model**.

        Performs no network access, reads no credential and no environment
        variable — it is a lookup over what was registered.

        An absent or placeholder Primary is treated exactly like any other
        unregistered name: it is looked up, it is not found, and it raises
        `ProviderNotRegisteredError`. There is deliberately no placeholder
        detection here. `_is_placeholder` and `PLACEHOLDER_MARKERS` belong to the
        Validation Layer, and a second copy of that vocabulary in a second module
        is the drift class ADR 0002 exists to warn about. The outcome is the same
        either way: a project whose provider is a placeholder fails
        `config.llm_provider_declared` and, by §14.10, never reaches here.
        """
        selection = resolved_context.config.llm_provider
        provider = self._providers.get(selection.primary or "")
        if provider is None:
            known = ", ".join(sorted(self._providers)) or "none"
            raise ProviderNotRegisteredError(
                f"Project {resolved_context.project_id!r} declares primary LLM "
                f"provider {selection.primary!r}, which is not registered. "
                f"Registered providers: {known}. Specification 10.10 requires "
                "this to be caught at Validation Layer time, not "
                "mid-conversation, so reaching this point means an activation "
                "gate was bypassed."
            )
        self._assert_declared_model(provider, selection.primary, resolved_context)
        return provider

    def generate_with_fallback(
        self,
        resolved_context: ResolvedContext,
        prompt_bundle: PromptBundle,
        history: tuple[Turn, ...],
    ) -> ProviderResponse:
        """Call the primary; on a transient failure, call the secondary (§10.9).

        The bundle and history are passed through **exactly as received**. This
        module does not read them, reorder them, re-budget them or substitute
        one for the other — §10.3 forbids it from deciding prompt content, and
        P-1 makes which history reaches the payload the adapter's contract, not
        a decision available here.

        **Nothing re-checks capacity for the secondary, and nothing needs to.**
        Each adapter performs C-1a's own final assertion against *its own*
        window with *its own* tokenizer before calling out, and the shared
        conformance suite requires every adapter to fail closed on an oversized
        payload rather than truncate. A secondary that cannot fit this bundle
        therefore says so itself. Inventing a cross-provider compatibility
        comparison here would add a second, weaker copy of a check the adapter
        contract already guarantees.
        """
        selection = resolved_context.config.llm_provider
        primary = self.get_provider(resolved_context)
        primary_id = selection.primary or ""

        try:
            return primary.generate(prompt_bundle, history)
        except ProviderError as exc:
            if exc.error_type not in FAILOVER_ERROR_TYPES:
                # Outside the failover set: propagate untouched, so the exact
                # normalised failure stays visible instead of being masked by a
                # secondary that happens to work.
                raise
            primary_failure = exc

        attempts: tuple[tuple[str, str], ...] = (
            (primary_id, primary_failure.error_type.value),
        )

        secondary = self._providers.get(selection.secondary or "")
        if secondary is None:
            raise AllProvidersFailedError(
                self._exhausted_message(
                    resolved_context,
                    attempts,
                    trailing=(
                        "No usable secondary is configured "
                        f"(declared: {selection.secondary!r})."
                    ),
                ),
                attempts,
            ) from primary_failure

        try:
            return secondary.generate(prompt_bundle, history)
        except ProviderError as exc:
            # The secondary is the last hop, so any failure of it is exhaustion
            # (§10.9: "if none configured or it also fails"). Its class is
            # recorded rather than used to decide anything further.
            attempts += ((selection.secondary or "", exc.error_type.value),)
            raise AllProvidersFailedError(
                self._exhausted_message(resolved_context, attempts),
                attempts,
            ) from exc

    # -- internals ------------------------------------------------------------
    def _assert_declared_model(
        self,
        provider: ProviderInterface,
        provider_id: str | None,
        resolved_context: ResolvedContext,
    ) -> None:
        """The registered adapter must be bound to the model config declares.

        Routing is keyed on `provider_id`, which is coarser than identity:
        `ModelIdentity` is a pair, and its own note is that "tokenizers and
        context windows vary across a vendor's own model families". This is the
        check that keeps the coarse key honest.

        A missing or placeholder declared model fails here as well. That is the
        same comparison rather than a special case — an unstated model does not
        equal a bound one — and it is the fail-closed direction: the alternative
        is routing a project's traffic to a model nothing confirmed it chose.
        """
        # Guaranteed by `register`, which admits nothing else; asserted rather
        # than assumed so a future registration path cannot quietly skip it.
        assert isinstance(provider, ModelBoundProvider)
        bound = provider.model_binding().identity.model_id
        declared = resolved_context.config.llm_provider.model
        if declared == bound:
            return
        raise ProviderModelMismatchError(
            f"Project {resolved_context.project_id!r} declares provider "
            f"{provider_id!r} with model {declared!r}, but the adapter "
            f"registered under {provider_id!r} is bound to {bound!r}. A model "
            "is not interchangeable within a vendor: the context window and the "
            "tokenizer vocabulary both belong to one specific model."
        )

    @staticmethod
    def _exhausted_message(
        resolved_context: ResolvedContext,
        attempts: tuple[tuple[str, str], ...],
        trailing: str = "",
    ) -> str:
        """§10.9's outcome, stated for an operator — never for a customer.

        Names the providers tried and the normalised class each returned. No
        vendor payload, no credential, no user-facing wording: composing what a
        customer reads belongs to the Runtime Engine's degraded response.
        """
        tried = "; ".join(f"{name!r} -> {failure}" for name, failure in attempts)
        message = (
            f"No configured provider produced a response for project "
            f"{resolved_context.project_id!r}. Attempted: {tried}."
        )
        return f"{message} {trailing}".strip()
