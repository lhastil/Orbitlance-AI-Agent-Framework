"""Concrete `AuditLogStore` adapters.

Each adapter is one module owning whatever its backing system needs. This
subtree is the only place in `runtime/observability/` where a storage
technology, a serialization format or filesystem access may appear — the core
(`logger.py`, `store.py`, `runtime/models/audit.py`) stays storage-agnostic and
a structural test enforces that.

**This package deliberately imports none of its modules.** Doing so would make
every adapter's backing system a hard import of the observability layer, and
would give the framework a de facto default audit store. There is no default:
`AuditLogger` still constructs an `InMemoryAuditLogStore` when given none, and
the production composition root still wires that one. An adapter is selected by
explicit import and explicit construction, and the existence of one activates it
for nothing.

The same pattern, and the same reasoning, as `runtime/provider/adapters/`.
"""
