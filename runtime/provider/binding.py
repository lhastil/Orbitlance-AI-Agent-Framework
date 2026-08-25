"""Model binding — one origin for capabilities, tokenizer and identity (T-1).

An adapter is bound at **construction** to exactly one `(provider, model)` pair
(P-2). Everything that depends on that pair — the context window, the
serialization reserve, the tokenizer's vocabulary — must come from the same
binding, because a mismatch between them is not a visible error. It is a wrong
answer that looks exact.

Concretely, the invalid state this module exists to prevent:

    TokenBudgetManager(tokenizer=tokenizer_for_model_X,
                       capabilities=capabilities_of_model_Y)

Module 5 would count every string precisely, against the wrong vocabulary, and
report success. That is the fail-open class this framework has removed four
times already (a null registry that answered False, a decomposition that
dropped duplicates, a seam that under-counted, a sum that omitted joins). It is
removed here the same way: by making the invalid state unconstructible rather
than by detecting it afterwards.

`ModelBinding` is that construction. It validates identity agreement once, at
construction, and thereafter *is* the single origin an adapter exposes. An
adapter that builds one cannot hand Module 5 a mismatched pair without
explicitly bypassing its own binding.

**Nothing here names a provider or a model.** `ModelIdentity` carries opaque
strings supplied by whichever adapter is installed; this module never compares
them to a list of known vendors, because no such list exists or should.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from runtime.models.provider import ProviderCapabilities
from runtime.provider.errors import ProviderBindingError


@runtime_checkable
class TokenCounter(Protocol):
    """Counts tokens. Structurally identical to Module 5's `TokenizerPort`.

    Declared here rather than imported from Module 5's ports module on purpose:
    the provider layer depends only on `runtime/models/`, never on a module.
    Importing Module 5's port would create a provider-to-budget edge and invert
    the direction the whole architecture rests on — Module 5 must be able to
    consume an adapter's tokenizer without the provider layer knowing Module 5
    exists. (The independence tests scan this package for that import path as a
    plain substring, so it is deliberately not written out here.)

    Because both are structural protocols requiring the same single method, an
    adapter's tokenizer satisfies both at once. No adaptation is needed.
    """

    def count_tokens(self, text: str) -> int:
        ...


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Which provider and model a binding describes.

    Both fields are opaque to the framework. `provider_id` is the name a
    project's config declares and a future Provider Registry resolves;
    `model_id` is whatever that provider calls the model. Neither is validated
    against a vendor list — the framework has no such list, and adding one would
    make it provider-aware.

    Equality is exact and case-sensitive. Two adapters for the same vendor at
    different models are different identities, which is the point: tokenizers
    and context windows vary across a vendor's own model families.
    """

    provider_id: str
    model_id: str

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")

    def __str__(self) -> str:
        return f"{self.provider_id}/{self.model_id}"


@runtime_checkable
class IdentifiedTokenizer(Protocol):
    """A token counter that also states which model it tokenizes for.

    Declared here, in the provider layer, rather than by extending
    `TokenizerPort` — Module 5 must not become provider-aware, and it does not
    need this: it needs a count, and its port says exactly that and nothing
    more. Identity matters only where the pairing is *made*, which is here.

    Structural, so an adapter's tokenizer satisfies it by having the methods.
    """

    def count_tokens(self, text: str) -> int:
        ...

    def model_identity(self) -> ModelIdentity:
        ...


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """The single origin of one adapter's identity, capabilities and tokenizer.

    Construction fails if the tokenizer declares a different identity than the
    binding. That check is the whole value of the type: after it passes, the
    capabilities and the tokenizer provably describe the same model, and an
    adapter can hand both to the runtime without the caller having to verify the
    pairing themselves.

    A tokenizer that does *not* declare an identity is accepted and recorded as
    unverified rather than assumed to match. Refusing it outright would force
    every adapter's tokenizer to implement a method the frozen `TokenizerPort`
    does not require; assuming it matches would be the fail-open answer. The
    conformance suite reports the unverified case as a failure, which is where
    an adapter-quality judgement belongs — see CS-3 in `conformance`.
    """

    identity: ModelIdentity
    capabilities: ProviderCapabilities
    tokenizer: TokenCounter

    def __post_init__(self) -> None:
        declared = self.tokenizer_identity
        if declared is not None and declared != self.identity:
            raise ProviderBindingError(
                f"tokenizer describes {declared} but the binding is for "
                f"{self.identity}; a tokenizer for a different model would "
                "count every string precisely against the wrong vocabulary"
            )

    @property
    def tokenizer_identity(self) -> ModelIdentity | None:
        """The tokenizer's declared identity, or None if it declares none."""
        if isinstance(self.tokenizer, IdentifiedTokenizer):
            return self.tokenizer.model_identity()
        return None

    @property
    def identity_is_verified(self) -> bool:
        """True when the tokenizer declared an identity and it matched."""
        return self.tokenizer_identity is not None


@runtime_checkable
class ModelBoundProvider(Protocol):
    """A `ProviderInterface` that exposes the binding it was constructed with.

    Deliberately **not** part of `ProviderInterface`: frozen §9.6 declares two
    members and this phase does not change that signature. This is a separate
    structural protocol an adapter also satisfies, which keeps the frozen
    contract intact while letting the conformance suite verify T-1 and P-2.

    An adapter satisfying this is stating: my capabilities, my tokenizer and my
    model identity all came from one construction, and here it is.
    """

    def get_capabilities(self) -> ProviderCapabilities:
        ...

    def model_binding(self) -> ModelBinding:
        ...
