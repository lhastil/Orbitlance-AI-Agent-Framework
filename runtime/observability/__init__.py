"""Observability / Audit Logger — specification §15.

Public surface:

    AuditLog                §15.6's interface, as other modules depend on it
    AuditLogger             the implementation: stamps identity and time, appends
    AuditLogStore           the seam §15.8's durable store plugs into
    InMemoryAuditLogStore   append-only, process-lifetime, **not durable**

`AuditEvent` and `AuditFilters` live in `runtime.models` alongside every other
data model.

**A leaf module** (§15.7): it imports `runtime.models` and the standard library,
and nothing else in the runtime. Every other module depends on it,
one-directionally.

**What this milestone does not deliver**, each recorded rather than implied:

* **durability** — the only store is in-memory, so §15.8 is partially met (OB-1);
* **duplicate-id rejection** — ids are generated per call, so §15.12(d)'s case
  cannot arise from outside this module and no fake check was written (OB-2);
* **an alert on audit-gap** — §15.9 requires one and the repository has no
  metrics seam to raise it through (OB-3);
* **retention, authorization, pagination** — undefined by §15, so undefined here.
"""

from runtime.models.audit import AuditEvent, AuditFilters
from runtime.observability.logger import AuditLog, AuditLogger
from runtime.observability.store import AuditLogStore, InMemoryAuditLogStore

__all__ = [
    "AuditEvent",
    "AuditFilters",
    "AuditLog",
    "AuditLogStore",
    "AuditLogger",
    "InMemoryAuditLogStore",
]
