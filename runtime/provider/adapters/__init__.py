"""Concrete provider adapters.

Empty by design. The framework selects no default provider, and no adapter is
required for the provider-independent foundation to be complete and testable.

Each future adapter lives in its own subpackage, owns its provider SDK, and must
pass `runtime.provider.conformance` before registration (specification §9.10).
An adapter is the only place in the repository where a vendor name or SDK import
may appear.
"""
