"""Project Loader tests.

Covers the five scenarios the frozen spec names for this module, plus the
engineering guarantees Task 2 requires: determinism, purity, isolation, and the
Loader doing no validation.
"""

from __future__ import annotations

import dataclasses

import pytest

from runtime.loader import (
    FilesystemProjectSource,
    InMemoryProjectCache,
    InvalidProjectIdError,
    MalformedConfigError,
    ProjectLoader,
    ProjectNotFoundError,
    config_parser,
)

CONFIG = """# Example Project Configuration

## Purpose

Human prose the Loader must ignore.

## Active Industry Playbook

`core/industry_playbooks/healthcare.md`

## Knowledge Status

Filled in.

## Branding Status

Filled in.

## Integrations Status

Filled in.

## LLM Provider

- **Primary:** anthropic
- **Model:** claude-sonnet-5
- **Secondary (optional):** none

## Enabled Workflows

- **Discovery** — understand the need
- **Consultation** — book a visit

## Operating Constraints

- Never diagnose a condition.
"""


def build_project(tmp_path, project_id="example_client", *, config=CONFIG, dirs=None):
    """Create a project on disk and return a loader bound to its root."""
    root = tmp_path / project_id
    root.mkdir(parents=True)
    if config is not None:
        (root / "config.md").write_text(config, encoding="utf-8")
    for name, files in (dirs or {}).items():
        directory = root / name
        directory.mkdir()
        for filename, text in files.items():
            (directory / filename).write_text(text, encoding="utf-8")
    return ProjectLoader(FilesystemProjectSource(tmp_path))


# --- spec scenario (a): fully-populated project ---------------------------
def test_loads_fully_populated_project(tmp_path) -> None:
    loader = build_project(
        tmp_path,
        dirs={
            "knowledge": {"01_company.md": "# Company\n\n## Overview\n\nReal.\n"},
            "branding": {"brand.md": "# Brand\n"},
            "integrations": {"integrations.md": "# Integrations\n"},
        },
    )
    context = loader.load("example_client")

    assert context.root_exists
    assert context.project_id == "example_client"
    assert context.knowledge.present and len(context.knowledge.documents) == 1
    assert context.branding.present
    assert context.integrations.present
    assert context.config.exists

    data = context.config_data
    assert data.active_playbooks == ("core/industry_playbooks/healthcare.md",)
    assert data.llm_provider.primary == "anthropic"
    assert data.llm_provider.model == "claude-sonnet-5"
    assert data.enabled_workflows == ("Discovery", "Consultation")
    assert "Never diagnose" in data.operating_constraints


# --- spec scenario (b): missing extension points do not raise -------------
def test_missing_extension_points_are_reported_not_raised(tmp_path) -> None:
    loader = build_project(tmp_path, dirs={"knowledge": {"01_company.md": "# C\n"}})
    context = loader.load("example_client")

    assert context.knowledge.present
    assert not context.branding.present
    assert not context.integrations.present
    assert context.branding.documents == {}


def test_present_but_empty_directory_is_present_and_empty(tmp_path) -> None:
    """The empty-scaffold case: present, zero documents, deterministic."""
    loader = build_project(tmp_path, dirs={"knowledge": {}, "branding": {}})
    context = loader.load("example_client")

    assert context.knowledge.present
    assert len(context.knowledge.documents) == 0
    assert context.knowledge.is_empty


# --- spec scenario (c): unknown project id --------------------------------
def test_unknown_project_id_raises(tmp_path) -> None:
    loader = build_project(tmp_path)
    with pytest.raises(ProjectNotFoundError) as excinfo:
        loader.load("no_such_project")
    assert "no_such_project" in str(excinfo.value)


@pytest.mark.parametrize("bad", ["", "   ", "../escape", "a/b", "a\\b"])
def test_unusable_project_ids_are_rejected(tmp_path, bad) -> None:
    """Isolation is structural: an id can never address another directory."""
    loader = build_project(tmp_path)
    with pytest.raises(InvalidProjectIdError):
        loader.load(bad)


# --- spec scenario (d): malformed config ----------------------------------
def test_unreadable_config_raises_malformed_config(tmp_path) -> None:
    root = tmp_path / "broken_client"
    root.mkdir()
    # Invalid UTF-8 -- the file exists but cannot be decoded as text.
    (root / "config.md").write_bytes(b"\xff\xfe\x00\x00 not valid utf-8 \xc3\x28")
    loader = ProjectLoader(FilesystemProjectSource(tmp_path))

    with pytest.raises(MalformedConfigError):
        loader.load("broken_client")


def test_absent_config_is_reported_not_raised(tmp_path) -> None:
    """A missing config is state, not an error -- the Resolver decides."""
    loader = build_project(tmp_path, config=None)
    context = loader.load("example_client")

    assert not context.config.exists
    assert context.config_data.declared_sections == frozenset()


