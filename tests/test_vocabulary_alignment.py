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
