"""Guardrail Engine — specification §8.

Enforces the universal Core guardrails bundle and the project's additive
Operating Constraints at two checkpoints: pre-flight, before any provider call,
and post-response, before a generated answer reaches the user.

Pure and deterministic. It never mutates the message, the response, the
`CoreBundle` or the `ResolvedContext`; it never persists anything; it never
calls a provider, opens a socket or touches the filesystem. §8.8's optional LLM
"guardrail judge" is deliberately **not** implemented — the specification itself
positions it as a *"sampled/async audit pass, not a blocking check on every
turn"*, so the enforcement path stays free of provider infrastructure.

---

## What is enforced deterministically, and what is not

This is the honest centre of this module, and it must not be skimmed.

`core/guardrails/*` and a project's Operating Constraints are **prose written in
the second person to the agent** — *"The AI must never: Invent facts or business
information"*, *"Escalate immediately when: … Security concerns are detected"*,
*"Never diagnose a condition."* They already reach the model as prompt content
through the Prompt Assembler's Guardrails slot. What this Engine adds is a
second, independent layer that does not depend on the model obeying them.

A second layer is only worth anything if it is real. So this module implements
exactly the checks that can be justified from an authoritative source, and
refuses to approximate the rest:

**Implemented (deterministic):**

* **`core.escalation.human_representative_request`** and
  **`core.escalation.manager_request`** — a pre-flight message asking for a
  person escalates. **The vocabulary is not defined here.** It is read from
  `escalation.md`'s *"Escalation Trigger Phrases"* section, which states that it
  is the authoritative source; this module looks it up and matches, and would
  enforce a different vocabulary tomorrow without being edited. That is the
  whole point: safety semantics stay in `core/`, where the framework's other
  safety content lives, and Python never becomes the authority for them.
  These two escalate and **never block** — a customer asking for a human is
  requesting a handoff, not a refusal of service (GE-1's ruling, 2026-09-05).
* **`core.safety.unsupported_price`** — a price appearing in a response but
  absent from the project's resolved Knowledge is blocked. §8.2 names this
  example verbatim (*"a price not present in Knowledge"*) and §8.12(b) tests it.
  The guardrail it enforces is `safety.md`'s *"Invent facts or business
  information"*. See `PRICE_PATTERN` for where the lexical definition comes from.
* **`engine.guardrails_unavailable`** — if the Core guardrails bundle is not
  intact, the Engine cannot enforce anything and blocks. §8.7 loads the bundle
  atomically; §8.9 requires an Engine that cannot do its job to fail closed
  rather than pass.
* **Internal failure at either checkpoint** — any unexpected exception becomes a
  blocked, escalating result (§8.9), never a pass and never a traceback.

**Not implemented, and deliberately not approximated:**

* **Eight of `escalation.md`'s ten Automatic Escalation Conditions.** Every one
  of the eight is semantic — *"The AI cannot confidently answer after
  clarification"*, *"Security concerns are detected"*, *"Legal or contractual
  discussions begin"*. Detecting them needs intent classification, and Core
  publishes no vocabulary for them. A keyword list invented here would become
  this framework's safety semantics on no authority, and would fail in both
  directions: missing real escalations while blocking innocent messages. Two of
  the eight are not pre-flight questions at all — *"cannot confidently answer
  after clarification"* needs conversation history this checkpoint is not given
  (§8.4), and *"Technical issues exceed the AI's capabilities"* is observable
  only after a failure (**AUDIT-6**, which stays open).
* **Every project Operating Constraint.** `sunrise_dental_clinic` carries five,
  and all five are semantic — including *"Never quote a price for treatment
  requiring an in-person exam"*, which needs to know which treatments require
  one. §8.11 records structured, machine-checkable constraints as the intended
  remedy; that mechanism does not exist yet and is future work.

**The consequence, stated plainly: `check_pre_flight` evaluates exactly two
conditions and no others.** It verifies the bundle, matches Core's published
escalation vocabulary, and fails closed on internal error. What it does not
check remains named here, exposed through `UNENFORCED_CORE_CONDITIONS`, and
asserted by tests, instead of being hidden behind an interface that looks
complete.
"""

from __future__ import annotations

import re

