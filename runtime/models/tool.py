"""ToolRequest and ToolResponse — the Tool Executor's boundary types.

Implements the two frozen data-model rows from docs/runtime-specification.md:

* **ToolRequest** — `toolContract, parameters, project_id, conversation_id`.
  *"Created by Workflow State Manager/Router when a workflow calls for an
  action; discarded after Tool Executor processes it."*
  **Workflow State Manager (sole writer); never contains credentials.**
* **ToolResponse** — `success, data, errorType (nullable),
  capability_unavailable`. *"Created by Tool Executor per call."*
  **Tool Executor (sole writer);** read by Workflow State Manager and
  Observability.

Four fields each, exactly as frozen. Nothing is added. The Python names are
snake_case renderings of the table's camelCase, the same convention
`ProviderResponse` already uses for `errorType` and `rawProviderPayload`.

**Ownership is a real constraint, not a comment.** The Tool Executor constructs
`ToolResponse` and never constructs a `ToolRequest`: a module that could
manufacture its own input could manufacture the work it claims to have done.
That separation is what makes "never fabricate success" checkable from outside.

**No writer exists for `ToolRequest` today.** Nothing in the implemented runtime
produces one — the Workflow Router emits only a `WorkflowTransitionDecision`,
`WorkflowState` carries no tool field, and the one provider adapter declares
`tool_calling_support=False`. The type is defined because the Tool Executor's
frozen signature cannot be written without it, not because a producer is
waiting. Recorded as TE-1 in docs/known-issues-runtime.md.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


class ToolErrorType(enum.StrEnum):
    """The normalised failure classes a tool execution reports.

    **Deliberately tool-scoped, and deliberately not `ProviderErrorType`.** That
    enum's own docstring scopes it to "the normalised failure classes every
    adapter maps its **vendor** errors onto" for LLM providers, per §9.9.
    Reusing it would widen a committed contract's meaning to cover a different
    kind of external system, and the two vocabularies have no reason to stay in
    step as either grows.

    Deliberately small, for the same reason §9.9's set is small: the runtime
    above must handle a tool failure without knowing which CRM produced it.
    Four members, each corresponding to something a caller can actually act on
    differently. A failure that fits none of them is `EXECUTION_FAILED` — that
    is what the general case is for, and growing this enum per integration
    would defeat the normalisation it exists to provide.
    """

    #: The tool ran and did not succeed. The general case.
    EXECUTION_FAILED = "execution_failed"
    #: The request itself was rejected as invalid or unsupported by the tool.
    INVALID_REQUEST = "invalid_request"
    #: No implementation is configured for the requested contract (§11.9).
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    #: The tool's own client reported a timeout. The framework defines none.
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """One normalised request to execute a tool-contract action.

    Written **solely by the Workflow State Manager**. The Tool Executor receives
    it and must never construct or mutate one.

    `tool_contract` names one of the five `core/tools/` contracts — the frozen
    set §11.11 fixes as current (`crm`, `calendar`, `email`,
    `consultation_form`, `integrations`). This type deliberately does **not**
    validate the name against that list: the canonical list lives in
    `CoreBundle.tool_contracts` and in the Validation Layer's transcription, and
    a third copy here would be the drift class ADR 0002 warns about. An
    unrecognised contract is simply one with no registered implementation, which
    the executor already answers honestly.

    **Never contains credentials** — stated in the frozen row and enforced by
    the field list: there is no field a credential could occupy. `parameters`
    carries the action's business inputs (names, emails, appointment times),
    which is PII by design and credential-free by contract (§11.3).
    """

    tool_contract: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    project_id: str = ""
    conversation_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class ToolResponse:
    """The normalised result of one tool execution. Tool Executor is sole writer.

    Immutable and created fresh per call, like every other per-call result in
    this runtime.

    **The invariants below exist to make §11.2's "never fabricate success" and
    §11.10's "a `ToolResponse` claiming success must correspond to an
    actually-confirmed external call" structural rather than aspirational.**
    They constrain only combinations the frozen clauses already forbid; no
    combination the specification permits is rejected here.

    **There is no diagnostic message field, and none was added.** The frozen row
    names exactly four fields, and a failure therefore carries its class and
    nothing else. Diagnostic detail deliberately does not travel in `data`
    either: a concrete tool's exception text is the same credential-bearing
    channel the provider layer already goes to lengths to redact, and §11.3
    forbids credentials crossing this boundary. Recorded as TE-4.
    """

    success: bool = False
    data: Mapping[str, Any] = field(default_factory=dict)
    error_type: ToolErrorType | None = None
    capability_unavailable: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))
        if self.success and self.error_type is not None:
            raise ValueError(
                "a successful ToolResponse cannot carry an error type; "
                "specification 11.2 forbids fabricating success"
            )
        if self.success and self.capability_unavailable:
            raise ValueError(
                "a ToolResponse cannot be both successful and capability "
                "unavailable; specification 11.9 makes the unavailable case a "
                "declined execution, not a completed one"
            )

    @property
    def failed(self) -> bool:
        """Mirrors `ProviderResponse.failed`: not successful is not a detail."""
        return not self.success
