"""Cross-module vocabulary alignment (R3-1 regression).

The Validation Layer and the Resolver both decide what a declared workflow
label means, and they reach that decision by different routes:

  * Validation resolves against `framework_spec.WORKFLOW_ALIASES` — a table
    *transcribed* from `core/templates/config.md`.
  * The Resolver derives the vocabulary from `core/workflows/` via `CoreBundle`,
    transcribing nothing.

Two routes to one answer is exactly the situation where drift goes unnoticed:
Validation once accepted three spellings the Resolver dropped, so a project
could pass validation and then silently lose a workflow. These tests fail if
the two ever disagree again.

The frozen template is the authority for both.
"""

from __future__ import annotations

import pytest

from runtime.resolver.extension_points import _resolve_workflows
from runtime.validation import framework_spec as spec
from runtime.validation.rules.config import ConfigWorkflowsRule

#: Source: core/templates/config.md — "The six available workflows are:
#: Discovery, Recommendation, Consultation, CRM Sync, Follow-up, Voice Agent."
TEMPLATE_SPELLINGS: tuple[tuple[str, str], ...] = (
    ("Discovery", "discovery"),
    ("Recommendation", "recommendation"),
    ("Consultation", "consultation"),
    ("CRM Sync", "crm_sync"),
    ("Follow-up", "follow_up"),
    ("Voice Agent", "voice_agent"),
)

#: Removed by the R3-1 fix. The template sanctions none of these.
WITHDRAWN_SPELLINGS: tuple[str, ...] = (
    "Consultation Request",
    "CRM Synchronization",
    "CRM Synchronisation",
)


def validation_resolves(label: str) -> str | None:
    return ConfigWorkflowsRule._resolve(label)


def resolver_resolves(label: str) -> str | None:
    matched, _ = _resolve_workflows((label,), spec.CANONICAL_WORKFLOWS)
    return matched[0] if matched else None


@pytest.mark.parametrize(("label", "canonical"), TEMPLATE_SPELLINGS)
def test_both_modules_accept_every_template_spelling(label, canonical) -> None:
    assert validation_resolves(label) == canonical
    assert resolver_resolves(label) == canonical


@pytest.mark.parametrize("label", WITHDRAWN_SPELLINGS)
def test_neither_module_accepts_a_withdrawn_spelling(label) -> None:
    """R3-1: Validation must not accept what the Resolver will drop."""
    assert validation_resolves(label) is None, "Validation still accepts it"
    assert resolver_resolves(label) is None, "Resolver unexpectedly accepts it"


@pytest.mark.parametrize("label", sorted(spec.WORKFLOW_ALIASES))
def test_every_alias_the_validator_accepts_the_resolver_also_resolves(label) -> None:
    """The property R3-1 violated, asserted exhaustively over the alias table.

    Anything Validation calls valid must survive resolution, or a project can
    pass its activation gate and lose a workflow immediately afterwards.
    """
    assert validation_resolves(label) == resolver_resolves(label)


def test_canonical_workflows_match_the_resolver_derivation_source() -> None:
    """The transcribed constant must equal what the Resolver derives from Core."""
    assert set(spec.CANONICAL_WORKFLOWS) == {
        canonical for _, canonical in TEMPLATE_SPELLINGS
    }


def test_no_alias_maps_outside_the_canonical_six() -> None:
    assert set(spec.WORKFLOW_ALIASES.values()) <= set(spec.CANONICAL_WORKFLOWS)


# =============================================================================
# WR-3 — validation's view of workflow scope must equal the runtime's
# =============================================================================
# The Validation Layer may not import the Router or the Resolver (§13.7), so it
# restates two Router constants and the Resolver's enabled-set rule. These tests
# fail the day either restatement drifts.
def _real_core():
    import pathlib

    from runtime.core_loader import CoreLoader, FilesystemCoreSource

    root = pathlib.Path(__file__).resolve().parents[1]
    return CoreLoader(FilesystemCoreSource(root / "core")).get_core_bundle()


def test_wr3_the_first_turn_workflow_matches_the_router() -> None:
    from runtime.workflow_router.router import FIRST_TURN_WORKFLOW

    assert spec.FIRST_TURN_WORKFLOW == FIRST_TURN_WORKFLOW


def test_wr3_the_routing_section_matches_the_router() -> None:
    from runtime.workflow_router.router import _ROUTING_SECTION

    assert spec.ROUTING_PHRASES_SECTION == _ROUTING_SECTION


ENABLED_SET_CASES = [
    (),
    ("Discovery",),
    ("discovery.md",),
    ("Discovery", "CRM-Sync", "Follow up"),
    ("Consultation", "Voice Agent"),
    ("_(placeholder)_",),
    ("Lead Qualification",),
    ("Discovery", "Lead Qualification"),
]


@pytest.mark.parametrize("labels", ENABLED_SET_CASES, ids=repr)
def test_wr3_validation_derives_the_resolvers_enabled_set(labels) -> None:
    """Exactly the Resolver's semantics, on a full project through the real
    Loader parser — including that nothing declared enables everything and a
    placeholder-only list enables nothing."""
    from runtime.resolver import Resolver
    from runtime.validation.rule import ProjectRuleContext
    from runtime.validation.rules.config import _enabled_workflows
    from tests.validation.conftest import VALID_CONFIG, document, make_core, make_project

    head, rest = VALID_CONFIG.split("## Enabled Workflows", 1)
    tail = rest[rest.index("\n## ") :]
    items = "".join(f"- **{label}**\n" for label in labels)
    config = document("config.md", f"{head}## Enabled Workflows\n\n{items}{tail}")
    project = make_project(config=config)
    core = make_core()

    resolved = Resolver().resolve(core, project).config.enabled_workflows
    validated = _enabled_workflows(ProjectRuleContext(project=project, core=core))
    assert validated == frozenset(resolved)


def test_wr3_validation_finds_the_targets_the_router_routes_to() -> None:
    """On the real Core: every target validation reads from a workflow's
    "Routing Phrases" is one the Router actually routes to, and no other."""
    from runtime.models.conversation import WorkflowState
    from runtime.validation.rules.config import _published_routing_targets
    from runtime.workflow_router import WorkflowRouter

    core = _real_core()
    router = WorkflowRouter()
    published_any = False
    for name, document in core.workflows.items():
        workflow = name.removesuffix(".md")
        published = set(_published_routing_targets(document))
        routed: set[str] = set()
        for line in document.raw_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or len(stripped) <= 2:
                continue
            state = WorkflowState(conversation_id="wr3", active_workflow=workflow)
            target = router.route(state, stripped[2:].strip(), core).target_workflow
            if target != workflow:
                routed.add(target)
        assert published == routed, workflow
        published_any = published_any or bool(published)
    assert published_any, "Core publishes no routing targets at all"
