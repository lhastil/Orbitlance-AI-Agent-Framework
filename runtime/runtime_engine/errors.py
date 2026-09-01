"""Runtime Engine construction failures.

Two classes, both construction-time: a project that has not passed validation,
and a deployment with no durable audit database configured.

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


class AuditStoreNotConfiguredError(ValueError):
    """No durable audit database was configured for the deployment.

    §15.2 makes persisting audit events a **responsibility**, not an optional
    extra, so the production path depends on a durable store being reachable.
    `activate` therefore reads `ORBITLANCE_AUDIT_DB` and refuses to build an
    engine when it is absent: a runtime that serves traffic while silently
    keeping no durable audit trail is the Compliance risk §15.9 names, and
    failing at deployment time is the honest place to surface it.

    **Absence only.** If the variable is set but the path cannot be opened,
    created or initialised, the adapter's own `SqliteAuditLogStoreError`
    propagates unchanged — that is a different fault, it already carries the
    path and the underlying reason, and wrapping it here would hide both.

    **No default path is invented.** Choosing where a deployment's audit records
    live is a deployment decision; guessing one would put durable customer-linked
    records somewhere nobody chose.

    A `ValueError` rather than a member of any module's error family, matching
    `ProjectNotActivatedError` below: both are assembly-time misconfigurations
    raised before any conversation exists, and neither is a per-turn outcome.
    """


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
