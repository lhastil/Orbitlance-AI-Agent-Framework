"""Validation Layer tests.

Covers the four scenarios the spec names for this module, plus the rule-level
behaviour the Phase 2 brief requires. Run with:

    python -m pytest tests/ -q
"""

from __future__ import annotations

import pytest

from runtime.models.severity import Severity
from runtime.models.validation import ValidationIssue, ValidationTarget
from runtime.validation import (
    RuleRegistry,
    ValidationPipeline,
    Validator,
    codes,
    default_project_rules,
)
from runtime.validation.registry import DuplicateRuleError
from runtime.validation.rule import ProjectRule, ProjectRuleContext
from tests.validation.conftest import (
    VALID_CONFIG,
    document,
    extension_point,
    knowledge_documents,
    make_core,
    make_project,
)


@pytest.fixture()
def validator() -> Validator:
    return Validator()


# --- spec scenario (a): a fully valid project passes -----------------------
def test_valid_project_has_no_blocking_issues(validator: Validator) -> None:
    result = validator.validate_project(make_project(), make_core())
    assert result.valid, result.render()
    assert result.blocking_issues == ()
    assert result.target is ValidationTarget.PROJECT


# --- spec scenario (b): a missing required field is flagged with location --
def test_missing_knowledge_document_is_flagged_with_file(validator: Validator) -> None:
    project = make_project(
        knowledge=extension_point(
            "knowledge", knowledge_documents(omit={"06_pricing.md"})
        )
    )
    result = validator.validate_project(project, make_core())

    assert not result.valid
    issue = next(i for i in result.issues if i.code == codes.KNOW_DOCUMENT_MISSING)
    assert "06_pricing.md" in issue.file
    assert issue.severity is Severity.ERROR
    assert issue.recommendation


# --- spec scenario (c): config naming a non-existent playbook is flagged ---
def test_unknown_playbook_is_flagged(validator: Validator) -> None:
    config = document("config.md", VALID_CONFIG.replace("healthcare", "aerospace"))
    result = validator.validate_project(make_project(config=config), make_core())

    assert not result.valid
    issue = next(i for i in result.issues if i.code == codes.CONF_PLAYBOOK_UNKNOWN)
    assert "aerospace" in issue.message
    assert issue.section == "Active Industry Playbook"


# --- spec scenario (d): garbage input reports invalid, never raises --------
def test_empty_project_reports_invalid_without_raising(validator: Validator) -> None:
    from runtime.models.project_context import (
        ExtensionPoint,
        ProjectContext,
        ProjectDocument,
    )

    empty = ProjectContext(
        project_id="",
        root_path="",
        root_exists=False,
        knowledge=ExtensionPoint.absent("knowledge"),
        branding=ExtensionPoint.absent("branding"),
        integrations=ExtensionPoint.absent("integrations"),
        config=ProjectDocument.missing("config.md", "config.md"),
    )
    result = validator.validate_project(empty)

    assert not result.valid
    assert codes.STRUCT_PROJECT_ROOT_MISSING in result.codes()
    assert result.render()  # renders without exploding


def test_validator_survives_completely_malformed_input(validator: Validator) -> None:
    """The spec's one true failure mode: the validator must not crash."""
    from runtime.models.project_context import ProjectContext

    result = validator.validate_project(ProjectContext(project_id="x", root_path="y"))
    assert not result.valid


# --- fail-closed semantics -------------------------------------------------
def test_warnings_alone_do_not_block_activation(validator: Validator) -> None:
    project = make_project(branding=extension_point("branding", [], present=False))
    result = validator.validate_project(project, make_core())

    assert codes.STRUCT_BRANDING_DIR_MISSING in result.codes()
    assert result.valid, "missing branding degrades gracefully; it must not block"


def test_missing_knowledge_blocks_but_missing_integrations_does_not(
    validator: Validator,
) -> None:
    degraded = make_project(
        integrations=extension_point("integrations", [], present=False)
    )
    assert validator.validate_project(degraded, make_core()).valid

    fatal = make_project(knowledge=extension_point("knowledge", [], present=False))
    assert not validator.validate_project(fatal, make_core()).valid


