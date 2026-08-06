"""The Resolution Order, implemented — one function per extension point.

Source of truth: `docs/project-configuration.md`, "Missing-resource behavior,
per extension point". That table is deliberately **not uniform**, and the
framework states plainly that applying one rule to all four would be unsafe.
Keeping one function per extension point makes that non-uniformity structural
rather than a chain of conditionals a future contributor might "simplify".

| Extension point | If missing | Implemented in |
|---|---|---|
| Branding | Core's neutral default voice | `resolve_branding` |
| Config | Documented defaults (no playbook; all workflows) | `resolve_config` |
| Integrations | Degrade the affected capability | `resolve_integrations` |
| Knowledge | Fail loudly at activation | `resolve_knowledge` |

**Every set these rules need is derived from `CoreBundle`, never transcribed.**
Required knowledge comes from `core/knowledge/`, the workflow vocabulary from
`core/workflows/`, and the capability set from `core/tools/`. That is why this
module imports no framework constants and does not repeat V-5's transcription
problem — and why it never imports the Validation Layer, which would invert the
frozen dependency direction.
"""

from __future__ import annotations

from collections.abc import Mapping

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ExtensionPoint, ProjectContext, ProjectDocument
from runtime.models.resolved_context import (
    ExtensionPointName,
    ResolutionAction,
    ResolutionDecision,
    ResolvedConfig,
)

Decisions = tuple[ResolutionDecision, ...]


def _stem(name: str) -> str:
    """Canonical comparison form for a Core document name or a config label.

    `discovery.md` -> `discovery`; `CRM Sync` -> `crm_sync`; `Follow-up` ->
    `follow_up`. Exact matching only afterwards — no prefix or fuzzy matching
    (the V-4 defect class).

    Deliberately independent of `core_bundle.playbook_key`, which normalises a
    *path* out of config.md. This normalises a label; the shared `.md` handling
    is incidental, not shared knowledge.
    """
    text = name.strip().casefold()
    if text.endswith(".md"):
        text = text[:-3]
    return text.replace("-", "_").replace(" ", "_")


def _live_documents(point: ExtensionPoint) -> Mapping[str, ProjectDocument]:
    """Documents that actually carry content. Presence, not content analysis."""
    return {
        name: doc
        for name, doc in point.documents.items()
        if doc.exists and not doc.is_empty
    }


# --- Knowledge: fail loudly ------------------------------------------------
def resolve_knowledge(
    core: CoreBundle, project: ProjectContext
) -> tuple[Mapping[str, ProjectDocument], bool, Decisions]:
    """Knowledge has no Core fallback; a gap blocks activation.

    Returns `(documents, knowledge_incomplete, decisions)`.

    The required set is every contract in `core/knowledge/`. If Core declares
    none, completeness is **unknowable**, and the only safe answer is
    incomplete — an empty CoreBundle means the Core Loader failed, and reporting
    "complete" there would be the fail-open defect V-1 was raised for.
    """
    required = tuple(sorted(_stem(name) for name in core.knowledge_contracts))
    documents = _live_documents(project.knowledge)
    supplied = {_stem(name) for name in documents}

    if not required:
        return (
            documents,
            True,
            (
                ResolutionDecision(
                    ExtensionPointName.KNOWLEDGE,
                    ResolutionAction.ACTIVATION_BLOCKED,
                    "Core declares no knowledge contracts, so project knowledge "
                    "completeness cannot be determined. Failing closed.",
                ),
            ),
        )

    missing = tuple(name for name in required if name not in supplied)
    if missing:
        return (
            documents,
            True,
            (
                ResolutionDecision(
                    ExtensionPointName.KNOWLEDGE,
                    ResolutionAction.ACTIVATION_BLOCKED,
                    "Knowledge is incomplete; no content was substituted. Missing "
                    f"or empty: {', '.join(missing)}.",
                ),
            ),
        )

    return (
        documents,
        False,
        (
            ResolutionDecision(
                ExtensionPointName.KNOWLEDGE,
                ResolutionAction.PROJECT_VERSION_USED,
                f"All {len(required)} knowledge contracts are supplied by the project.",
            ),
        ),
    )


# --- Branding: fall back to Core's neutral default voice --------------------
def resolve_branding(
    core: CoreBundle, project: ProjectContext
) -> tuple[Mapping[str, ProjectDocument], Decisions]:
    """Branding is an overlay; without it the agent is under-styled, not wrong.

    When absent the overlay resolves **empty**, because Core Personality — which
    the frozen table names as the reason this fallback is safe — already occupies
    its own slot earlier in the Prompt Assembler's order. Copying it into the
    branding slot would emit the same text twice in one prompt.
    """
    documents = _live_documents(project.branding)
    if documents:
        return documents, (
            ResolutionDecision(
                ExtensionPointName.BRANDING,
                ResolutionAction.PROJECT_VERSION_USED,
                f"Project supplied {len(documents)} branding document(s).",
            ),
        )

    personality = "01_core_personality.md"
    detail = (
        "No project branding; falling back to Core's neutral default voice. The "
        "overlay resolves empty because Core Personality already supplies that "
        "voice in its own assembly slot."
    )
    if personality not in core.prompts:
        detail += " Warning: Core Personality is absent from this CoreBundle."
    return {}, (
        ResolutionDecision(
            ExtensionPointName.BRANDING, ResolutionAction.CORE_DEFAULT_APPLIED, detail
        ),
    )