from runtime.models.core_bundle import CoreBundle
from runtime.models.guardrail import Checkpoint, GuardrailResult
from runtime.models.provider import ProviderResponse
from runtime.models.resolved_context import ResolvedContext

#: The guardrails bundle, atomic (§8.7, and known-issues.md #2's resolution:
#: Safety + Escalation + Compliance always together).
#:
#: Declared here rather than imported from `runtime.assembler.core_slots`: §8.7
#: allows Core Loader and Resolver, so importing Module 4 would be an edge the
#: architecture does not grant. Same transcription-with-citation pattern the
#: Core Loader's manifest already uses.
GUARDRAIL_FILES: tuple[str, ...] = ("safety.md", "escalation.md", "compliance.md")

#: What counts as a price. **Not invented here.**
#:
#: Transcribed from `runtime/validation/framework_spec.py`'s
#: `CLIENT_SPECIFIC_PATTERNS`, whose entry is labelled *"hardcoded price"* and is
#: already used by the Validation Layer to find prices in Core files. Reusing the
#: framework's own committed definition means "price" means one thing across the
#: runtime; declaring it locally rather than importing keeps Module 8 off Module
#: 13, which §8.7 does not permit it to depend on.
#:
#: Deliberately narrow: a currency sigil followed by digits. It will not find
#: "one hundred and twenty dollars", and it is not extended to try — a broader
#: pattern would be a guess about language, and §8.11 records structured
#: expression as the route to richer checking.
PRICE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![A-Za-z0-9])\$\s?\d[\d,]*(\.\d{2})?"
)

#: Characters the price pattern can capture at the end of a token that are
#: sentence punctuation rather than part of the number. Stripped before
#: comparison — see `_unsupported_prices` for why this delimits the token rather
#: than normalising its value.
#:
#: Named "punctuation" rather than "separator" deliberately: the Prompt
#: Assembler reserves that word for the Knowledge-composition constant only it
#: may know, and a test in Module 4 fails if any other module names it.
TRAILING_PUNCTUATION: str = ",."

#: Where Core publishes the deterministic escalation vocabulary (GE-1, ruled
#: 2026-09-05). **Addresses into a Core document, not the policy itself**: the
#: phrases live in `escalation.md` and are read from it per call, so this module
#: enforces whatever Core currently says and never becomes the authority for it.
#: Each heading is worded identically to the condition it serves, which is what
#: makes `core.*` attribution structural rather than hand-maintained.
#:
#: **Private.** §8.6 declares two members, and this is an implementation detail
#: of how they find their policy — not a published declaration of coverage.
#: `UNENFORCED_CORE_CONDITIONS` is that declaration, and is public for it.
_ESCALATION_VOCABULARY_SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "The customer explicitly requests a human representative",
        "core.escalation.human_representative_request",
    ),
    (
        "The customer requests a manager or supervisor",
        "core.escalation.manager_request",
    ),
)

#: Guardrail conditions that exist as prose and have **no** deterministic
#: evaluator. Published so a caller can see exactly what this Engine does not
#: check, rather than inferring coverage from the fact that it returned a result.
#: Source: `core/guardrails/escalation.md`, "Automatic Escalation Conditions".
#:
#: The first two conditions are **absent** because Core now publishes a
#: vocabulary for them and this Engine enforces it — see
#: `_ESCALATION_VOCABULARY_SECTIONS`. The eight below remain unenforced.
UNENFORCED_CORE_CONDITIONS: tuple[str, ...] = (
    "The AI cannot confidently answer after clarification.",
    "A business decision requires human approval.",
    "A complaint requires manual review.",
    "Legal or contractual discussions begin.",
    "Payment disputes arise.",
    "Security concerns are detected.",
    "Sensitive account actions require authorization.",
    "Technical issues exceed the AI's capabilities.",
)

#: Project Operating Constraints have no deterministic evaluator at all (§8.11).
UNENFORCED_PROJECT_CONSTRAINTS: str = (
    "Free-text Operating Constraints are not machine-checkable. Specification "
    "8.11 records structured constraint expression as the intended mechanism; "
    "until it exists, project constraints reach the model as prompt content "
    "only and are not enforced by this Engine."
)