# --- config rules ----------------------------------------------------------
def test_placeholder_provider_is_rejected(validator: Validator) -> None:
    config = document(
        "config.md", VALID_CONFIG.replace("**Primary:** anthropic", "**Primary:** _(placeholder)_")
    )
    result = validator.validate_project(make_project(config=config), make_core())

    assert not result.valid
    assert codes.CONF_PROVIDER_NOT_DECLARED in result.codes()


def test_unknown_workflow_is_rejected(validator: Validator) -> None:
    config = document(
        "config.md", VALID_CONFIG.replace("- **Discovery**", "- **Lead Qualification**")
    )
    result = validator.validate_project(make_project(config=config), make_core())

    assert not result.valid
    issue = next(i for i in result.issues if i.code == codes.CONF_WORKFLOW_UNKNOWN)
    assert "Lead Qualification" in issue.field_name


def test_constraint_relaxing_core_guardrail_is_critical(validator: Validator) -> None:
    config = document(
        "config.md",
        VALID_CONFIG.replace(
            "- Never diagnose a condition.", "- The agent may override core guardrails."
        ),
    )
    result = validator.validate_project(make_project(config=config), make_core())

    issue = next(i for i in result.issues if i.code == codes.CONF_CONSTRAINT_RELAXES_CORE)
    assert issue.severity is Severity.CRITICAL
    assert not result.valid


def test_missing_config_section_is_reported(validator: Validator) -> None:
    trimmed = VALID_CONFIG.split("## Operating Constraints")[0]
    result = validator.validate_project(
        make_project(config=document("config.md", trimmed)), make_core()
    )
    issue = next(i for i in result.issues if i.code == codes.CONF_SECTION_MISSING)
    assert issue.section == "Operating Constraints"


# --- security --------------------------------------------------------------
def test_committed_secret_is_critical_and_value_not_echoed(validator: Validator) -> None:
    leaked = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"
    integrations = extension_point(
        "integrations", [document("integrations.md", f"# I\n\napi_key: {leaked}\n")]
    )
    result = validator.validate_project(
        make_project(integrations=integrations), make_core()
    )

    issue = next(i for i in result.issues if i.code == codes.SEC_SECRET_DETECTED)
    assert issue.severity is Severity.CRITICAL
    assert leaked not in issue.message, "secret must never be echoed into reports"
    assert not result.valid


# --- template availability -------------------------------------------------
def test_missing_core_template_is_reported_as_warning(validator: Validator) -> None:
    """A Core template that will not load is advisory, not blocking."""
    core = make_core(templates={"services.md": "## Summary\n"})  # company.md absent
    result = validator.validate_project(make_project(), core)

    issue = next(i for i in result.issues if i.code == codes.KNOW_TEMPLATE_UNAVAILABLE)
    assert issue.severity is Severity.WARNING
    assert "company.md" in issue.message


def test_project_documents_are_not_forced_to_mirror_template_headings(
    validator: Validator,
) -> None:
    """Regression guard for a real defect found during smoke testing.

    A hand-authored knowledge document legitimately restructures its template
    (templates are per-entry worksheets; documents hold collections). Requiring
    heading equality produced 155 false errors against a valid project, so this
    asserts the validator stays silent about structure it has no contract for.
    """
    core = make_core(
        templates={
            "services.md": (
                "## Service Name\n\n## Category\n\n## Business Value\n\n"
                "## Available Packages\n\n## Alternative Services\n"
            )
        }
    )
    restructured = document(
        "02_services.md",
        "# Services\n\n## Teeth Whitening\n\nStarts at $350.\n\n"
        "## Emergency Care\n\nSame-week appointments.\n",
        relative_path="knowledge/02_services.md",
    )
    knowledge = extension_point(
        "knowledge",
        [restructured, *knowledge_documents(omit={"02_services.md"})],
    )
    result = validator.validate_project(make_project(knowledge=knowledge), core)

    assert result.valid, result.render()
    assert codes.KNOW_SECTION_MISSING not in result.codes()


