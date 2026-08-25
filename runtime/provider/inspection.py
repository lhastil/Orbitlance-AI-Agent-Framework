"""The provider-neutral inspection contract used by conformance (CS-1).

The conformance suite must prove that an adapter serialized the *authoritative*
history — `PromptBundle.conversation_history_window` — and not the raw `history`
argument. It cannot do that by reading the adapter's payload: that payload's
shape is exactly the provider-specific detail `ProviderInterface` exists to hide,
and a suite that understood it would need a branch per vendor.

So the adapter reports what it used, in framework terms, through this contract.
`SerializedPrompt` carries **only strings the adapter took from the bundle** —
no SDK objects, no vendor message classes, no request options, no role names. An
adapter can satisfy this without its SDK types ever crossing the boundary,
which is the whole design constraint.

This is a **testing contract**, not part of `ProviderInterface`. Frozen §9.6
declares two members and this phase does not change that signature; an adapter
satisfies this protocol *in addition*, structurally. What it is not is optional
in effect: an adapter that does not expose it cannot be proven to obey the
authoritative-history rule, and the suite reports that as a failure rather than
passing it on the assumption that it behaves. That is the same shape as the
Validation Layer's resolution of V-1 — an absent collaborator means the check
could not run, and "could not run" never counts as "passed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SerializedPrompt:
    """What an adapter actually put into its provider request, in framework terms.

    Each field holds the framework content the adapter serialized, in the order
    it serialized it. The adapter reports its *own* view of what it sent; the
    suite compares that against what it supplied. A dishonest adapter can defeat
    this, exactly as a dishonest `get_capabilities()` can defeat the capability
    checks — §9.10 makes misreporting a conformance failure, and no offline
    suite can do better than that (see CS-2).

    Provider framing is deliberately absent. Role markers, JSON envelopes,
    system-prompt placement and request options are all the adapter's business,
    and reporting them here would make this type provider-shaped.
    """

    static_texts: tuple[str, ...] = ()
    history_texts: tuple[str, ...] = ()
    latest_message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "static_texts", tuple(self.static_texts))
        object.__setattr__(self, "history_texts", tuple(self.history_texts))

    @property
    def all_texts(self) -> tuple[str, ...]:
        """Every framework string that reached the payload.

        CS-1 searches all of these, not just `history_texts`: an adapter that
        folded the raw history into its system content would otherwise pass a
        check that only looked where the history was supposed to be.
        """
        return (*self.static_texts, *self.history_texts, self.latest_message)

    def contains(self, needle: str) -> bool:
        return any(needle in text for text in self.all_texts)


@runtime_checkable
class PromptInspectable(Protocol):
    """An adapter that can report, neutrally, what its last call serialized."""

    def last_serialized_prompt(self) -> SerializedPrompt | None:
        """The most recent serialization, or None if nothing was serialized yet.

        Returning None after a successful `generate` is itself a conformance
        failure: it leaves the authoritative-history rule unproven.
        """
        ...


@dataclass(frozen=True, slots=True)
class RecordingSerializer:
    """Helper an adapter may use to build a `SerializedPrompt` from a bundle.

    Provided so that the *correct* behaviour is the path of least resistance:
    it reads history from `bundle.conversation_history_window` and has no way to
    read the raw `history` argument, because it is never given it.

    Purely optional. An adapter may build `SerializedPrompt` however it likes —
    what conformance checks is the result, never the route taken to it.
    """

    #: Kept for symmetry with future options; no behaviour depends on it yet.
    include_latest_message: bool = field(default=True)

    def record(self, prompt_bundle: object) -> SerializedPrompt:
        """Snapshot the authoritative content of `prompt_bundle`.

        Typed loosely to keep this module free of any import that would make the
        provider layer depend on more than it needs; the attributes read are
        `PromptBundle`'s frozen public surface.
        """
        sections = getattr(prompt_bundle, "static_sections", ())
        window = getattr(prompt_bundle, "conversation_history_window", ())
        latest = getattr(prompt_bundle, "latest_message", "")
        return SerializedPrompt(
            static_texts=tuple(section.content for section in sections),
            history_texts=tuple(turn.content for turn in window),
            latest_message=latest if self.include_latest_message else "",
        )
