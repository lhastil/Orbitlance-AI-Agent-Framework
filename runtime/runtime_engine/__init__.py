"""Runtime Engine — specification §14.

Public surface:

    activate                  the production composition root
    RuntimeEngine             the orchestrator; one activated project each
    RuntimeRequest            §14.4's incoming request
    RuntimeResponse           §14.5's output to the channel adapter
    ProjectNotActivatedError  §14.10's gate, raised at construction only

The engine is constructed for **one validated, resolved project** and answers
`handle_request` for that project only. Activation is a construction
precondition, not a per-message check (§14.2, §14.10).

`activate` is the production path: it loads, resolves and validates a project,
then constructs the engine with collaborators scoped to that project alone —
including its own Audit Logger. The `RuntimeEngine` constructor remains public
and is the seam tests and future callers use directly; it enforces the
activation gate and derives its own budget, but it accepts whatever session,
workflow and audit collaborators it is given, so scoping is a guarantee of
`activate`, not of the constructor.

**The observability contract now lives in §15.** This package no longer defines
`ObservabilitySink` or `NullObservabilitySink`: the placeholder they existed to
be was replaced when `runtime.observability` was built, as its own docstring
said it would be. The engine depends on `runtime.observability.AuditLog` and
owns none of the audit semantics — see `engine`.

**What this milestone still does not do**, each recorded rather than implied:

* it starts no concurrency and establishes no thread-safety contract (RE-3);
* it composes no customer-facing fallback text; a blocked turn carries flags and
  no text (RE-5);
* its tool stage is a typed no-op, because nothing produces a `ToolRequest`
  (TE-1), and it never fabricates one;
* it adds no second provider pass, so a tool result cannot reach the customer on
  the same turn (TE-5).
"""

from runtime.models.runtime import RuntimeRequest, RuntimeResponse
from runtime.runtime_engine.activation import activate
from runtime.runtime_engine.engine import RuntimeEngine
from runtime.runtime_engine.errors import ProjectNotActivatedError

__all__ = [
    "ProjectNotActivatedError",
    "RuntimeEngine",
    "RuntimeRequest",
    "RuntimeResponse",
    "activate",
]
