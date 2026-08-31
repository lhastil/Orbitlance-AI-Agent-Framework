"""Workflow Router — specification §6.

Decides which workflow is active for a turn and returns a candidate
`WorkflowTransitionDecision` for the Workflow State Manager to commit. A leaf:
it persists nothing, calls no provider, and never imports Module 7.

    from runtime.workflow_router import WorkflowRouter

    decision = WorkflowRouter().route(state, "hello", core_bundle)
    workflows.commit_transition("conv-1", decision)   # Module 7 commits it

See `router` for what this module deterministically can and cannot decide, and
why `collected_data` is always empty.
"""

from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_router.errors import RouterError, UndefinedWorkflowError
from runtime.workflow_router.router import (
    FIRST_TURN_WORKFLOW,
    WORKFLOW_SUFFIX,
    WorkflowRouter,
)

__all__ = [
    "FIRST_TURN_WORKFLOW",
    "WORKFLOW_SUFFIX",
    "RouterError",
    "UndefinedWorkflowError",
    "WorkflowRouter",
    "WorkflowTransitionDecision",
]
