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

---

## P-1 — Which history is authoritative

`generate` receives history twice, and the frozen contract requires both (§9.4
lists `PromptBundle` and conversation history; §9.6 fixes the signature). Only
one of them is the payload:

> **`prompt_bundle.conversation_history_window` is the sole authoritative
> history for provider serialization.**

That window is what the Token Budget Manager selected *and counted*. The raw
`history` argument is the unbudgeted conversation, retained for observability
and auditing — it corresponds to the frozen `ProviderRequest` data model's
`conversationHistoryWindow`, a record of the call, not a source of payload.

An adapter **must not**:

* serialize the raw `history` argument;
* serialize history from both sources;
* reconstruct, expand or re-derive history from the raw argument;
* add any turn the Token Budget Manager excluded;
* substitute `history` for `prompt_bundle.conversation_history_window`.

Why this is stated rather than left to judgement: Modules 4 and 5 were rebuilt
across three amendments so that what is counted is byte-identical to what ships.
An adapter reading the wrong argument would defeat all of it at the final hop —
sending turns nothing measured, overflowing the window while every counter above
reported success. The failure would be silent, which is what makes it worth a
rule instead of a convention.

Conformance proves this neutrally: check CS-1 supplies disjoint sentinels
through the two paths and asserts which one reached the adapter's
provider-neutral serialization report. See `runtime.provider.inspection`.

## P-2 — Model binding happens at construction

An adapter is bound to one `(provider identity, model identity)` pair when it is
constructed, not per call. Nothing supplies a model to `generate`, and nothing
should: `get_capabilities()` must be answerable without a live call (§9.2), and
a context window and a tokenizer vocabulary are both facts about one specific
model. An adapter that could be re-pointed per call could not honestly answer a
capability query at all.

`PromptBundle` therefore carries no provider or model configuration, and must
not be given any — it is the provider-agnostic assembly output, and putting a
model name in it would make every module upstream provider-aware.

See `runtime.provider.binding` for the construction contract this implies.

## C-1a — What `serialization_reserve` must cover (Phase 1)

Phase-1 policy, deliberately chosen over adding a capability field: the reserve
an adapter declares must cover **both** its serialization envelope *and* its
completion/output allocation. Providers bound input and output against the same
window; nothing in the framework reserves output space, so the adapter's single
declared scalar is where that allocation lives.

The adapter's own final assertion is therefore:

    serialized request + declared output allocation <= context_window

checked **before** the call. If it cannot be established safely, the adapter
raises `ContextWindowExceededError`. No truncation, no silent retry with less
content, no hidden budget decision — the budget was already decided upstream
against counted content.

A dedicated `max_output_tokens` capability may replace this later, but only
through a deliberate architecture change, never as a quiet refinement.
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

        **Serialize `prompt_bundle.conversation_history_window`, never the
        `history` argument** — see P-1 in this module's docstring. `history` is
        the raw, unbudgeted conversation, present for observability; the bundle's
        window is what was selected and counted, and is the only history the
        payload may contain.

        It must not mutate `prompt_bundle`, must not drop selected content to
        make room, and must raise a normalised `ProviderError` rather than
        letting a vendor exception escape. An oversized payload is
        `ContextWindowExceededError`, never a truncated success.
        """
        ...
