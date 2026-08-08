"""Prompt Assembler failure modes.

Both are hard bugs elsewhere in the runtime, surfaced loudly rather than
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
