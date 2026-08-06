"""Runtime Module 3 — Resolver.

Public surface:

    Resolver().resolve(core_bundle, project_context) -> ResolvedContext

The extension-point rules in `extension_points` are exported so the Resolution
Order can be tested and read rule by rule, but `Resolver` is the module's
interface. Nothing downstream should call the individual rules.
"""

from runtime.models.resolved_context import (
    ExtensionPointName,
    ResolutionAction,
    ResolutionDecision,
    ResolvedConfig,
    ResolvedContext,
)
from runtime.resolver.resolver import Resolver

__all__ = [
    "ExtensionPointName",
    "ResolutionAction",
    "ResolutionDecision",
    "ResolvedConfig",
    "ResolvedContext",
    "Resolver",
]