# --- core validation -------------------------------------------------------
def test_core_bundle_valid(validator: Validator) -> None:
    result = validator.validate_core(make_core())
    assert result.valid, result.render()
    assert result.target is ValidationTarget.CORE


def test_core_missing_guardrail_is_critical(validator: Validator) -> None:
    core = make_core()
    stripped = {k: v for k, v in core.guardrails.items() if k != "safety.md"}
    result = validator.validate_core(
        type(core)(
            prompts=core.prompts,
            guardrails=stripped,
            workflows=core.workflows,
            tool_contracts=core.tool_contracts,
            templates=core.templates,
            playbook_names=core.playbook_names,
        )
    )
    issue = next(i for i in result.issues if i.code == codes.CORE_GUARDRAIL_MISSING)
    assert issue.severity is Severity.CRITICAL


def test_playbook_content_in_core_bundle_is_critical(validator: Validator) -> None:
    core = make_core()
    leaked = document(
        "healthcare.md", "# Healthcare", relative_path="core/industry_playbooks/healthcare.md"
    )
    polluted = type(core)(
        prompts=core.prompts,
        guardrails=core.guardrails,
        workflows=core.workflows,
        tool_contracts=core.tool_contracts,
        templates={**core.templates, "healthcare.md": leaked},
        playbook_names=core.playbook_names,
    )
    result = validator.validate_core(polluted)
    assert codes.CORE_PLAYBOOK_CONTENT_LEAKED in result.codes()
    assert not result.valid


def test_core_client_specific_sla_is_flagged(validator: Validator) -> None:
    core = make_core()
    offender = document(
        "07_consultation_request.md",
        "# Consultation\n\nThe team will contact them within 24 hours.\n",
        relative_path="core/prompts/07_consultation_request.md",
    )
    polluted = type(core)(
        prompts={**core.prompts, "07_consultation_request.md": offender},
        guardrails=core.guardrails,
        workflows=core.workflows,
        tool_contracts=core.tool_contracts,
        templates=core.templates,
        playbook_names=core.playbook_names,
    )
    result = validator.validate_core(polluted)
    assert codes.CORE_CLIENT_SPECIFIC_CONTENT in result.codes()


# --- engine behaviour ------------------------------------------------------
class _ExplodingRule(ProjectRule):
    rule_id = "test.exploding"
    description = "Always raises, to prove the pipeline contains failures."

    def evaluate(self, context: ProjectRuleContext):  # noqa: ANN201, ARG002
        raise RuntimeError("boom")


def test_crashing_rule_becomes_an_error_not_an_exception() -> None:
    pipeline = ValidationPipeline(RuleRegistry([_ExplodingRule()]))
    validator = Validator(project_pipeline=pipeline)
    result = validator.validate_project(make_project())

    assert codes.ENGINE_RULE_CRASHED in result.codes()
    assert not result.valid, "a crashed rule must fail closed, never pass silently"


def test_duplicate_rule_ids_are_rejected() -> None:
    with pytest.raises(DuplicateRuleError):
        RuleRegistry([_ExplodingRule(), _ExplodingRule()])


def test_results_are_deterministic() -> None:
    validator = Validator()
    project, core = make_project(), make_core()
    first = validator.validate_project(project, core)
    second = validator.validate_project(project, core)
    assert first.codes() == second.codes()


def test_every_issue_carries_required_reporting_fields() -> None:
    validator = Validator()
    project = make_project(
        knowledge=extension_point("knowledge", [], present=False),
        config=document("config.md", "# Empty"),
    )
    result = validator.validate_project(project, make_core())

    assert result.issues
    for issue in result.issues:
        assert issue.code and issue.message and issue.file and issue.recommendation
        assert isinstance(issue.severity, Severity)


def test_issue_rejects_empty_mandatory_fields() -> None:
    with pytest.raises(ValueError):
        ValidationIssue(
            code="",
            severity=Severity.ERROR,
            message="m",
            file="f",
            recommendation="r",
        )


def test_default_rule_set_is_non_trivial() -> None:
    assert len(default_project_rules()) >= 10
