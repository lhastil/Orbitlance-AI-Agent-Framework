"""Runtime Engine — specification §14.

The top-level orchestrator: the only module that calls the others in sequence
(§14.1), and the only one that depends on all of them (§14.7). Nothing depends
back on it, so the graph stays a DAG with this module as its single root.

It implements no other module's logic. §14.3 is blunt about why — *"If Runtime
Engine starts containing prompt-building or guardrail logic directly, that's a
maintainability red flag and a violation of every other module's single
responsibility."* Every stage here wraps one call and interprets its result;
none reproduces one.

---

## Activation happens at construction, not per message

§14.10 makes a passed `ValidationResult` *"a hard precondition"*, and §14.2
places the decision *"at project-activation/deploy time — not re-validated on
every single message, for performance."* Both are satisfied the same way: an
engine cannot be constructed for a project that has not passed validation, so
`handle_request` never has to ask.

    validate → activate → resolve → RuntimeEngine(...) → handle_request(...)

**The activation state is not a new type.** `ValidationResult` and
`ResolvedContext` already carry everything §14 needs — the former proves the
project passed and names its subject, the latter is the resolved project. A
wrapper around them would duplicate both and add nothing, so the constructor
takes them directly and binds them by checking that they describe the same
project. That check is the activation state: after it passes, the pair provably
belong together.

**Resolution is retained, not repeated.** The `ResolvedContext` supplied at
construction is used for every turn. §14.2's "not re-validated on every single
message" is about validation, but re-resolving per message would recompute the
same answer from unchanged files. Who *owns* caching remains unassigned (R3-2);
this module simply holds what it was given and invalidates nothing.

## Cross-project identity

`handle_request` refuses a request whose `project_id` differs from the activated
project, before any provider or tool call. An engine is bound to one project;
serving another's request through it would run one client's message against a
second client's Knowledge, provider and integrations. §14 states no such rule —
this is a §14-local boundary check, and it does **not** close TE-7, which
concerns the Tool Executor's own unguarded boundary.

## Failure containment

§14.9: *"Any single module's failure must be caught and translated into the
appropriate degraded response — Runtime Engine is the layer responsible for
ensuring a lower-level exception never becomes a raw, unhandled crash reaching
the user."*

So every stage runs inside a guard, and any exception becomes a degraded
`RuntimeResponse`. **No repository-wide exception base was introduced** to make
that possible: the runtime holds 51 exception classes across twelve unrelated
hierarchies, and unifying them would mean editing twelve committed modules for
no behaviour this clause does not already get from catching broadly.

Two failure shapes are handled differently on purpose. A guardrail block and a
tool failure are *values* — `GuardrailResult` and `ToolResponse` — because §8.9
and §11.5 make them so; they are read, never caught. Everything else raises, and
raising is contained.

**No exception text ever reaches `RuntimeResponse`.** A vendor exception's
message and request URL are a known credential-bearing channel, which the
provider layer already goes to lengths to redact; re-exposing it in a customer
response would undo that at the last hop.

## Concurrency

**This module establishes no concurrent runtime contract.** One request is
executed start to finish on the calling thread. There is no async surface, no
thread, no executor, no pool, and no lock — a lock here would manufacture a
guarantee the specification never made, and §7.10 is the *only* atomicity clause
in the whole document.

That is a statement about §14 and nothing more. Several collaborators hold
mutable state without guarding it — the Session Manager, the two registries, the
Core Loader's cache — and the Validation Layer's rules are shared singletons
(V-7, ADR 0003, whose stated deadline is "before Runtime Engine adds
concurrency"). **Running this engine concurrently is unsupported**, and this
milestone does not make the repository thread-safe. Recorded as RE-3; V-7 and
C-10 stay open.

## Observability

§14.2 ends with "observability logging", and §15 does not exist. The engine
emits exactly one event per turn through an injected `ObservabilitySink`,
defaulting to one that does nothing.

It is the engine's own final act rather than a pipeline stage, deliberately: a
stage would be skipped whenever a block or a contained failure short-circuits
the turn, and those are the turns most worth recording. §15.9's rule that a
logging failure *"must not block the conversation from proceeding"* is honoured
by guarding the call — but note the other half of that clause, that a silent
audit gap is itself a Compliance risk, is currently unmet by the null default
(RE-4).
"""

from __future__ import annotations

from runtime.assembler.ports import TokenBudgetPort
from runtime.guardrail import GuardrailEngine
from runtime.models.core_bundle import CoreBundle
from runtime.models.resolved_context import ResolvedContext
from runtime.models.runtime import RuntimeRequest, RuntimeResponse
from runtime.models.validation import ValidationResult, ValidationTarget
from runtime.provider_registry import ProviderRegistry
from runtime.runtime_engine.errors import ProjectNotActivatedError
from runtime.runtime_engine.ports import NullObservabilitySink, ObservabilitySink
from runtime.runtime_engine.stages import Stage, TurnState, build_pipeline
from runtime.session import SessionManager
from runtime.tool_executor import ToolExecutor
from runtime.workflow_router import WorkflowRouter
from runtime.workflow_state import WorkflowStateManager

#: Event types this engine emits. One per turn, exactly one of these.
EVENT_TURN_COMPLETED = "runtime.turn_completed"
EVENT_TURN_BLOCKED = "runtime.turn_blocked"
EVENT_TURN_DEGRADED = "runtime.turn_degraded"
EVENT_REQUEST_REJECTED = "runtime.request_rejected"