# --- Integrations: degrade the affected capability --------------------------
def resolve_integrations(
    core: CoreBundle, project: ProjectContext
) -> tuple[Mapping[str, ProjectDocument], frozenset[str], Decisions]:
    """There is no Core version of a client's CRM, so missing means degraded.

    The capability set is derived from `core/tools/`. When the project supplies
    no integrations, **every** Core capability degrades — the per-tool
    capability-disabled state the spec's test scenario (c) names.

    When the project *does* supply integrations, this returns no degradation.
    Deciding which individual tool has a configured provider is explicitly the
    Tool Executor's responsibility ("resolve the project's configured concrete
    provider from `ResolvedContext.integrations`"), and claiming it here would
    require the Resolver to interpret document text — which ADR 0004 reserves to
    the Project Loader. See known issue L-4.
    """
    capabilities = frozenset(_stem(name) for name in core.tool_contracts)
    documents = _live_documents(project.integrations)

    if documents:
        return documents, frozenset(), (
            ResolutionDecision(
                ExtensionPointName.INTEGRATIONS,
                ResolutionAction.PROJECT_VERSION_USED,
                f"Project supplied {len(documents)} integrations document(s); "
                "per-tool provider resolution belongs to the Tool Executor.",
            ),
        )

    if not capabilities:
        return {}, frozenset(), (
            ResolutionDecision(
                ExtensionPointName.INTEGRATIONS,
                ResolutionAction.CORE_DEFAULT_APPLIED,
                "Core declares no tool contracts, so there is no capability to "
                "degrade.",
            ),
        )

    return {}, capabilities, (
        ResolutionDecision(
            ExtensionPointName.INTEGRATIONS,
            ResolutionAction.CAPABILITY_DEGRADED,
            "No project integrations; every Core capability is disabled and must "
            f"be declined honestly: {', '.join(sorted(capabilities))}.",
        ),
    )


# --- Config: fall back to documented defaults -------------------------------
def resolve_config(
    core: CoreBundle, project: ProjectContext
) -> tuple[ResolvedConfig, Decisions]:
    """Config selects Core resources; absent selections have documented defaults.

    The documented defaults are exactly two: *no playbook selected* and *all
    workflows enabled*. "All workflows" is derived from `core/workflows/`, which
    `core/templates/config.md` names as the authority ("List which workflows
    from `core/workflows/` are active for this project").

    Values are carried through verbatim. A placeholder provider or an unknown
    workflow is reported, never corrected — judging those is the Validation
    Layer's job, exactly as it is the Project Loader's non-responsibility.
    """
    all_workflows = tuple(sorted(_stem(name) for name in core.workflows))
    data = project.config_data
    decisions: list[ResolutionDecision] = []

    if not project.config.exists:
        decisions.append(
            ResolutionDecision(
                ExtensionPointName.CONFIG,
                ResolutionAction.CORE_DEFAULT_APPLIED,
                "No config.md; applying documented defaults — no playbook "
                f"selected, all {len(all_workflows)} workflows enabled.",
            )
        )
        return ResolvedConfig(enabled_workflows=all_workflows), tuple(decisions)

    decisions.append(
        ResolutionDecision(
            ExtensionPointName.CONFIG,
            ResolutionAction.PROJECT_VERSION_USED,
            "Project supplied config.md; per-selection defaults fill any gap.",
        )
    )

    if not data.active_playbooks:
        decisions.append(
            ResolutionDecision(
                ExtensionPointName.CONFIG,
                ResolutionAction.CORE_DEFAULT_APPLIED,
                "No industry playbook selected — the documented default. "
                "Playbooks are reference-only and never load at runtime.",
            )
        )

    enabled, unresolved = _resolve_workflows(data.enabled_workflows, all_workflows)
    for label in unresolved:
        decisions.append(
            ResolutionDecision(
                ExtensionPointName.CONFIG,
                ResolutionAction.DECLARATION_UNRESOLVED,
                f"config.md enables {label!r}, which matches no workflow in "
                "core/workflows/. Carried unresolved; judging it belongs to the "
                "Validation Layer.",
            )
        )

    if not enabled and not unresolved:
        enabled = all_workflows
        decisions.append(
            ResolutionDecision(
                ExtensionPointName.CONFIG,
                ResolutionAction.CORE_DEFAULT_APPLIED,
                f"No workflows selected; enabling all {len(all_workflows)} — the "
                "documented default.",
            )
        )

    return (
        ResolvedConfig(
            active_playbooks=data.active_playbooks,
            llm_provider=data.llm_provider,
            enabled_workflows=enabled,
            operating_constraints=data.operating_constraints,
        ),
        tuple(decisions),
    )


def _resolve_workflows(
    declared: tuple[str, ...], available: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Map declared labels onto canonical Core workflow names.

    Exact match on the normalised form only. Every spelling
    `core/templates/config.md` sanctions — "CRM Sync", "Follow-up", "Voice
    Agent" — normalises onto a `core/workflows/` stem, so no alias table is
    needed and none is duplicated from the Validation Layer.
    """
    known = set(available)
    matched: list[str] = []
    unresolved: list[str] = []
    for label in declared:
        key = _stem(label)
        if key in known:
            if key not in matched:
                matched.append(key)
        else:
            unresolved.append(label)
    return tuple(sorted(matched)), tuple(unresolved)
