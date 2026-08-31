"""Workflow Router — specification §6.

Decides, each turn, which workflow is active, and returns a **candidate**
`WorkflowTransitionDecision`. It persists nothing: §6.3 makes it a pure decision
function and the Workflow State Manager owns persistence. It never imports
Module 7, never calls a provider, and never touches the filesystem or network.

A leaf: §6.7 allows Core Loader (for workflow definitions) and optionally the
Provider Interface. The provider path is **not** implemented — see D-4.

---

## What this router does, and what it deliberately does not

**It is structural, not semantic.** §6.2 says to consult each workflow's
documented Trigger and Decision Point rules from `CoreBundle`. Read against the
actual documents, those rules are prose written for a human or a language model,
not conditions a program can evaluate:

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
does not. What remains is genuinely deterministic, and it is exactly two rules:

**R-1 — a new conversation routes to the first-turn workflow.** This is not a
guess: `core/workflows/discovery.md`'s own Trigger names *"A new conversation
begins"* as a condition to start it, and `recommendation.md` says to start
*"only after the Discovery Workflow has collected sufficient information"*.
Discovery is where the framework's own documents say a conversation begins.

**R-2 — otherwise, stay put.** §6.9: *"Ambiguous input with no clear signal →
default to remaining in the current workflow (conservative — avoids
workflow-thrashing)."* With no evaluable transition rule available, every input
is ambiguous by that definition, so the current workflow is retained.

The consequence is honest and worth stating: **this router never advances a
conversation past its first workflow.** Advancing requires evaluating
"sufficient information has been collected", which is a semantic judgement the
frozen documents delegate to the AI and §6.3 wants kept off the deterministic
path. That sentence is asserted by test, so the limitation cannot quietly stop
being true. Closing the gap needs either machine-readable rules authored in
`core/workflows/` or the provider-backed classification §6.7 permits — both
deliberately out of scope here.

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

        `latest_message` is part of the frozen signature and is accepted in full,
        but no rule currently evaluates it: every transition the workflow
        documents describe turns on a semantic judgement this module will not
        fabricate. It is named rather than ignored so the seam is ready for the
        day real rules exist.
        """
        del latest_message  # no deterministic rule consults it yet — see R-2

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

        # D-3: nothing in the specification defines what to extract from a
        # message, so nothing is extracted. Module 7 persists what it is given;
        # an invented extraction would become durable state on no authority.
        return WorkflowTransitionDecision(target_workflow=target, collected_data={})

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
