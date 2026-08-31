"""Provider Registry — specification §10.

Public surface:

    ProviderRegistry            register adapters; resolve and route (§10.6)
    FAILOVER_ERROR_TYPES        the normalised classes that trigger failover
    AllProvidersFailedError     §10.9's terminal outcome
    ProviderNotRegisteredError  the declared provider is not registered
    ProviderModelMismatchError  registered adapter is bound to another model
    DuplicateProviderError      registration rejects, never overwrites
    UnidentifiableProviderError a candidate exposes no model binding

There is deliberately **no adapter import and no provider SDK here**, and no
default provider: an adapter reaches this module only because a caller
constructed it and registered it.

`ProviderRequest` is **not** implemented in this milestone. The frozen Data
Models table names the Provider Registry its sole writer, so its ownership is
reserved and cannot be claimed elsewhere; no clause requires it to be
constructed, and nothing reads it until Observability (§15) defines what may be
logged. Recorded as PR-3 in `docs/known-issues-runtime.md`.
"""

from runtime.provider_registry.errors import (
    AllProvidersFailedError,
    DuplicateProviderError,
    ProviderModelMismatchError,
    ProviderNotRegisteredError,
    UnidentifiableProviderError,
)
from runtime.provider_registry.registry import FAILOVER_ERROR_TYPES, ProviderRegistry

__all__ = [
    "FAILOVER_ERROR_TYPES",
    "AllProvidersFailedError",
    "DuplicateProviderError",
    "ProviderModelMismatchError",
    "ProviderNotRegisteredError",
    "ProviderRegistry",
    "UnidentifiableProviderError",
]
