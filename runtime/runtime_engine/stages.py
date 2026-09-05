"""The Runtime Engine's pipeline stages — specification §14.

§14's composition decision is a requirement, not a style note:

> `handleRequest` must be implemented as an **ordered, injected list of pipeline
> stages**, not a single hand-written function body. Each stage wraps exactly one
> module call… Guardrail pre-flight and post-response stages are
> **non-removable** — the composition mechanism must not allow a configuration
> that omits them.

So each class below wraps one module's call, and `build_pipeline` is the only
way to obtain a pipeline. It takes collaborators, never a stage list, which is
what makes the two guardrail stages structurally impossible to omit: there is no
argument through which a caller could leave one out, reorder the sequence, or
substitute a permissive stand-in.

## Order

Taken from §14.2's sequence verbatim:

    resolve project + session → pre-flight guardrail check → prompt assembly
    → provider call → post-response guardrail check → workflow routing/state
    commit → tool execution → response delivery → observability logging

Two notes on how that maps to the tuple below.

* §14.2 places **workflow routing/state commit before tool execution**. The
  authorization for this milestone sketched the reverse; §14.2 is frozen and
  wins, and the discrepancy is reported rather than quietly resolved.
* Loading the conversation's `WorkflowState` is part of §14.2's first step,
  "resolve project + session" — it is not a separate concern the specification
  omitted. It has its own stage only because §4.6's frozen `assemble` signature
  requires a `WorkflowState`, so it must be in hand before assembly, and one
  stage per module call is the rule.

Observability is not a member of this tuple. A stage in the list would be
skipped whenever a guardrail block or a contained failure short-circuits the
turn — and those are exactly the turns most worth recording. It is the engine's
own final act instead; see `engine`.

## Short-circuiting

A stage that concludes the turn sets `TurnState.outcome`, and the engine stops
there. §14.12(b) requires a pre-flight block to short-circuit *before any
provider call*: that holds structurally here, because the provider stage is
simply never reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from runtime.assembler import PromptAssembler
from runtime.assembler.ports import TokenBudgetPort
from runtime.guardrail import GuardrailEngine
from runtime.models.conversation import (
    ConversationContext,
    Turn,
    TurnRole,
    WorkflowState,
)
from runtime.models.core_bundle import CoreBundle
from runtime.models.guardrail import GuardrailResult
from runtime.models.prompt_bundle import PromptBundle
from runtime.models.provider import ProviderResponse
from runtime.models.resolved_context import ResolvedContext
from runtime.models.runtime import RuntimeRequest, RuntimeResponse
from runtime.models.tool import ToolRequest, ToolResponse
from runtime.provider_registry import ProviderRegistry
from runtime.session import SessionManager
from runtime.tool_executor import ToolExecutor
from runtime.workflow_router import WorkflowRouter
from runtime.workflow_state import WorkflowStateManager


@dataclass(slots=True)
class TurnState:
    """One request's working state. Request-local, never shared, never stored.

    The only mutable object in this package. It exists because composed stages
    have to hand work to one another, and threading nine values through nine
    signatures would rebuild the monolithic body §14's composition decision
    exists to prevent.

    It is not a data model: nothing outside a single `handle_request` call sees
    one, and none of it is persisted.
    """

    request: RuntimeRequest
    conversation: ConversationContext | None = None
    workflow_state: WorkflowState | None = None
    bundle: PromptBundle | None = None
    provider_response: ProviderResponse | None = None
    pre_flight: GuardrailResult | None = None
    post_response: GuardrailResult | None = None
    #: Always `None` today — nothing in this runtime produces one (TE-1).
    tool_request: ToolRequest | None = None
    tool_response: ToolResponse | None = None
    #: Set by whichever stage concludes the turn. Non-None stops the pipeline.
    outcome: RuntimeResponse | None = None


@runtime_checkable
class Stage(Protocol):
    """One pipeline step, wrapping one module's call."""

    name: str

    def run(self, state: TurnState) -> None:
        ...


# --- §14.2 step 1: resolve project + session ---------------------------------
class SessionStage:
    """Records the incoming turn through the Session Manager (§12).

    Creates the conversation on first contact, then appends the user's turn.
    The Session Manager's own contract prescribes this ordering: *"The Runtime
    Engine calls this before the provider call with the user's turn… Appending
    the user turn first is what makes `latest_user_message` and the Budget
    Manager's history window correct, and it is what preserves the user's
    message when the provider call fails."*
    """

    __slots__ = ("_sessions", "_project_id", "name")

    def __init__(self, sessions: SessionManager, project_id: str) -> None:
        self._sessions = sessions
        self._project_id = project_id
        self.name = "session"

    def run(self, state: TurnState) -> None:
        conversation_id = state.request.conversation_id
        if not self._sessions.exists(conversation_id):
            self._sessions.create_session(
                conversation_id, self._project_id, channel=state.request.channel
            )
        state.conversation = self._sessions.append_turn(
            conversation_id, Turn(role=TurnRole.USER, content=state.request.message)
        )


