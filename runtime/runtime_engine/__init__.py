"""Runtime Engine — specification §14.

Public surface:

    RuntimeEngine             the orchestrator; one activated project each
    RuntimeRequest            §14.4's incoming request
    RuntimeResponse           §14.5's output to the channel adapter
    ObservabilitySink         the §14-local seam §15 will replace
    NullObservabilitySink     the default: records nothing
    ProjectNotActivatedError  §14.10's gate, raised at construction only

The engine is constructed for **one validated, resolved project** and answers
`handle_request` for that project only. Activation is a construction
precondition, not a per-message check (§14.2, §14.10).

**What this milestone does not do**, each recorded rather than implied:

* it starts no concurrency and establishes no thread-safety contract (RE-3);
* it emits no audit trail by default — the null sink records nothing (RE-4);
* it composes no customer-facing fallback text; a blocked turn carries flags and
  no text (RE-5);
* its tool stage is a typed no-op, because nothing produces a `ToolRequest`
  (TE-1), and it never fabricates one;
* it adds no second provider pass, so a tool result cannot reach the customer on
  the same turn (TE-5).
"""

from runtime.models.runtime import RuntimeRequest, RuntimeResponse
from runtime.runtime_engine.engine import RuntimeEngine
from runtime.runtime_engine.errors import ProjectNotActivatedError
from runtime.runtime_engine.ports import NullObservabilitySink, ObservabilitySink

__all__ = [
    "NullObservabilitySink",
    "ObservabilitySink",
    "ProjectNotActivatedError",
    "RuntimeEngine",
    "RuntimeRequest",
    "RuntimeResponse",
]
