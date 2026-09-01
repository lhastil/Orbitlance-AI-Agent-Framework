"""Runtime Engine construction failures.

Exactly one class, and only construction-time.

**No repository-wide exception base is introduced.** The runtime holds 51
exception classes across twelve unrelated hierarchies, and unifying them would
mean editing twelve committed modules. §14.9 does not require a common base — it
requires that no lower-level exception reaches the user as a crash, which the
engine achieves by containing failures at each stage boundary and returning a
degraded `RuntimeResponse`.

Nothing here is raised during `handle_request`. Once an engine exists, every
per-turn outcome is a `RuntimeResponse`.
"""

from __future__ import annotations


class ProjectNotActivatedError(ValueError):
    """The engine was given a project that has not passed validation (§14.10).

    §14.10 makes a passed `ValidationResult` *"a hard precondition"* for
    accepting any request, and §14.2 places that decision *"at
    project-activation/deploy time — not re-validated on every single message"*.
    Both are satisfied by refusing to construct: an engine that exists is an
    engine whose project was validated, so `handle_request` never has to ask.

    A `ValueError` rather than a member of any module's error family. It is an
    assembly-time misconfiguration — the same category as
    `DuplicateProviderError` and `DuplicateToolError`, both of which follow the
    precedent `runtime.validation.registry` set with `DuplicateRuleError`.
    Labelled as precedent, not as specification: §14 states no error type.
    """
