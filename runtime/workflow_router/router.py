"""Workflow Router — specification §6.

Decides, each turn, which workflow is active, and returns a **candidate**
`WorkflowTransitionDecision`. It persists nothing: §6.3 makes it a pure decision
function and the Workflow State Manager owns persistence. It never imports
Module 7, never calls a provider, and never touches the filesystem or network.

A leaf: §6.7 allows Core Loader (for workflow definitions) and optionally the
Provider Interface. The provider path is **not** implemented — see D-4.

---

## What this router does, and what it deliberately does not

**It is deterministic, not semantic, and its vocabulary is Core's.** §6.2 says
to consult each workflow's documented Trigger and Decision Point rules from
`CoreBundle` against the current state and latest message. Those prose rules are
written for a human or a language model, not as conditions a program can
evaluate:

* five of six define a Decision Point (all but `voice_agent`), and every one
  of them turns on a judgement rather than a checkable condition — *"If
  sufficient information has been collected"*, *"If the customer accepts the
  recommendation"*, *"If the customer confirms the information"*, *"If the
  customer responds"*;
* `crm_sync`'s *"If synchronization succeeds"* depends on a tool-execution
  result, which `route()` is not given either;
* several Triggers name events this module cannot observe with the inputs §6.6
  gives it — *"A consultation request is submitted"*, *"A lead becomes
  qualified"* — which belong to the unbuilt Tool Executor;
* `voice_agent` triggers on the conversation's channel, and `route()` receives
  no channel.

Inventing keyword heuristics to bridge that gap would quietly make this file the
framework's routing semantics, resting on nothing in the specification. So it
does not — the bridge is authored in `core/workflows/` instead. Three rules:

**R-1 — a new conversation routes to the first-turn workflow.** This is not a
guess: `core/workflows/discovery.md`'s own Trigger names *"A new conversation
begins"* as a condition to start it, and `recommendation.md` says to start
*"only after the Discovery Workflow has collected sufficient information"*.
Discovery is where the framework's own documents say a conversation begins.

**R-2 — a Core-published phrase advances the conversation (WR-1, ruled
2026-09-05).** A workflow may publish a "Routing Phrases" section naming, per
third-level heading, a workflow it routes to and the phrases that take a
conversation there. This module reads that section and matches; **it defines no
phrase and no ordering.** Edit the document and routing changes with it, with no
Python to keep in step — which is the whole point: routing semantics stay in
`core/`, beside the workflows they belong to.

Two workflows publish one today, `discovery → recommendation` and
`recommendation → consultation`. What that vocabulary is, and is not, is stated
in the documents themselves: for `discovery` it is a **message-shaped readiness
signal**, not an evaluation of accumulated `collected_data`, because nothing
collects any. No workflow publishes a **backward** target, so a conversation does
not regress — an invariant of Core's content and its tests, deliberately not an
ordering table in this file.

**R-3 — otherwise, stay put.** §6.9: *"Ambiguous input with no clear signal →
default to remaining in the current workflow (conservative — avoids
workflow-thrashing)."* Anything Core has not published a phrase for is ambiguous
by that definition, so the current workflow is retained.

Still out of scope, and still not approximated: `crm_sync`'s tool-result
condition (**TE-5 / TE-1**), `voice_agent`'s channel (**AUDIT-5**), and what it
means for the Consultation workflow to *complete* (**WR-2**). The provider-backed
classification §6.3 and §6.7 permit as a secondary signal is not implemented
(D-4).

**`collected_data` is always empty.** §6.4's inputs are a state, a message and
Core's definitions; nothing in the specification defines what to extract from a
message or how. Returning an empty mapping is the only honest answer, and
Module 7 persists exactly what it is given, so an invented extraction would
become durable conversation state on no authority at all.
"""

from __future__ import annotations

from runtime.models.conversation import WorkflowState
from runtime.models.core_bundle import CoreBundle
from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_router.errors import UndefinedWorkflowError

#: The workflow a brand-new conversation starts in (R-1).
#:
#: Declared once, here, so the choice is a single reviewable decision rather
#: than a string repeated across the module. Source: `core/workflows/discovery.md`
#: Trigger — *"A new conversation begins"* — and `recommendation.md`'s
#: *"only after the Discovery Workflow has collected sufficient information"*.
FIRST_TURN_WORKFLOW: str = "discovery"

#: `CoreBundle.workflows` is keyed by filename; decisions name the stem, which is
#: the canonical id `ResolvedConfig.enabled_workflows` and `WorkflowState` use.
WORKFLOW_SUFFIX: str = ".md"

#: Where a workflow publishes the phrases that route out of it (WR-1, ruled
#: 2026-09-05). **An address into a Core document, not the policy itself.** The
#: phrases, and the workflow each one routes to, are declared in
#: `core/workflows/*.md` and read from there per call, so this module enforces
#: whatever Core currently says and never becomes the authority for it.
#:
#: **Private, and deliberately the only routing constant here.** There is no
#: ordering table, no from/to map and no list of workflow names: a subsection's
#: heading names its own target, so the permitted progression is entirely
#: Core-declared. A hardcoded ordering policy in Python is exactly what the
#: ruling forbids.
_ROUTING_SECTION: str = "Routing Phrases"


