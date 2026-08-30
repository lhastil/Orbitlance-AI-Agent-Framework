"""Concrete provider adapters.

Each adapter lives in its own subpackage, owns its provider SDK as an optional
extra, and must pass `runtime.provider.conformance` before registration
(specification §9.10). An adapter subtree is the only place in the repository
where a vendor name or SDK import may appear.

Currently present: `gemini/` (google / gemini-3.6-flash), the first concrete
adapter.

**This package deliberately imports none of its subpackages.** Doing so would
make every provider SDK a hard import of the provider layer, and would give the
framework a de facto default. There is no default provider: an adapter is
selected by construction, and the existence of one activates it for nothing.
"""
