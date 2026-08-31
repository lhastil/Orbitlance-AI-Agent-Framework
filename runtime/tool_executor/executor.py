"""Tool Executor — specification §11.

Executes the concrete action behind one tool call and normalises the result.
It never decides *when* a tool should be called (§11.3): it receives a
`ToolRequest` someone else wrote and answers it, once.

**No credentials, no environment, no SDK, no network in this module.** §11.3
confines credential handling to each concrete implementation, and this module
imports only `runtime.models`. Everything that talks to a third party lives
behind `ToolPort`.

---

## What this module does *not* do, and why each absence is deliberate

Every item here is a **ruled decision**, recorded so a reader is never left to
infer that §11 required it.

**No retries.** §11.2 and §11.9 defer to "the error-handling behavior already
documented in each tool contract" and to "policy". Those documents say, in
full: *"Retry only when appropriate"* (`crm.md`, `calendar.md`, `email.md`),
*"Retry when appropriate"* (`integrations.md`), and *"Retry according to
business rules"* (`consultation_form.md`). No count, no backoff, no ceiling, no
definition of "appropriate", and no artifact named "business rules" exists.

A retry policy invented here would not be a convenience — it would re-send a
customer's email and re-create a CRM record, violating the same contracts'
*"Avoid sending duplicate emails"* and *"Never create duplicate records
intentionally"*. **A side-effecting operation is never retried merely because
its failure looked transient.** The first failure is surfaced honestly, which is
what §11.2's "never fabricate success" and §11.9's "never optimistic success"
actually require. §11.12(c)'s retry scenario is therefore not implementable
today; it is recorded as TE-2 rather than faked.

**No timeout.** Nothing in the repository states one — no value, no default, no
source. `integrations.md` lists "Timeout Settings (optional)" among a tool's own
*inputs*, which places it with the implementation. A framework-wide default
invented here would set a latency policy on no authority, so an implementation
owns whatever its client needs and this module enforces nothing.

**No integrations parsing.** §11.2's literal path is "resolve the project's
configured concrete provider from `ResolvedContext.integrations`". That mapping
holds raw Markdown `ProjectDocument`s whose provider values are English
sentences, and interpreting them here is ruled **Invalid** twice over: ADR 0004
reserves parsing to the Project Loader, and known issue L-4 rejects both
re-implementing the Validation Layer's substring search and depending on that
layer. Availability is therefore determined by what a caller registered.
Recorded honestly as TE-3: the literal §11.2 path is not executable against the
current representation, and typed integration resolution remains a separately
authorised Loader change under L-4.

**No batching, no parallelism, no tool loop.** §11.6 declares one call taking
one request. §14.2's pipeline names "tool execution" as a single ordered stage
and contains no second generation pass, so a tool result has no path back to the
model on that turn. Recorded as TE-5 for Module 14 to settle.

**No auto-discovery, no locks.** Registration is explicit; §11 states no
atomicity requirement (contrast §7.10, the clause Module 7's locks exist to
satisfy), so none is claimed. Both are implementation decisions, described in
`register`.
"""

from __future__ import annotations

from runtime.models.resolved_context import ResolvedContext
from runtime.models.tool import ToolErrorType, ToolRequest, ToolResponse
from runtime.tool_executor.errors import DuplicateToolError
from runtime.tool_executor.ports import ToolPort


class ToolExecutor:
    """§11.6's single member, plus explicit registration.

    Registration semantics — per-instance, add-only, duplicate-rejecting, no
    unregistration, no thread-safety claim — are **implementation decisions
    taken for consistency with this repository's two existing registries**. §11
    specifies none of them. They are documented in `register` rather than left
    to be mistaken for contract.
    """

    __slots__ = ("_tools",)

    def __init__(self) -> None:
        self._tools: dict[str, ToolPort] = {}

    # -- registration (implementation decision, not §11) ----------------------
    def register(self, tool_contract: str, tool: ToolPort) -> ToolExecutor:
        """Bind one already-constructed implementation to one contract name.

        Explicit and caller-driven. Nothing is discovered: importing a concrete
        tool package to find implementations would make a vendor SDK a hard
        dependency of the framework and give it a de facto default integration,
        the two hazards `runtime/provider/adapters/__init__.py` already names.
        It would also reproduce the failure `runtime.validation.registry`
        describes — something that "silently stops running because a module was
        not imported".

        The implementation is passed already constructed. Building one here
        would mean this module held a credential-bearing client, which §11.3
        places inside the implementation instead.

        Returns `self`, so registrations chain. A duplicate contract is
        rejected and the original survives.
        """
        if not tool_contract.strip():
            raise ValueError("tool_contract must not be empty")
        existing = self._tools.get(tool_contract)
        if existing is not None:
            raise DuplicateToolError(
                f"tool contract {tool_contract!r} is already served by "
                f"{type(existing).__name__}; registration rejects rather than "
                "overwrites, so which external system a project reaches cannot "
                "change silently during process assembly."
            )
        self._tools[tool_contract] = tool
        return self

    def registered_contracts(self) -> frozenset[str]:
        """Every contract with a registered implementation."""
        return frozenset(self._tools)

    def is_available(self, tool_contract: str) -> bool:
        """Whether this contract has an implementation (§11.9's determination).

        Availability is *what was registered*, not what a project's
        `integrations/` document says — see this module's docstring and TE-3.
        """
        return tool_contract in self._tools

    # -- §11.6 ----------------------------------------------------------------
    def execute(
        self, tool_request: ToolRequest, resolved_context: ResolvedContext
    ) -> ToolResponse:
        """Execute one tool call and return a normalised result (§11.6).

        Exactly one attempt. **Never raises** — §11.5 makes `ToolResponse` this
        module's only output, and §11.9 requires the unconfigured case to return
        a result "rather than crashing".

        Three outcomes, and only three:

        * **No implementation registered** → `capability_unavailable=True`,
          `success=False`. §11.9 names this outcome directly. An unrecognised
          contract name reaches the same answer, because a contract nothing
          serves is unavailable however the name arose.
        * **The implementation raised** → a failed response carrying
          `EXECUTION_FAILED` and nothing else. §11.2 assigns normalisation here,
          and no detail from the exception crosses the boundary: a vendor
          exception's message and request URL are a known credential-bearing
          channel, and §11.3 forbids credentials travelling in a `ToolResponse`.
        * **The implementation returned** → its result is passed through
          **unchanged**.

        That last point is the load-bearing one. This module never edits a
        result: it does not add a success it was not given, does not clear an
        error, and does not populate `data`. §11.10 makes a success claim a
        statement about a confirmed external call, and only the implementation
        knows what its provider confirmed — so the claim is the
        implementation's to make and this module's to carry faithfully. The one
        thing it will not do is manufacture one.
        """
        tool = self._tools.get(tool_request.tool_contract)
        if tool is None:
            return ToolResponse(
                success=False,
                capability_unavailable=True,
                error_type=ToolErrorType.CAPABILITY_UNAVAILABLE,
            )

        try:
            return tool.execute(tool_request, resolved_context)
        except Exception:  # noqa: BLE001 - §11.2 normalises; §11.3 keeps detail out
            # Deliberately not `from exc`, and deliberately carrying nothing
            # from it: this returns rather than raises, so no traceback is
            # built, and the vendor detail that could contain a credential
            # never reaches a caller or a log through this object.
            return ToolResponse(
                success=False, error_type=ToolErrorType.EXECUTION_FAILED
            )
