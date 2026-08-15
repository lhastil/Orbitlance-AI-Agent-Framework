"""The Provider Interface — the contract every concrete adapter implements.

Specification §9: the abstract contract for an LLM provider adapter. This module
is provider-neutral by construction — it names no vendor, imports no SDK, and
exposes no provider-specific message class, configuration object or type. Those
belong exclusively inside a concrete adapter, which is the only place a
provider SDK may ever appear.

The interface deliberately stays at §9.6's two members. An adapter needs more
internally — serialization, retries within its own limits, credential handling —
but none of that crosses this boundary, because everything above it must work
identically regardless of which adapter is installed.

**What an adapter owns beyond this signature**, per the architecture:

* serializing `PromptBundle` and history into its provider's payload format;
* the final assertion that the serialized payload fits the declared context
  window, raising `ContextWindowExceededError` rather than truncating;
* translating vendor errors into the normalised set in `errors`;
* supplying a tokenizer appropriate to the model it describes.

**What it must never do:** modify the `PromptBundle` it is given, make a second
budget decision by dropping content the Token Budget Manager selected, or return
a shortened success where it should have failed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.conversation import Turn
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import ProviderCapabilities, ProviderResponse


@runtime_checkable
class ProviderInterface(Protocol):
    """What every concrete LLM provider adapter must implement."""

    def get_capabilities(self) -> ProviderCapabilities:
        """This provider's capacity and feature support.

        Must be answerable **without a live call** (§9.2) and must report
        truthfully: §9.10 makes a provider claiming a context window that does
        not match reality a conformance failure rather than a production
        surprise. The Token Budget Manager sizes every budget from this number.

        Repeated calls must agree — the budget is decided from one call and
        verified against another.
        """
        ...

    def generate(
        self, prompt_bundle: PromptBundle, history: tuple[Turn, ...]
    ) -> ProviderResponse:
        """Send the assembled prompt and return a normalised response.

        The bundle arrives already budgeted: the Token Budget Manager has
        counted its content against `get_capabilities()`. The adapter serializes
        it, asserts the result fits, and calls the provider.

        It must not mutate `prompt_bundle`, must not drop selected content to
        make room, and must raise a normalised `ProviderError` rather than
        letting a vendor exception escape. An oversized payload is
        `ContextWindowExceededError`, never a truncated success.
        """
        ...