# --- spec scenario (e): no data shared between projects -------------------
def test_two_projects_share_no_loaded_data(tmp_path) -> None:
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "config.md").write_text(
        CONFIG.replace("anthropic", "alpha_provider"), encoding="utf-8"
    )
    (tmp_path / "beta").mkdir()
    (tmp_path / "beta" / "config.md").write_text(
        CONFIG.replace("anthropic", "beta_provider"), encoding="utf-8"
    )
    loader = ProjectLoader(FilesystemProjectSource(tmp_path))

    a, b = loader.load("alpha"), loader.load("beta")

    assert a.config_data.llm_provider.primary == "alpha_provider"
    assert b.config_data.llm_provider.primary == "beta_provider"
    assert a.knowledge is not b.knowledge
    assert a.config_data is not b.config_data


# --- engineering guarantees ------------------------------------------------
def test_loading_is_deterministic(tmp_path) -> None:
    loader = build_project(
        tmp_path,
        dirs={"knowledge": {"02_b.md": "# B\n", "01_a.md": "# A\n", "03_c.md": "# C\n"}},
    )
    first = loader.load("example_client")
    second = loader.load("example_client")

    assert tuple(first.knowledge.documents) == tuple(second.knowledge.documents)
    assert tuple(first.knowledge.documents) == ("01_a.md", "02_b.md", "03_c.md")
    assert first.config_data.enabled_workflows == second.config_data.enabled_workflows


def test_loader_is_pure_by_default(tmp_path) -> None:
    """No cache unless one is injected: two loads produce distinct objects."""
    loader = build_project(tmp_path)
    assert loader.load("example_client") is not loader.load("example_client")


def test_injected_cache_is_used_and_invalidated(tmp_path) -> None:
    cache = InMemoryProjectCache()
    loader = build_project(tmp_path)
    loader = ProjectLoader(FilesystemProjectSource(tmp_path), cache=cache)

    first = loader.load("example_client")
    assert loader.load("example_client") is first, "cache hit expected"

    loader.invalidate("example_client")
    assert loader.load("example_client") is not first, "invalidation must take effect"


def test_invalidate_without_cache_is_a_noop(tmp_path) -> None:
    build_project(tmp_path)
    ProjectLoader(FilesystemProjectSource(tmp_path)).invalidate("anything")


def test_returned_context_is_immutable(tmp_path) -> None:
    loader = build_project(tmp_path)
    context = loader.load("example_client")
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.project_id = "mutated"  # type: ignore[misc]


# --- the Loader must not validate -----------------------------------------
def test_loader_reports_placeholders_verbatim_without_judging_them(tmp_path) -> None:
    """Judging a placeholder is the Validation Layer's job, not the Loader's."""
    config = CONFIG.replace("**Primary:** anthropic", "**Primary:** _(placeholder)_")
    loader = build_project(tmp_path, config=config)
    context = loader.load("example_client")

    assert context.config_data.llm_provider.primary == "_(placeholder)_"


def test_loader_reports_unknown_workflow_without_judging_it(tmp_path) -> None:
    config = CONFIG.replace("- **Discovery**", "- **Not A Real Workflow**")
    loader = build_project(tmp_path, config=config)
    context = loader.load("example_client")

    assert "Not A Real Workflow" in context.config_data.enabled_workflows


def test_loader_reports_nonexistent_playbook_without_resolving_it(tmp_path) -> None:
    config = CONFIG.replace("healthcare.md", "does_not_exist.md")
    loader = build_project(tmp_path, config=config)
    context = loader.load("example_client")

    assert context.config_data.active_playbooks == (
        "core/industry_playbooks/does_not_exist.md",
    )


# --- config parsing --------------------------------------------------------
def test_unrecognised_headings_are_dropped() -> None:
    config = config_parser.parse_config("## Totally Unknown\n\nbody\n")
    assert config.declared_sections == frozenset()


def test_plural_playbook_heading_alias_resolves() -> None:
    config = config_parser.parse_config(
        "## Active Industry Playbook(s)\n\n`hotel.md`\n"
    )
    assert config.declares("Active Industry Playbook")
    assert config.active_playbooks == ("hotel.md",)


def test_shorter_heading_does_not_satisfy_a_longer_section() -> None:
    """Exact resolution only -- no prefix matching (the V-4 defect class)."""
    config = config_parser.parse_config("## Knowledge\n\nbody\n")
    assert not config.declares("Knowledge Status")


def test_duplicate_heading_first_occurrence_wins() -> None:
    config = config_parser.parse_config(
        "## LLM Provider\n\n- **Primary:** first\n\n"
        "## LLM Provider\n\n- **Primary:** second\n"
    )
    assert config.llm_provider.primary == "first"


def test_empty_config_yields_empty_typed_fields() -> None:
    config = config_parser.parse_config("")
    assert config.declared_sections == frozenset()
    assert config.active_playbooks == ()
    assert config.enabled_workflows == ()
    assert config.llm_provider.is_empty
    assert config.operating_constraints == ""


def test_absent_provider_label_is_none_not_empty_string() -> None:
    config = config_parser.parse_config("## LLM Provider\n\n- **Primary:** anthropic\n")
    assert config.llm_provider.primary == "anthropic"
    assert config.llm_provider.model is None
