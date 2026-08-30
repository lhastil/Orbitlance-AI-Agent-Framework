"""The shared provider conformance suite.

Specification §9.10 requires every concrete adapter to pass a shared suite before
registration. This is that suite, written once so that each future adapter runs
the same checks rather than defining its own — an adapter that supplies its own
notion of correctness is not conforming to anything.

It is provider-neutral and needs no real provider: it runs against any object
satisfying `ProviderInterface`, including a fake. It is built **before** the
first adapter deliberately, so the first adapter is validated by a suite that
already exists rather than one written around it.

**What this suite can and cannot check.** §9.6 exposes two members, so the suite
verifies everything observable through them: capability validity, stability and
truthfulness, response normalisation, error normalisation, immutability of the
caller's bundle, and fail-closed overflow. It cannot inspect an adapter's
serialized payload, because serialization format is exactly the provider-specific
detail the interface exists to hide — so "content preservation" is checked as
*the adapter did not modify what it was given*, which is neutral and meaningful,
rather than by reaching into a payload the suite would have to understand.

Each check is independent and raises `ConformanceError` naming what went
wrong. `run_conformance` collects every failure rather than stopping at the
first, so an adapter author sees the whole picture in one run.

**CS-2 - what this offline suite deliberately does not claim.** Specification
9.10 names capability truthfulness as the headline requirement: a provider
claiming a context window that does not match reality is a conformance failure.
Proving that requires a live call, so this suite does not attempt it. What it
checks is self-consistency - capabilities are valid, stable across calls,
positive window, non-negative reserve, boolean feature flags - and it must not
be read as more than that. An offline fake cannot demonstrate a real provider's
actual context window, and pretending otherwise would turn a recorded gap into a
false assurance. A live-call conformance tier is a recorded future extension,
deliberately not built in this phase.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field

from runtime.models.conversation import Turn, TurnRole
from runtime.models.prompt_bundle import PromptBundle, PromptSection, PromptSlot
from runtime.models.provider import (
    ProviderCapabilities,
    ProviderErrorType,
    ProviderResponse,
)
from runtime.provider.binding import ModelBinding, ModelBoundProvider
from runtime.provider.errors import ContextWindowExceededError, ProviderError
from runtime.provider.inspection import PromptInspectable
from runtime.provider.ports import ProviderInterface


class ConformanceError(Exception):
    """One conformance requirement an adapter did not meet."""


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """Outcome of a conformance run."""

    checks_run: tuple[str, ...] = ()
    failures: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.failures

    def raise_if_failed(self) -> None:
        if self.failures:
            raise ConformanceError(
                f"{len(self.failures)} conformance failure(s):\n  - "
                + "\n  - ".join(self.failures)
            )


# --- fixtures the suite drives adapters with ---------------------------------
#: CS-1 probes. Disjoint by construction: neither string can appear inside the
#: other, so "which history reached the payload" has one unambiguous answer.
BUNDLE_HISTORY_SENTINEL = "ORBITLANCE-CS1-AUTHORITATIVE-WINDOW"
RAW_HISTORY_SENTINEL = "ORBITLANCE-CS1-RAW-ARGUMENT"


def sample_bundle(
    content: str = "system content", history: tuple[Turn, ...] | None = None
) -> PromptBundle:
    """A minimal, well-formed bundle. Deliberately provider-neutral."""
    return PromptBundle(
        project_id="conformance",
        conversation_id="conformance-1",
        static_sections=(
            PromptSection(
                slot=PromptSlot.CORE_PERSONALITY,
                sources=("core/prompts/01_core_personality.md",),
                content=content,
            ),
        ),
        conversation_history_window=(
            history if history is not None else (Turn(TurnRole.USER, "earlier"),)
        ),
        latest_message="hello",
    )


def history_probe_bundle() -> PromptBundle:
    """A bundle whose history window carries the authoritative sentinel."""
    return sample_bundle(history=(Turn(TurnRole.USER, BUNDLE_HISTORY_SENTINEL),))


def raw_history_probe() -> tuple[Turn, ...]:
    """The raw `history` argument - carries the sentinel that must NOT ship."""
    return (Turn(TurnRole.USER, RAW_HISTORY_SENTINEL),)


def sample_history() -> tuple[Turn, ...]:
    return (Turn(TurnRole.USER, "earlier"), Turn(TurnRole.AGENT, "reply"))


def oversized_bundle(capabilities: ProviderCapabilities) -> PromptBundle:
    """A bundle that cannot fit, whatever the adapter's serialization costs.

    Sized from the declared window rather than a fixed constant, so the check
    holds for a small model and a large one alike.
    """
    filler = "token " * (capabilities.context_window + 1_000)
    return sample_bundle(filler)


# --- individual checks --------------------------------------------------------
def check_implements_interface(provider: ProviderInterface) -> None:
    if not isinstance(provider, ProviderInterface):
        raise ConformanceError(
            "does not satisfy ProviderInterface (needs get_capabilities and generate)"
        )


def check_capabilities_are_valid(provider: ProviderInterface) -> None:
    caps = provider.get_capabilities()
    if not isinstance(caps, ProviderCapabilities):
        raise ConformanceError("get_capabilities did not return ProviderCapabilities")
    if caps.context_window <= 0:
        raise ConformanceError(f"context_window is {caps.context_window}")
    if caps.serialization_reserve < 0:
        raise ConformanceError(
            f"serialization_reserve is {caps.serialization_reserve}"
        )
    if caps.serialization_reserve >= caps.context_window:
        raise ConformanceError("serialization_reserve leaves no room for content")


def check_capabilities_are_stable(provider: ProviderInterface) -> None:
    """The budget is decided from one query and verified against another."""
    if provider.get_capabilities() != provider.get_capabilities():
        raise ConformanceError("get_capabilities is not stable across calls")


def check_capability_flags_are_boolean(provider: ProviderInterface) -> None:
    caps = provider.get_capabilities()
    if not isinstance(caps.streaming_support, bool):
        raise ConformanceError("streaming_support is not a bool")
    if not isinstance(caps.tool_calling_support, bool):
        raise ConformanceError("tool_calling_support is not a bool")


def check_generate_returns_normalised_response(provider: ProviderInterface) -> None:
    """A well-formed bundle yields a normalised response, or a normalised error.

    Declining is legitimate — an adapter may reject for reasons the suite cannot
    arrange. What is not legitimate is returning something that is not a
    `ProviderResponse`, or an `error_type` outside the normalised set.
    """
    try:
        response = provider.generate(sample_bundle(), sample_history())
    except ProviderError:
        return
    if not isinstance(response, ProviderResponse):
        raise ConformanceError("generate did not return ProviderResponse")
    if response.error_type is not None and not isinstance(
        response.error_type, ProviderErrorType
    ):
        raise ConformanceError("error_type is not a normalised ProviderErrorType")


def check_bundle_is_not_mutated(provider: ProviderInterface) -> None:
    """Content preservation, as far as this boundary can observe it.

    The adapter serializes; the suite cannot read that payload without knowing
    the provider's format. What it can require is that the caller's bundle comes
    back unchanged — an adapter that edits content before sending has already
    broken the counted-content guarantee.
    """
    bundle = sample_bundle()
    before = (
        bundle.static_sections,
        bundle.conversation_history_window,
        bundle.latest_message,
    )
    with contextlib.suppress(ProviderError):
        provider.generate(bundle, sample_history())  # a failure is fine; mutation is not
    after = (
        bundle.static_sections,
        bundle.conversation_history_window,
        bundle.latest_message,
    )
    if before != after:
        raise ConformanceError("generate mutated the PromptBundle it was given")


def check_oversized_payload_fails_closed(provider: ProviderInterface) -> None:
    """Overflow must raise, never truncate and never quietly succeed."""
    caps = provider.get_capabilities()
    bundle = oversized_bundle(caps)
    try:
        response = provider.generate(bundle, sample_history())
    except ContextWindowExceededError:
        return
    except ProviderError as exc:
        raise ConformanceError(
            "an oversized payload raised "
            f"{type(exc).__name__} rather than ContextWindowExceededError"
        ) from exc
    raise ConformanceError(
        "an oversized payload returned a response instead of failing closed "
        f"(error_type={response.error_type}) — truncation and silent fallback "
        "are both forbidden"
    )


def check_errors_are_normalised(provider: ProviderInterface) -> None:
    """Whatever escapes `generate` must be a normalised ProviderError.

    Adapters that cannot be driven into a failure by the suite pass trivially;
    the check exists to catch a raw SDK exception escaping (§9.9).
    """
    try:
        provider.generate(oversized_bundle(provider.get_capabilities()), ())
    except ProviderError:
        return
    except Exception as exc:  # noqa: BLE001 - that is precisely what is checked
        raise ConformanceError(
            f"a non-normalised {type(exc).__name__} escaped generate"
        ) from exc


def check_authoritative_history_is_serialized(provider: ProviderInterface) -> None:
    """CS-1: the bundle's window ships; the raw `history` argument does not.

    Proven neutrally. Two disjoint sentinels go in by the two paths, and the
    adapter reports - in framework terms, never in its payload format - which
    strings it serialized. No vendor structure is inspected.

    An adapter that does not expose `PromptInspectable` fails here rather than
    passing quietly: the rule cannot be proven against it, and "could not be
    checked" has never counted as "passed" in this framework.
    """
    if not isinstance(provider, PromptInspectable):
        raise ConformanceError(
            "does not expose the provider-neutral inspection contract "
            "(last_serialized_prompt), so P-1 authoritative-history use cannot "
            "be proven; see runtime.provider.inspection"
        )
    try:
        provider.generate(history_probe_bundle(), raw_history_probe())
    except ProviderError as exc:
        raise ConformanceError(
            f"declined the well-formed CS-1 probe with {type(exc).__name__}, "
            "leaving authoritative-history use unproven"
        ) from exc
    snapshot = provider.last_serialized_prompt()
    if snapshot is None:
        raise ConformanceError(
            "reported no serialization after a successful generate, leaving "
            "authoritative-history use unproven"
        )
    if snapshot.contains(RAW_HISTORY_SENTINEL):
        raise ConformanceError(
            "serialized the raw `history` argument, which the Token Budget "
            "Manager never counted (P-1: only "
            "prompt_bundle.conversation_history_window may reach the payload)"
        )
    if not snapshot.contains(BUNDLE_HISTORY_SENTINEL):
        raise ConformanceError(
            "did not serialize prompt_bundle.conversation_history_window, the "
            "only authoritative history (P-1)"
        )


def check_tokenizer_and_capabilities_agree(provider: ProviderInterface) -> None:
    """CS-3: capabilities and tokenizer describe the same model (T-1).

    A tokenizer for one model paired with a window for another makes Module 5
    count precisely against the wrong vocabulary and report success. This check
    requires the adapter to expose the single binding both came from, and
    requires that binding's tokenizer to say which model it is for.
    """
    if not isinstance(provider, ModelBoundProvider):
        raise ConformanceError(
            "does not expose model_binding(), so the tokenizer and capabilities "
            "cannot be shown to describe the same model (T-1); see "
            "runtime.provider.binding"
        )
    binding = provider.model_binding()
    if not isinstance(binding, ModelBinding):
        raise ConformanceError("model_binding did not return a ModelBinding")
    if binding.capabilities != provider.get_capabilities():
        raise ConformanceError(
            "get_capabilities does not return the binding's capabilities, so "
            "the binding is not the single origin it claims to be"
        )
    declared = binding.tokenizer_identity
    if declared is None:
        raise ConformanceError(
            "the bound tokenizer declares no model identity, so its vocabulary "
            "cannot be shown to match the declared context window (T-1)"
        )
    if declared != binding.identity:
        raise ConformanceError(
            f"tokenizer describes {declared} but the adapter is bound to "
            f"{binding.identity}"
        )


#: Order matters only for cost and blast radius, never for meaning - each check
#: is independent, as this module's docstring states. The two oversized-payload
#: checks run LAST because they are the expensive ones: `oversized_bundle` scales
#: with the declared window, so against a million-token model each sends several
#: megabytes. Running the small structural probes first means a transient fault
#: provoked by that traffic cannot be misreported as a contract violation, which
#: is exactly what happened to CS-1 on the first live run.
#:
#: The oversized checks themselves are unchanged: same probes, same assertions,
#: same fail-closed requirement. Only their position moved.
CHECKS: tuple[Callable[[ProviderInterface], None], ...] = (
    # -- cheap and structural: no payload larger than a few hundred bytes
    check_implements_interface,
    check_capabilities_are_valid,
    check_capabilities_are_stable,
    check_capability_flags_are_boolean,
    check_tokenizer_and_capabilities_agree,
    check_generate_returns_normalised_response,
    check_bundle_is_not_mutated,
    check_authoritative_history_is_serialized,
    # -- expensive: payload sized from the provider's own context window
    check_oversized_payload_fails_closed,
    check_errors_are_normalised,
)


def _with_cause(exc: BaseException) -> str:
    """The failure text, plus whatever underlying error produced it.

    A check that reports only its own sentence discards the diagnostic it was
    handed. When a provider declines a probe, "declined with
    ProviderUnavailableError" does not say whether the backend returned 503, 500
    or the connection never opened - and those need different responses. The
    cause is already chained; this simply stops it being thrown away.

    Walks the whole chain, because an adapter may wrap a vendor error which
    itself wraps a transport error, and the innermost link is usually the
    informative one.
    """
    parts: list[str] = [str(exc)]
    seen: set[int] = {id(exc)}
    cause = exc.__cause__
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        parts.append(f"caused by {type(cause).__name__}: {cause}")
        cause = cause.__cause__
    return " | ".join(parts)


def run_conformance(provider: ProviderInterface) -> ConformanceReport:
    """Run every check, collecting failures rather than stopping at the first."""
    names: list[str] = []
    failures: list[str] = []
    for check in CHECKS:
        names.append(check.__name__)
        try:
            check(provider)
        except ConformanceError as exc:
            failures.append(f"{check.__name__}: {_with_cause(exc)}")
        except Exception as exc:  # noqa: BLE001 - a harness must always report
            # An adapter raising something unexpected is itself a conformance
            # failure, and reporting it beats crashing the run: an author needs
            # the whole picture, not the first thing that went wrong.
            failures.append(
                f"{check.__name__}: raised {type(exc).__name__}: {_with_cause(exc)}"
            )
    return ConformanceReport(checks_run=tuple(names), failures=tuple(failures))


def assert_conforms(provider: ProviderInterface) -> None:
    """Convenience for an adapter's own test module: run, then raise on failure."""
    run_conformance(provider).raise_if_failed()
