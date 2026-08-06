"""ResolvedContext — the fully-resolved Core+Project combination.

Implements the `ResolvedContext` data model from docs/runtime-specification.md:
project_id, resolvedKnowledge, resolvedBranding, resolvedIntegrations,
resolvedConfig (incl. llmProvider and operatingConstraints),
knowledge_incomplete, degraded_capabilities, fallback_log.

Ownership: the Resolver is the sole writer. It is read by the Prompt Assembler,
Token Budget Manager, Guardrail Engine, Tool Executor and Provider Registry —
none of which ever sees a raw `ProjectContext`. That is why this type, not
`ProjectContext`, is the runtime's real downstream contract.

Everything here is immutable. The Resolver is specified as a pure function, so
nothing it returns may be mutated by a consumer.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from runtime.models.project_config import LlmProviderSelection
from runtime.models.project_context import ProjectDocument


class ExtensionPointName(str, enum.Enum):
    """The four documented extension points, and only those.

    Source: docs/project-configuration.md. A fifth value would be an
    architecture change, not a code change.
    """

    KNOWLEDGE = "knowledge"
    BRANDING = "branding"
    INTEGRATIONS = "integrations"
    CONFIG = "config"


class ResolutionAction(str, enum.Enum):
    """What the Resolver decided for one extension point.

    These mirror the Resolution Order table's four outcomes plus the
    project-supplied case. There is deliberately no generic "other".
    """

    #: The project supplied this resource; its version was used.
    PROJECT_VERSION_USED = "project_version_used"
    #: The project did not supply it; a documented Core default was applied.
    CORE_DEFAULT_APPLIED = "core_default_applied"
    #: No Core default exists; the affected capability is disabled.
    CAPABILITY_DEGRADED = "capability_degraded"
    #: No safe default exists; the project must not activate.
    ACTIVATION_BLOCKED = "activation_blocked"
    #: A declared value matched nothing in Core. Carried, never judged.
    DECLARATION_UNRESOLVED = "declaration_unresolved"


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    """One recorded decision.

    Spec rule 10 requires every fallback decision to appear in `fallback_log`;
    spec responsibility 2 requires recording *which choice was made*. This type
    satisfies both, so the log is a complete audit of the Resolution Order
    rather than only its failures.
    """

    extension_point: ExtensionPointName
    action: ResolutionAction
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ValueError("A resolution decision must explain itself.")


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """The project's configuration after documented defaults are applied.

    `enabled_workflows` holds canonical Core workflow names (the stems of
    `core/workflows/`), never the human labels config.md used. Downstream
    modules index `CoreBundle.workflows` with these.
    """

    active_playbooks: tuple[str, ...] = ()
    llm_provider: LlmProviderSelection = field(default_factory=LlmProviderSelection)
    enabled_workflows: tuple[str, ...] = ()
    operating_constraints: str = ""

    @property
    def has_playbook(self) -> bool:
        return bool(self.active_playbooks)


@dataclass(frozen=True, slots=True)
class ResolvedContext:
    """Core and one project, resolved. The contract for everything downstream."""

    project_id: str
    knowledge: Mapping[str, ProjectDocument] = field(default_factory=dict)
    branding: Mapping[str, ProjectDocument] = field(default_factory=dict)
    integrations: Mapping[str, ProjectDocument] = field(default_factory=dict)
    config: ResolvedConfig = field(default_factory=ResolvedConfig)
    knowledge_incomplete: bool = True
    degraded_capabilities: frozenset[str] = field(default_factory=frozenset)
    fallback_log: tuple[ResolutionDecision, ...] = ()

    def __post_init__(self) -> None:
        for attr in ("knowledge", "branding", "integrations"):
            object.__setattr__(
                self, attr, MappingProxyType(dict(getattr(self, attr)))
            )
        object.__setattr__(
            self, "degraded_capabilities", frozenset(self.degraded_capabilities)
        )

    def is_capability_available(self, capability: str) -> bool:
        """Whether a Core tool capability may be offered for this project."""
        return capability not in self.degraded_capabilities

    def decisions_for(
        self, extension_point: ExtensionPointName
    ) -> tuple[ResolutionDecision, ...]:
        return tuple(d for d in self.fallback_log if d.extension_point == extension_point)
