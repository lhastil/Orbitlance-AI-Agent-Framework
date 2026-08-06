"""Resolver — Runtime Module 3.

Implements module 3 of docs/runtime-specification.md:

    resolve(coreBundle, projectContext) -> ResolvedContext

Combines a `CoreBundle` with a raw `ProjectContext` per the Resolution Order in
`docs/project-configuration.md`, producing the `ResolvedContext` that every
module downstream consumes.

**A pure function with no process control.** The spec is explicit that a
Resolver with side effects would be a design error: it never mutates its
inputs, never calls a provider, never touches the filesystem, and never decides
whether a project activates. Missing Knowledge sets `knowledge_incomplete`; the
Runtime Engine owns the gate that reads it.

**Only enough checking to decide fallback.** Presence and emptiness are
fallback inputs. Whether a provider is a placeholder, whether a playbook exists
in Core, whether a workflow name is legitimate — all of that is the Validation
Layer's, and this module deliberately reports rather than corrects.

Dependency direction is one-way and shallow: this module imports
`runtime.models` only. It does not import the Project Loader, the Core Loader
or the Validation Layer, and none of them imports it.
"""

from __future__ import annotations

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectContext
from runtime.models.resolved_context import ResolvedContext
from runtime.resolver import extension_points as points


class Resolver:
    """Combines Core and one project into a `ResolvedContext`.

    Stateless and collaborator-free by design — the spec gives this module no
    external dependencies. Two `Resolver` instances are interchangeable, and
    resolving the same inputs twice always produces an equal result.
    """

    __slots__ = ()

    def resolve(self, core: CoreBundle, project: ProjectContext) -> ResolvedContext:
        """Apply the Resolution Order, per extension point.

        The four rules are independent: none reads another's output, so their
        evaluation order affects only the order of `fallback_log` entries, which
        is fixed here to keep output deterministic.
        """
        knowledge, incomplete, knowledge_decisions = points.resolve_knowledge(
            core, project
        )
        branding, branding_decisions = points.resolve_branding(core, project)
        integrations, degraded, integration_decisions = points.resolve_integrations(
            core, project
        )
        config, config_decisions = points.resolve_config(core, project)

        return ResolvedContext(
            project_id=project.project_id,
            knowledge=knowledge,
            branding=branding,
            integrations=integrations,
            config=config,
            knowledge_incomplete=incomplete,
            degraded_capabilities=degraded,
            fallback_log=(
                *knowledge_decisions,
                *branding_decisions,
                *integration_decisions,
                *config_decisions,
            ),
        )
