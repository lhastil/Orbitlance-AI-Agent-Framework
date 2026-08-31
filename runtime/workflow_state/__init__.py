"""Workflow State Manager — specification §7.

Persists `WorkflowState` per conversation and commits the Workflow Router's
transition decisions. A leaf module: it depends on nothing else in the runtime
and decides nothing about workflows.

    from runtime.workflow_state import WorkflowStateManager
    from runtime.models import WorkflowTransitionDecision

    workflows = WorkflowStateManager()
    workflows.get_state("conv-1")                    # active_workflow is None
    workflows.commit_transition(
        "conv-1", WorkflowTransitionDecision("discovery")
    )

See `manager` for the four ratified decisions and why a new conversation starts
with no active workflow.
"""

from runtime.models.workflow import WorkflowTransitionDecision
from runtime.workflow_state.errors import (
    InvalidTransitionError,
    WorkflowStateError,
    WorkflowStateStoreUnavailableError,
)
from runtime.workflow_state.manager import (
    NO_PREVIOUS_WORKFLOW,
    TRANSITION_ARROW,
    WorkflowStateManager,
)
from runtime.workflow_state.store import (
    InMemoryWorkflowStateStore,
    WorkflowStateStore,
)

__all__ = [
    "NO_PREVIOUS_WORKFLOW",
    "TRANSITION_ARROW",
    "InMemoryWorkflowStateStore",
    "InvalidTransitionError",
    "WorkflowStateError",
    "WorkflowStateManager",
    "WorkflowStateStore",
    "WorkflowStateStoreUnavailableError",
    "WorkflowTransitionDecision",
]
