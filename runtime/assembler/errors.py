"""Prompt Assembler failure modes.

Each is a hard bug elsewhere in the runtime, surfaced loudly rather than
absorbed. The assembler has no soft-failure path: it either produces a correct
bundle or refuses to produce one.
"""

from __future__ import annotations


class AssemblerError(Exception):
    """Base for every Prompt Assembler failure."""


class PlaybookLeakError(AssemblerError):
    """Industry Playbook content reached an assembled section.

    Spec rule 10 requires this as *"a hard runtime assertion, not just a design
    intention"*. Reaching it means the Core Loader admitted playbook content
    into a `CoreBundle`, which its own spec calls a Core Loader defect.
    """


class UnknownWorkflowError(AssemblerError):
    """The active workflow does not exist in the `CoreBundle`.

    Defence in depth mirroring Workflow Router rule 10 — *"routing to an
    undefined workflow is a hard bug, caught by assertion"*. The assembler does
    not choose the workflow and will not quietly emit a bundle without the one
    it was told is active.
    """


class WorkflowNotEnabledError(AssemblerError):
    """The active workflow exists in Core but this project has not enabled it.

    Distinct from `UnknownWorkflowError`, and deliberately so: a workflow being
    present in `CoreBundle` says nothing about whether a project selected it.
    Core existence is the Workflow Router's assertion (rule 10); project scope is
    a different question, and the frozen specification assigns it to no module at
    all. The Prompt Assembler is the only built module holding both facts — the
    project's `enabled_workflows` and the active `WorkflowState` — in one call.

    Defence in depth, in the same shape as rule 9's degraded-bundle handling:
    the Runtime Engine is the primary gate once it exists, and this assertion
    stands behind it so a direct caller cannot bypass the invariant.

    Raised rather than quietly omitting the slot. Omitting would produce a bundle
    that looks complete while silently dropping the workflow the caller believed
    was active, which is the class of silent divergence this runtime refuses.
    """
