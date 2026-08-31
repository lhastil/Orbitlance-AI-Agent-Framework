"""`ToolPort` — the contract a concrete tool implementation satisfies.

**Framework-introduced, not specified.** §11 names no tool interface anywhere.
It says the Tool Executor must "resolve the project's configured concrete
provider… execute it", which presupposes something executable without ever
describing it. This Protocol is the smallest shape that makes §11.6's frozen
signature expressible, and it is labelled as an implementation decision rather
than presented as a discovered requirement.

It is deliberately **not** modelled on `ProviderInterface`. That contract exists
for LLM providers and carries capability metadata, a context window and a
tokenizer — none of which a CRM or a calendar has. Borrowing its shape would
import a vocabulary that does not apply.

One method. No capability query, no registration hook, no lifecycle callbacks,
no conformance suite: nothing in §11 or its test scenarios needs them, and each
would be surface invented on no authority.

---

## What an implementation owns, and what it must never do

Everything provider-specific lives behind this Protocol, exactly as §11.3
requires:

* **Credentials.** *"Credential handling stays fully internal to each concrete
  implementation, never passed through `ToolRequest`/`ToolResponse`."* An
  implementation reads its own secrets, from wherever its deployment supplies
  them. The executor never sees them, never holds them, and never logs them.
* **Its SDK and its network calls.** §11.8 grants the Tool Executor's world
  external dependencies — the third-party APIs behind the five contracts. They
  live here, not in the executor.
* **Its own timeout,** if its client needs one. The framework defines none, and
  the executor enforces none — no clause anywhere states a value or a default.

## `success=True` is an assertion, not a hope

§11.10: *"A `ToolResponse` claiming success must correspond to an
actually-confirmed external call."* The executor cannot verify that from
outside — only the implementation knows what its provider confirmed. So the
obligation is placed here, explicitly:

> **Returning `success=True` asserts that the external operation was actually
> confirmed, to the fullest extent this implementation is able to confirm it.
> An implementation that cannot honestly establish that must not return
> `success=True`.**

The executor never upgrades a result: it does not turn a failure into a success,
and it never invents a success of its own. That is the half of §11.10 it can
guarantee, and it does.

## Retries are not performed, here or above

The executor performs **none** — a ruled decision recorded in the executor
module and in TE-2. An implementation that retries internally is making a claim
about its own operation's idempotency that only it can make; nothing in this
framework instructs it to, and nothing above it will retry on its behalf.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.resolved_context import ResolvedContext
from runtime.models.tool import ToolRequest, ToolResponse


@runtime_checkable
class ToolPort(Protocol):
    """What a concrete implementation of one `core/tools/` contract provides."""

    def execute(
        self, tool_request: ToolRequest, resolved_context: ResolvedContext
    ) -> ToolResponse:
        """Perform the action and return a normalised result.

        The two parameters mirror §11.6's frozen signature rather than narrowing
        it: the executor is given both and passes both through unchanged, so an
        implementation that legitimately needs project context — a project's
        branding for an email, its knowledge for a form — has it, and the
        executor does not have to decide on its behalf what is relevant.

        Must not mutate either argument; both are immutable by construction.

        May raise. The executor normalises any exception into a failed
        `ToolResponse` (§11.2's "normalize the result") rather than letting it
        escape, and deliberately carries no detail from it across the boundary,
        because a vendor exception's message is a known credential-bearing
        channel. Returning a failed `ToolResponse` is preferable to raising:
        it is the only way to say *which* normalised class failed.
        """
        ...