class RuntimeEngine:
    """§14.6's single member, over an activated project."""

    __slots__ = ("_context", "_validation", "_pipeline", "_observability")

    def __init__(
        self,
        *,
        resolved_context: ResolvedContext,
        validation: ValidationResult,
        core: CoreBundle,
        sessions: SessionManager,
        guardrails: GuardrailEngine,
        token_budget: TokenBudgetPort,
        providers: ProviderRegistry,
        router: WorkflowRouter,
        states: WorkflowStateManager,
        tools: ToolExecutor,
        observability: ObservabilitySink | None = None,
    ) -> None:
        """Bind one validated, resolved project to its collaborators.

        `token_budget` is **required**. Module 4 accepts `None` and then answers
        "everything fits" without measuring anything; no engine path may reach
        that, so there is no default here to reach it with.

        Raises `ProjectNotActivatedError` if the validation result does not
        prove *this* project passed.
        """
        self._assert_activated(validation, resolved_context)
        self._context = resolved_context
        self._validation = validation
        self._observability = (
            observability if observability is not None else NullObservabilitySink()
        )
        self._pipeline: tuple[Stage, ...] = build_pipeline(
            core=core,
            context=resolved_context,
            sessions=sessions,
            guardrails=guardrails,
            token_budget=token_budget,
            providers=providers,
            router=router,
            states=states,
            tools=tools,
        )

    # -- activation gate (§14.10) --------------------------------------------
    @staticmethod
    def _assert_activated(
        validation: ValidationResult, context: ResolvedContext
    ) -> None:
        """§14.10's hard precondition, enforced once instead of per message."""
        if validation.target is not ValidationTarget.PROJECT:
            raise ProjectNotActivatedError(
                f"activation requires a project ValidationResult, not "
                f"{validation.target.value!r}"
            )
        if validation.subject_id != context.project_id:
            raise ProjectNotActivatedError(
                f"the validation result describes {validation.subject_id!r} but "
                f"the resolved context is {context.project_id!r}; an engine must "
                "not be assembled from two different projects"
            )
        if not validation.valid:
            raise ProjectNotActivatedError(
                f"project {context.project_id!r} has not passed validation "
                f"(coverage={validation.coverage.value}, "
                f"{len(validation.issues)} issue(s)); specification 14.10 makes "
                "that a hard precondition for accepting any request"
            )

    # -- properties -----------------------------------------------------------
    @property
    def project_id(self) -> str:
        """The single project this engine serves."""
        return self._context.project_id

    @property
    def stage_names(self) -> tuple[str, ...]:
        """The composed pipeline, in order. For inspection, never for editing."""
        return tuple(stage.name for stage in self._pipeline)

    # -- §14.6 ----------------------------------------------------------------
    def handle_request(self, request: RuntimeRequest) -> RuntimeResponse:
        """Run one turn end to end and return what the channel should deliver.

        Never raises. §14.9 makes containing every lower-level failure this
        module's job, so every outcome — completed, blocked, or degraded — comes
        back as a `RuntimeResponse`.
        """
        if request.project_id != self._context.project_id:
            self._observe(
                EVENT_REQUEST_REJECTED,
                request,
                {"reason": "project_id does not match the activated project"},
            )
            return RuntimeResponse(degraded=True)

        state = TurnState(request=request)
        failed_stage: str | None = None

        for stage in self._pipeline:
            try:
                stage.run(state)
            except Exception:  # noqa: BLE001 - §14.9: contain, never crash
                # Nothing from the exception travels onward. Its message may
                # carry a credential or a customer's data, and a degraded
                # response is what the caller is entitled to either way.
                failed_stage = stage.name
                state.outcome = RuntimeResponse(degraded=True)
                break
            if state.outcome is not None:
                break

        outcome = state.outcome
        if outcome is None:
            # No stage concluded the turn. That is a composition defect rather
            # than a runtime condition, and it fails closed like any other.
            failed_stage = failed_stage or "pipeline"
            outcome = RuntimeResponse(degraded=True)

        self._observe_outcome(request, outcome, failed_stage)
        return outcome

    # No `handleRequest` camelCase alias is published. §14.6 spells the member
    # that way and the Validation Layer publishes such aliases, but no ruling
    # sanctioned the convention repository-wide, and adding one here would make
    # §14 the second module to differ from the other twelve. Reported instead.

    # -- observability --------------------------------------------------------
    def _observe_outcome(
        self,
        request: RuntimeRequest,
        outcome: RuntimeResponse,
        failed_stage: str | None,
    ) -> None:
        if outcome.blocked:
            event = EVENT_TURN_BLOCKED
        elif outcome.degraded:
            event = EVENT_TURN_DEGRADED
        else:
            event = EVENT_TURN_COMPLETED

        payload = {
            "blocked": str(outcome.blocked),
            "escalate": str(outcome.escalate),
            "degraded": str(outcome.degraded),
            "channel": request.channel,
        }
        if failed_stage is not None:
            payload["failed_stage"] = failed_stage
        self._observe(event, request, payload)

    def _observe(
        self, event_type: str, request: RuntimeRequest, payload: dict[str, str]
    ) -> None:
        """Emit one event; a sink failure never becomes a conversation failure.

        §15.9 is explicit: a log store being unavailable *"must not block the
        conversation from proceeding"*. The payload carries only outcome facts —
        never the message, the prompt, or the provider's text — because §15.3
        forbids logging PII beyond an allowance nobody has written.
        """
        try:
            self._observability.record(
                event_type, request.project_id, request.conversation_id, payload
            )
        except Exception:  # noqa: BLE001 - §15.9: never blocks the conversation
            return