class WorkflowStateStage:
    """Loads the conversation's workflow state (§7.6).

    Part of §14.2's "resolve project + session" step. `get_state` creates an
    empty state on first access — the data-model row's "created on first
    message" — and that empty state chooses nothing: `active_workflow` stays
    `None` until the Router commits a transition.
    """

    __slots__ = ("_states", "name")

    def __init__(self, states: WorkflowStateManager) -> None:
        self._states = states
        self.name = "workflow_state"

    def run(self, state: TurnState) -> None:
        state.workflow_state = self._states.get_state(state.request.conversation_id)


# --- §14.2 step 2: pre-flight guardrail (NON-REMOVABLE) ----------------------
class PreFlightGuardrailStage:
    """Checks the incoming message before any provider call (§8.2).

    **Non-removable.** A block ends the turn here, so §14.12(b) — *"assert
    Provider Registry's `generate` was never invoked"* — holds structurally
    rather than by inspection.

    Worth saying plainly, because a stage that always passes is easy to mistake
    for coverage: **the Guardrail Engine's pre-flight check applies no content
    rule today.** Every automatic escalation condition is semantic prose with no
    deterministic evaluator, and the engine publishes that through
    `UNENFORCED_CORE_CONDITIONS`. This stage is wired and real, and it will
    block the moment the engine can — it just cannot block on message text yet.
    """

    __slots__ = ("_guardrails", "_context", "name")

    def __init__(self, guardrails: GuardrailEngine, context: ResolvedContext) -> None:
        self._guardrails = guardrails
        self._context = context
        self.name = "pre_flight_guardrail"

    def run(self, state: TurnState) -> None:
        result = self._guardrails.check_pre_flight(state.request.message, self._context)
        state.pre_flight = result
        if result.blocked:
            state.outcome = RuntimeResponse(blocked=True, escalate=result.escalate)


# --- §14.2 step 3: prompt assembly -------------------------------------------
class PromptAssemblyStage:
    """Builds this turn's `PromptBundle` (§4) — always budgeted.

    The assembler is constructed once, here, **with a required
    `TokenBudgetPort`**. That is the mechanism behind ruling D-1(b): Module 4
    still accepts `token_budget=None` and then silently answers "everything
    fits" without measuring (recorded as RE-1), and §14 makes that path
    unreachable by never offering it. The port is a positional constructor
    argument of this stage, so no assembler in this package can exist without
    one.

    The bundle's `degraded` flag is carried forward rather than re-derived.
    Module 4 decides degradation when Knowledge is missing; second-guessing it
    here would put a resolution judgement in the wrong module.
    """

    __slots__ = ("_assembler", "_context", "name")

    def __init__(
        self,
        core: CoreBundle,
        context: ResolvedContext,
        token_budget: TokenBudgetPort,
    ) -> None:
        self._assembler = PromptAssembler(core, token_budget=token_budget)
        self._context = context
        self.name = "prompt_assembly"

    def run(self, state: TurnState) -> None:
        assert state.conversation is not None
        assert state.workflow_state is not None
        state.bundle = self._assembler.assemble(
            self._context, state.workflow_state, state.conversation
        )


# --- §14.2 step 4: provider call ---------------------------------------------
class ProviderStage:
    """Sends the bundle through the Provider Registry (§10.6).

    Delegates entirely: the Registry selects this project's provider, attempts
    the configured secondary on a transient failure, and normalises the rest.
    Nothing about provider behaviour is decided here — §14.3 calls that a
    "maintainability red flag" and §10.3 keeps the calling logic on the far side
    of this seam.

    The raw, unbudgeted history goes in the `history` argument and the budgeted
    window travels inside the bundle. P-1 makes which one reaches the payload
    the adapter's contract, not a choice available here.
    """

    __slots__ = ("_registry", "_context", "name")

    def __init__(self, registry: ProviderRegistry, context: ResolvedContext) -> None:
        self._registry = registry
        self._context = context
        self.name = "provider"

    def run(self, state: TurnState) -> None:
        assert state.bundle is not None
        assert state.conversation is not None
        state.provider_response = self._registry.generate_with_fallback(
            self._context, state.bundle, state.conversation.history
        )


# --- §14.2 step 5: post-response guardrail (NON-REMOVABLE) -------------------
class PostResponseGuardrailStage:
    """Checks the generated answer before it can reach the customer (§8.2).

    **Non-removable**, and §8.3 forbids skipping it *"to save latency or
    cost"*. A block ends the turn carrying no text: §8.3 assigns composing a
    safe alternative elsewhere, and this engine does not invent one (RE-5).
    """

    __slots__ = ("_guardrails", "_context", "name")

    def __init__(self, guardrails: GuardrailEngine, context: ResolvedContext) -> None:
        self._guardrails = guardrails
        self._context = context
        self.name = "post_response_guardrail"

    def run(self, state: TurnState) -> None:
        assert state.provider_response is not None
        result = self._guardrails.check_post_response(
            state.provider_response, self._context
        )
        state.post_response = result
        if result.blocked:
            state.outcome = RuntimeResponse(blocked=True, escalate=result.escalate)