class WorkflowRouter:
    """Proposes the active workflow for a turn (§6.6).

    Stateless and side-effect free. `route` is a pure function of its arguments:
    identical inputs produce an equal decision, nothing is stored, and neither
    the `WorkflowState` nor the `CoreBundle` it is given is modified.
    """

    __slots__ = ("_first_turn_workflow",)

    def __init__(self, *, first_turn_workflow: str = FIRST_TURN_WORKFLOW) -> None:
        """`first_turn_workflow` is injectable for tests, not for configuration.

        A project cannot choose its own starting workflow through this: the
        Router receives no `ResolvedContext` (§6.6 fixes the signature), so it
        cannot know what a project enabled. Project scope is enforced by the
        Prompt Assembler and, later, the Runtime Engine.
        """
        self._first_turn_workflow = first_turn_workflow

    def route(
        self,
        current_state: WorkflowState,
        latest_message: str,
        core_bundle: CoreBundle,
    ) -> WorkflowTransitionDecision:
        """The candidate transition for this turn (§6.5 — not yet committed).

        `latest_message` is consulted against the phrases the **active workflow**
        publishes under its "Routing Phrases" section (§6.2, WR-1). A match
        advances the conversation to the workflow that section names; anything
        else keeps it where it is, which is §6.9's conservative default.

        Deterministic and provider-free: a case-insensitive substring scan over
        a list read from an already-loaded document. §6.3 makes that the primary
        mechanism and permits an LLM only as a secondary signal for genuinely
        ambiguous cases — that path remains unimplemented (D-4).
        """
        target = (
            current_state.active_workflow
            if current_state.active_workflow is not None
            else self._first_turn_workflow
        )
        reason = (
            "it is not defined in Core"
            if current_state.active_workflow is None
            else "the conversation's active workflow is no longer defined in Core"
        )
        self._assert_defined(target, core_bundle, reason)

        # Only an established workflow routes onward. A first turn has just been
        # placed in the first-turn workflow and has nothing to advance from yet.
        if current_state.active_workflow is not None:
            proposed = self._published_target(target, latest_message, core_bundle)
            if proposed is not None:
                self._assert_defined(
                    proposed,
                    core_bundle,
                    f"{target!r} publishes a routing phrase for it, but Core does "
                    "not define it",
                )
                target = proposed

        # D-3: nothing in the specification defines what to extract from a
        # message, so nothing is extracted. Module 7 persists what it is given;
        # an invented extraction would become durable state on no authority.
        return WorkflowTransitionDecision(target_workflow=target, collected_data={})

    # -- §6.2: the Core-published routing vocabulary --------------------------
    @staticmethod
    def _published_target(
        active: str, latest_message: str, core_bundle: CoreBundle
    ) -> str | None:
        """The workflow Core says this message routes to, or None.

        Reads the active workflow's own document: every third-level heading that
        follows its "Routing Phrases" section names a target, and the bullet
        list under it is that target's vocabulary. **The heading is the target**,
        which is why this module needs no ordering table — Core declares both
        the phrases and where they lead, and a workflow that publishes nothing
        routes nowhere.

        Sections are addressed through the decomposition the Core Loader already
        produced, so nothing here parses markdown beyond stripping a bullet's
        `- `. §6.7 allows Core Loader, not Module 2, so no markdown helper is
        imported.

        Order follows the document, and the first match wins: a message that
        matches two phrases is advancing either way, and reporting Core's own
        first answer is more honest than ranking them by a rule nobody wrote.
        """
        document = core_bundle.workflows.get(f"{active}{WORKFLOW_SUFFIX}")
        if document is None:
            return None

        haystack = latest_message.casefold()
        seen_routing_section = False
        for section in document.sections:
            if section.heading_level <= 2:
                seen_routing_section = (
                    section.normalised_heading == _ROUTING_SECTION.casefold()
                )
                continue
            if not seen_routing_section or section.heading_level != 3:
                continue
            for line in section.body.splitlines():
                stripped = line.strip()
                if not stripped.startswith("- ") or len(stripped) <= 2:
                    continue
                if stripped[2:].strip().casefold() in haystack:
                    return section.heading_text.strip()
        return None

    # -- §6.10 ---------------------------------------------------------------
    @staticmethod
    def _assert_defined(workflow: str, core_bundle: CoreBundle, reason: str) -> None:
        """§6.10: a decision must name a workflow that exists in `CoreBundle`.

        Core existence only. Whether the *project* enabled it is a different
        question and a different module's: `route()` never receives a
        `ResolvedContext`, so it cannot see `enabled_workflows`, and the Prompt
        Assembler already enforces that scope as defence in depth.
        """
        if f"{workflow}{WORKFLOW_SUFFIX}" in core_bundle.workflows:
            return
        available = tuple(
            sorted(
                name[: -len(WORKFLOW_SUFFIX)]
                for name in core_bundle.workflows
                if name.endswith(WORKFLOW_SUFFIX)
            )
        )
        raise UndefinedWorkflowError(workflow, available, reason)