class GuardrailEngine:
    """Checks a turn at both checkpoints (§8.6).

    The `CoreBundle` is supplied at construction, as the Prompt Assembler takes
    it, because it is process-lifetime data rather than per-call input. The
    `ResolvedContext` arrives per call, exactly as §8.4 specifies.
    """

    __slots__ = ("_core",)

    def __init__(self, core: CoreBundle) -> None:
        self._core = core

    # -- §8.6 public interface ----------------------------------------------
    def check_pre_flight(
        self, message: str, resolved_context: ResolvedContext
    ) -> GuardrailResult:
        """Check the incoming message before any provider call (§8.2).

        Two conditions are evaluated, against vocabulary Core publishes — the
        first two named in `_ESCALATION_VOCABULARY_SECTIONS`. Both **escalate
        without blocking**: the customer is asking for a person, not being
        refused (GE-1, ruled 2026-09-05). The other eight Automatic Escalation
        Conditions have no authoritative vocabulary and are named in
        `UNENFORCED_CORE_CONDITIONS`.

        Cheap, as §8.2 requires, and provider-free: this is a substring scan
        over a list read from an already-loaded document. No network call, no
        model, nothing that could make the pre-flight checkpoint cost what it
        exists to precede.

        `resolved_context` is accepted per §8.4 and not consulted: the two
        conditions are Core-universal, and reading a project's context here
        would make a universal guardrail project-dependent.
        """
        del resolved_context  # §8.4 input; no Core-universal rule consults it
        try:
            unavailable = self._guardrails_unavailable(Checkpoint.PRE_FLIGHT)
            if unavailable is not None:
                return unavailable

            escalation = self._escalation_request(message)
            if escalation is not None:
                return escalation

            return GuardrailResult(checkpoint=Checkpoint.PRE_FLIGHT)
        except Exception as exc:  # noqa: BLE001 - §8.9: never a pass, never a raise
            return self._internal_failure(Checkpoint.PRE_FLIGHT, exc)

    def check_post_response(
        self, response: ProviderResponse, resolved_context: ResolvedContext
    ) -> GuardrailResult:
        """Check the generated response before it reaches the user (§8.2).

        Never skipped to save latency or cost (§8.3), and never rewrites the
        response — §8.3 assigns composing a safe alternative elsewhere, so this
        detects and blocks only.
        """
        try:
            unavailable = self._guardrails_unavailable(Checkpoint.POST_RESPONSE)
            if unavailable is not None:
                return unavailable

            unsupported = self._unsupported_prices(response, resolved_context)
            if unsupported:
                quoted = ", ".join(repr(price) for price in unsupported)
                return GuardrailResult(
                    checkpoint=Checkpoint.POST_RESPONSE,
                    blocked=True,
                    reason=(
                        f"The response quotes {quoted}, which does not appear in "
                        f"the project's Knowledge. Core guardrail "
                        f"'safety.md: Invent facts or business information' "
                        f"forbids stating business information the project has "
                        f"not supplied."
                    ),
                    triggered_rule="core.safety.unsupported_price",
                )

            return GuardrailResult(checkpoint=Checkpoint.POST_RESPONSE)
        except Exception as exc:  # noqa: BLE001 - §8.9: never a pass, never a raise
            return self._internal_failure(Checkpoint.POST_RESPONSE, exc)

    # -- deterministic rules -------------------------------------------------
    def _escalation_request(self, message: str) -> GuardrailResult | None:
        """The first matching escalation condition, or None (§8.2, GE-1).

        Escalates, never blocks. `blocked=False` with a reason and a rule is a
        shape `GuardrailResult` already permits, and it is the honest one here:
        the turn proceeds, and the outcome carries a handoff signal.

        Conditions are evaluated in Core's own order, and the first match wins —
        a message asking for "a manager" is escalating either way, so reporting
        the first specific reason is more useful than reporting all of them.
        """
        haystack = message.casefold()
        for heading, rule in _ESCALATION_VOCABULARY_SECTIONS:
            for phrase in self._escalation_phrases(heading):
                if phrase.casefold() in haystack:
                    return GuardrailResult(
                        checkpoint=Checkpoint.PRE_FLIGHT,
                        blocked=False,
                        escalate=True,
                        reason=(
                            f"The message contains {phrase!r}. Core guardrail "
                            f"'escalation.md: {heading}' requires escalating "
                            f"immediately. The conversation is not blocked — the "
                            f"customer is requesting a person, not being refused."
                        ),
                        triggered_rule=rule,
                    )
        return None

    def _escalation_phrases(self, heading: str) -> tuple[str, ...]:
        """Core's published phrases for one condition, read per call.

        A bullet list under a heading `escalation.md` owns. Reading it here
        rather than transcribing it is what keeps Core authoritative: edit the
        document and this Engine's behaviour changes with it, with no Python to
        keep in step. The `- ` strip is the whole of the "parsing" — §8.7 allows
        Core Loader, not Module 2, so no markdown helper is imported.

        An empty result raises rather than quietly matching nothing: a missing
        vocabulary means this Engine cannot enforce a condition it claims to,
        which §8.9 says must fail closed rather than become a silent no-op. The
        caller's guard turns it into a blocked, escalating result.
        """
        document = self._core.guardrails["escalation.md"]
        phrases = tuple(
            stripped[2:].strip()
            for line in document.section_body(heading).splitlines()
            if (stripped := line.strip()).startswith("- ") and len(stripped) > 2
        )
        if not phrases:
            raise ValueError(
                f"core/guardrails/escalation.md publishes no trigger phrases "
                f"under {heading!r}. Specification 8.2's pre-flight scan cannot "
                f"be performed without them, and 8.9 forbids passing instead."
            )
        return phrases


    def _unsupported_prices(
        self, response: ProviderResponse, resolved_context: ResolvedContext
    ) -> tuple[str, ...]:
        r"""Prices in the response that do not appear in resolved Knowledge.

        Comparison is **verbatim** apart from one correction: a trailing `,` or
        `.` is stripped from the matched token first. The borrowed pattern ends
        in ``[\d,]*``, which greedily swallows the comma in *"Cleaning is $120,
        implants are…"* and yields `"$120,"`. That trailing character is
        sentence punctuation, not part of the number, and leaving it in blocked
        a price the project genuinely publishes.

        This corrects how the token is *delimited*; it does not normalise the
        *value*. Spacing, thousands separators and decimals are all still
        compared literally, because a rule for those is one the framework has
        not defined — so `"$ 120"` against a Knowledge entry of `"$120"` still
        blocks. The failure direction is deliberate: an unnormalised near-match
        blocks rather than passes, which is the safe way for a guardrail to be
        wrong.
        """
        knowledge = "\n".join(
            document.raw_text
            for document in resolved_context.knowledge.values()
            if document.exists
        )
        seen: list[str] = []
        for match in PRICE_PATTERN.finditer(response.text or ""):
            price = match.group(0).rstrip(TRAILING_PUNCTUATION)
            if price not in knowledge and price not in seen:
                seen.append(price)
        return tuple(seen)

    def _guardrails_unavailable(self, checkpoint: Checkpoint) -> GuardrailResult | None:
        """Fail closed when the Core bundle cannot back a decision (§8.7, §8.9).

        An Engine whose guardrails are missing cannot enforce them. Passing in
        that state is the no-op §8.9 names; blocking is the honest answer.
        """
        missing = tuple(
            name
            for name in GUARDRAIL_FILES
            if name not in self._core.guardrails
            or not self._core.guardrails[name].exists
            or not self._core.guardrails[name].raw_text.strip()
        )
        if not missing:
            return None
        return GuardrailResult(
            checkpoint=checkpoint,
            blocked=True,
            escalate=True,
            reason=(
                "The Core guardrails bundle is incomplete "
                f"({', '.join(missing)} missing or empty), so no guardrail can "
                "be enforced. Specification 8.9 requires failing closed rather "
                "than becoming a silent no-op."
            ),
            triggered_rule="engine.guardrails_unavailable",
        )

    @staticmethod
    def _internal_failure(checkpoint: Checkpoint, cause: Exception) -> GuardrailResult:
        """§8.9: the Engine's own failure blocks and escalates.

        Attributed to `engine.*` rather than to a guardrail, so observability
        does not record a safety rule that never fired.
        """
        return GuardrailResult(
            checkpoint=checkpoint,
            blocked=True,
            escalate=True,
            reason=(
                f"The Guardrail Engine failed while checking {checkpoint.value}: "
                f"{type(cause).__name__}: {cause}. Specification 8.9 requires a "
                "broken engine to block rather than pass."
            ),
            triggered_rule="engine.internal_failure",
        )
