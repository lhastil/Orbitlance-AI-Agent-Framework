"""Tool Executor — specification §11.

Public surface:

    ToolExecutor        register implementations; execute one call (§11.6)
    ToolPort            what a concrete implementation provides
    DuplicateToolError  registration rejects, never overwrites

There is deliberately **no concrete tool implementation and no vendor SDK** in
this package, and no default integration: an implementation reaches this module
only because a caller constructed it and registered it. Credentials, network
access and any timeout live behind `ToolPort`, per §11.3.

`ToolRequest`, `ToolResponse` and `ToolErrorType` live in `runtime.models.tool`
alongside every other entry in the frozen data-model table.

**What this module deliberately does not do** — each a ruled decision, not a
reading of §11: no retries (the contracts define no policy; a retried
side effect duplicates it), no timeout, no parsing of `integrations/`
documents, no batching or parallelism, no tool loop, no auto-discovery, no
thread-safety guarantee. See `executor` for the reasoning and
`docs/known-issues-runtime.md` TE-1 through TE-6 for what remains open.
"""

from runtime.tool_executor.errors import DuplicateToolError
from runtime.tool_executor.executor import ToolExecutor
from runtime.tool_executor.ports import ToolPort

__all__ = [
    "DuplicateToolError",
    "ToolExecutor",
    "ToolPort",
]
