"""Workflow Router failures.

§6.10 is unambiguous: a decision "must always name a workflow that exists in
`CoreBundle` — routing to an undefined workflow is a hard bug, caught by
assertion." So the Router refuses to return an invalid decision rather than
handing one downstream, where Module 7 would persist it unquestioned (§7.3) and
the Prompt Assembler would raise on a bundle it can no longer build.

Reaching either of these means Core is incomplete or the Router was asked to
continue a workflow that no longer exists — both defects elsewhere, surfaced
here rather than absorbed.
"""

from __future__ import annotations


class RouterError(Exception):
    """Base for every Workflow Router failure."""


class UndefinedWorkflowError(RouterError):
    """The workflow the Router would name does not exist in `CoreBundle`.

    §6.10's assertion. Two ways to arrive here, and both are bugs upstream: the
    ratified first-turn workflow is missing from Core, or a conversation is
    carrying an `active_workflow` that Core no longer defines.
    """

    def __init__(self, workflow: str, available: tuple[str, ...], reason: str) -> None:
        super().__init__(
            f"Cannot route to workflow {workflow!r}: {reason}. Available in "
            f"core/workflows/: {', '.join(available) if available else '(none)'}. "
            "Specification 6.10 requires every decision to name a workflow that "
            "exists in the CoreBundle."
        )
        self.workflow = workflow
        self.available = available
        self.reason = reason
