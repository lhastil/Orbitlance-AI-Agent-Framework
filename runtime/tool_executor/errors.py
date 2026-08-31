"""Tool Executor failures.

There is exactly one, and its scarcity is the point.

`execute()` **never raises**. §11.5 makes `ToolResponse` this module's output and
§11.9 requires an unconfigured contract to return a result "rather than
crashing", so every runtime outcome — declined, failed, or succeeded — is a
`ToolResponse`. An exception escaping `execute()` would be a second, untyped
output channel that the frozen contract does not have.

What remains is registration, which happens while a process is being wired
together, before any conversation exists. That is an assembly error, and it
subclasses `ValueError` following the precedent `runtime.validation.registry`
set with `DuplicateRuleError` and `runtime.provider_registry` followed with
`DuplicateProviderError` — **labelled as precedent, not as specification.** §11
says nothing about registration at all.
"""

from __future__ import annotations


class DuplicateToolError(ValueError):
    """Two implementations claim the same tool contract.

    Registration **rejects rather than overwrites**, and the first registration
    survives intact. This is an implementation decision made for consistency
    with the two registries already in this repository, not a rule §11 states.

    The reason it is worth having: a silent overwrite would change which
    external system a project's traffic reaches — which CRM receives a patient
    record, which mailbox sends a confirmation — with nothing in the process
    reporting that it changed. Registration errors are cheap; a side effect
    delivered to the wrong system is not.
    """