# --- §14.2 step 6: workflow routing + state commit ---------------------------
class WorkflowStage:
    """Routes and commits the workflow transition (§6, §7).

    §14.2 names "workflow routing/state commit" as one step and it stays one:
    the Router proposes and never writes, the Manager writes and never decides.

    The Router returns "stay in the active workflow" for every turn after the
    first — every transition its documents describe turns on a semantic
    judgement it refuses to fabricate. The seam is real; the routing is not yet
    intelligent, and this stage does not compensate for that.
    """

    __slots__ = ("_router", "_states", "_core", "name")

    def __init__(
        self, router: WorkflowRouter, states: WorkflowStateManager, core: CoreBundle
    ) -> None:
        self._router = router
        self._states = states
        self._core = core
        self.name = "workflow"

    def run(self, state: TurnState) -> None:
        assert state.workflow_state is not None
        decision = self._router.route(
            state.workflow_state, state.request.message, self._core
        )
        state.workflow_state = self._states.commit_transition(
            state.request.conversation_id, decision
        )


# --- §14.2 step 7: tool execution --------------------------------------------
class ToolStage:
    """The tool seam (§11) — a typed no-op until a producer exists.

    **Nothing in this runtime produces a `ToolRequest`.** The Workflow Router
    emits only a transition, `WorkflowState` carries no tool field, and the one
    provider adapter declares `tool_calling_support=False` while §9.11 defers
    provider tool-calling *"once Tool Executor integrates"*. The two clauses
    defer to each other; that circle is TE-1 and is not resolved here.

    So this stage does exactly one thing: if a request is present it executes
    it, and otherwise it does nothing. It does **not** infer a tool from the
    active workflow, the message, the integrations documents or the provider's
    text. Fabricating a request would mean inventing when a workflow calls for
    an action — precisely the semantics nobody has defined.

    A `ToolResponse`, if one is ever produced, is recorded on the turn state and
    is **not** sent to the customer and **not** fed back to the model: §14.2's
    pipeline has no second generation pass, and inventing one is forbidden
    (TE-5). Where it should go is §14's open question; the field exists so the
    answer has somewhere to land.
    """

    __slots__ = ("_tools", "_context", "name")

    def __init__(self, tools: ToolExecutor, context: ResolvedContext) -> None:
        self._tools = tools
        self._context = context
        self.name = "tool"

    def run(self, state: TurnState) -> None:
        if state.tool_request is None:
            return
        state.tool_response = self._tools.execute(state.tool_request, self._context)


# --- §14.2 step 8: response delivery -----------------------------------------
class DeliveryStage:
    """Turns a completed turn into a `RuntimeResponse` (§14.5).

    Also appends the agent's turn, the second half of the Session Manager's
    prescribed usage: *"and again afterwards with the response."*

    It is reached only when nothing blocked, because a block short-circuits
    earlier — and that ordering is what keeps a blocked answer out of the
    durable record. A response the customer never saw must not become an agent
    turn that the next prompt shows the model as delivered. §14 states no rule
    for this; the decision is recorded as RE-6.

    **Escalation is the union of both checkpoints.** A pre-flight escalation
    that does not block — a customer asking for a person — reaches this stage
    with the turn still running, and would be lost if only the post-response
    verdict were read. Authorized by GE-1's ruling (2026-09-05) as the one
    §14 change that ruling requires; no other escalation policy is introduced
    here, and whether an internal failure should escalate remains AUDIT-6.
    """

    __slots__ = ("_sessions", "name")

    def __init__(self, sessions: SessionManager) -> None:
        self._sessions = sessions
        self.name = "delivery"

    def run(self, state: TurnState) -> None:
        assert state.provider_response is not None
        text = state.provider_response.text
        self._sessions.append_turn(
            state.request.conversation_id, Turn(role=TurnRole.AGENT, content=text)
        )
        state.outcome = RuntimeResponse(
            text=text,
            escalate=any(
                verdict is not None and verdict.escalate
                for verdict in (state.pre_flight, state.post_response)
            ),
            degraded=bool(state.bundle is not None and state.bundle.degraded),
        )


def build_pipeline(
    *,
    core: CoreBundle,
    context: ResolvedContext,
    sessions: SessionManager,
    guardrails: GuardrailEngine,
    token_budget: TokenBudgetPort,
    providers: ProviderRegistry,
    router: WorkflowRouter,
    states: WorkflowStateManager,
    tools: ToolExecutor,
) -> tuple[Stage, ...]:
    """The one way to obtain a pipeline. Order is §14.2's.

    **Takes collaborators, never a stage list.** That is the mechanism §14's
    composition decision asks for — *"the composition mechanism must not allow a
    configuration that omits"* the guardrail stages. There is no argument
    through which a caller could drop one, reorder the sequence, or replace a
    guardrail with something permissive.
    """
    return (
        SessionStage(sessions, context.project_id),
        WorkflowStateStage(states),
        PreFlightGuardrailStage(guardrails, context),
        PromptAssemblyStage(core, context, token_budget),
        ProviderStage(providers, context),
        PostResponseGuardrailStage(guardrails, context),
        WorkflowStage(router, states, core),
        ToolStage(tools, context),
        DeliveryStage(sessions),
    )
