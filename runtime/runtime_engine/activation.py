"""The production composition root — one function, no abstraction.

Recorded as **AUDIT-4**: until now nothing in `runtime/` assembled an activated
engine. The chain below was performed only by a test helper, which meant the
*caller* owned every invariant a composition root should own — which is exactly
why AUDIT-1 and AUDIT-2 were reachable at all.

    filesystem
      → ProjectLoader        → ProjectContext
      → Resolver             → ResolvedContext
      → Validator            → ValidationResult
      → RuntimeEngine (which resolves the provider and derives its own budget)

**This is a construction function, not a second orchestrator.** §14.1 names one
module that calls the others in sequence, and `RuntimeEngine.handle_request` is
that path. Nothing here handles a message, builds a prompt, checks a guardrail,
calls a provider or a tool, manages a turn, or emits an event. Its job ends the
moment a correctly activated engine exists.

There is deliberately no `ActivationManager`, no factory class, no container, no
registry of activated engines, and no module-level state. A function that calls
seven constructors in order needs none of that, and every one of them would
become a place for project-scoped state to accumulate.

---

## The two invariants this function owns

**Project-scoped collaborators (AUDIT-2).** Every activation constructs its own
`SessionManager` and `WorkflowStateManager`. They are **not parameters**, so
there is no way to hand the same store to two projects through this path.

That matters because §12.6 and §7.6 are frozen and key every method on
`conversation_id` alone — `appendTurn(conversation_id, …)`,
`getState(conversation_id)`. Two projects sharing one store and receiving a
colliding conversation id will interleave their conversations, and neither
manager can detect it. Rather than amend a frozen signature, the fix is scoping:
**a conversation-id namespace belongs to exactly one project**, and constructing
the stores here is what makes that true.

**Provider-bound budget (AUDIT-1).** This function does *not* build a budget and
does *not* accept one. `RuntimeEngine` derives it from the binding of the
provider the project actually resolves to. Passing one through here would
re-open the very injection point AUDIT-1 exists to close.

## What is not yet reachable through this path

`activate` takes exactly the four arguments its contract names, so the engine it
returns has an empty `ToolExecutor` and the null observability sink. Both are
correct *today* — nothing produces a `ToolRequest` (TE-1), and §15 does not
exist (RE-4). When either changes, this signature is where the wiring goes.
"""

from __future__ import annotations

from pathlib import Path

from runtime.guardrail import GuardrailEngine
from runtime.loader import FilesystemProjectSource, ProjectLoader
from runtime.models.core_bundle import CoreBundle
from runtime.provider_registry import ProviderRegistry
from runtime.resolver import Resolver
from runtime.runtime_engine.engine import RuntimeEngine
from runtime.session import SessionManager
from runtime.tool_executor import ToolExecutor
from runtime.validation import Validator
from runtime.workflow_router import WorkflowRouter
from runtime.workflow_state import WorkflowStateManager


def activate(
    core: CoreBundle,
    projects_root: str | Path,
    project_id: str,
    providers: ProviderRegistry,
) -> RuntimeEngine:
    """Activate one project and return an engine bound to it.

    `core` arrives already loaded because the frozen `CoreBundle` row says it is
    *"created once at process startup; lives for the process lifetime"*. Loading
    it inside a per-project function would re-read `core/` once per project,
    contradicting that lifecycle for any deployment serving more than one.

    Raises rather than returning a partly-activated engine:

    * `ProjectNotFoundError` / `InvalidProjectIdError` — the project cannot be
      loaded;
    * `ProjectNotActivatedError` — it loaded but did not pass validation, or the
      result does not describe this project (§14.10's hard precondition, enforced
      once by `RuntimeEngine` rather than re-implemented here);
    * a normalised `ProviderError` — its declared provider is not registered, or
      the registered adapter is bound to a different model.

    Validation runs **here, once**, not per message. §14.2 places the go/no-go
    decision *"at project-activation/deploy time — not re-validated on every
    single message, for performance"*, and `handle_request` never asks again.

    No network call occurs. The Loader reads the filesystem, the Resolver and
    Validator are pure over in-memory structures, and provider resolution inside
    the engine is a registry lookup over already-constructed adapters.
    """
    project = ProjectLoader(FilesystemProjectSource(projects_root)).load(project_id)
    resolved_context = Resolver().resolve(core, project)
    validation = Validator(provider_registry=providers).validate_project(project, core)

    # The invalid case is refused by RuntimeEngine's own activation gate rather
    # than by a second check here: §14.10 has one owner, and two implementations
    # of one precondition is how they drift apart.
    return RuntimeEngine(
        resolved_context=resolved_context,
        validation=validation,
        core=core,
        sessions=SessionManager(),
        guardrails=GuardrailEngine(core),
        providers=providers,
        router=WorkflowRouter(),
        states=WorkflowStateManager(),
        tools=ToolExecutor(),
    )
