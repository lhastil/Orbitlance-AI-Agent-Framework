"""Core Loader tests — specification §1.

Two kinds of test here, and the split is deliberate. Most run against a
synthetic Core built in a tmp directory, so a failure mode can be arranged
exactly (a missing prompt, a malformed guardrail) without editing the real
`core/`. A smaller set runs against the **real repository `core/`**, because a
loader that only ever sees fixtures proves nothing about the framework's actual
content — and because the required-file manifest is a transcription that must
be caught the moment it drifts from what is on disk.

All five §1.12 scenarios are covered, and each is named in the test that covers
it.
"""

from __future__ import annotations

import pathlib

import pytest

from runtime.core_loader import (
    REQUIRED_GUARDRAILS,
    REQUIRED_PROMPTS,
    REQUIRED_TOOL_CONTRACTS,
    REQUIRED_WORKFLOWS,
    CoreDirectoryNotFoundError,
    CoreLoader,
    CoreLoaderError,
    CoreReadError,
    CoreSource,
    FilesystemCoreSource,
    MalformedCoreDocumentError,
    MissingCoreFileError,
    PlaybookContentLeakError,
    manifest,
)
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectDocument

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
REAL_CORE = REPO_ROOT / "core"


# =============================================================================
# a synthetic Core, so failure modes can be arranged precisely
# =============================================================================
def write_core(root: pathlib.Path, **omit: tuple[str, ...]) -> pathlib.Path:
    """Build a complete, valid Core under `root`. `omit` drops named files."""
    core = root / "core"
    plan = {
        manifest.PROMPTS_DIR: REQUIRED_PROMPTS,
        manifest.GUARDRAILS_DIR: REQUIRED_GUARDRAILS,
        manifest.WORKFLOWS_DIR: REQUIRED_WORKFLOWS,
        manifest.TOOLS_DIR: REQUIRED_TOOL_CONTRACTS,
        manifest.KNOWLEDGE_DIR: ("01_company.md", "02_services.md"),
        manifest.TEMPLATES_DIR: ("company.md", "services.md"),
    }
    for directory, names in plan.items():
        target = core / directory
        target.mkdir(parents=True, exist_ok=True)
        skipped = omit.get(directory, ())
        for name in names:
            if name in skipped:
                continue
            (target / name).write_text(
                f"# {name}\n\nBody for {name}.\n\n## Detail\n\nMore.\n",
                encoding="utf-8",
            )

    playbooks = core / manifest.PLAYBOOKS_DIR
    playbooks.mkdir(parents=True, exist_ok=True)
    for name in ("_template.md", "healthcare.md", "hotel.md"):
        (playbooks / name).write_text(
            f"# {name}\n\nPLAYBOOK-CONTENT-MUST-NEVER-LOAD\n", encoding="utf-8"
        )
    return core


@pytest.fixture
def core_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return write_core(tmp_path)


@pytest.fixture
def loader(core_dir: pathlib.Path) -> CoreLoader:
    return CoreLoader(FilesystemCoreSource(core_dir))


# =============================================================================
# §1.12(a) — loads successfully from a complete, valid core/
# =============================================================================
def test_a_loads_successfully_from_a_complete_core(loader: CoreLoader) -> None:
    core = loader.load()
    assert isinstance(core, CoreBundle)
    assert len(core.prompts) == len(REQUIRED_PROMPTS)
    assert len(core.guardrails) == len(REQUIRED_GUARDRAILS)
    assert len(core.workflows) == len(REQUIRED_WORKFLOWS)
    assert len(core.tool_contracts) == len(REQUIRED_TOOL_CONTRACTS)


def test_documents_are_parsed_into_ordered_sections(loader: CoreLoader) -> None:
    document = loader.load().prompts["02_mission.md"]
    assert document.exists
    assert document.raw_text
    assert [s.ordinal for s in document.sections] == list(range(len(document.sections)))
    assert document.sections[0].heading_text == "02_mission.md"


def test_documents_carry_repository_relative_provenance(loader: CoreLoader) -> None:
    """The Prompt Assembler distinguishes `core/` paths from project paths."""
    core = loader.load()
    assert core.prompts["02_mission.md"].relative_path == "core/prompts/02_mission.md"
    assert core.guardrails["safety.md"].relative_path == "core/guardrails/safety.md"
    for document in core.all_documents:
        assert document.relative_path.startswith("core/")
        assert "\\" not in document.relative_path


def test_loading_is_deterministic(loader: CoreLoader) -> None:
    first, second = loader.load(), loader.load()
    assert list(first.prompts) == list(second.prompts)
    assert first.prompts["02_mission.md"].raw_text == (
        second.prompts["02_mission.md"].raw_text
    )
    assert first.playbook_names == second.playbook_names


def test_the_bundle_is_immutable(loader: CoreLoader) -> None:
    core = loader.load()
    with pytest.raises(TypeError):
        core.prompts["new.md"] = ProjectDocument("x", "core/x.md")  # type: ignore[index]


def test_knowledge_contracts_are_loaded(loader: CoreLoader) -> None:
    """Not named by §1.2, but `CoreBundle` holds them and the Resolver reads them."""
    assert set(loader.load().knowledge_contracts) == {"01_company.md", "02_services.md"}


# =============================================================================
# §1.12(b) — fails when a required prompt file is missing
# =============================================================================
def test_b_fails_when_a_required_prompt_is_missing(tmp_path: pathlib.Path) -> None:
    core = write_core(tmp_path, prompts=("02_mission.md",))
    with pytest.raises(MissingCoreFileError) as caught:
        CoreLoader(FilesystemCoreSource(core)).load()
    assert "core/prompts/02_mission.md" in str(caught.value)


@pytest.mark.parametrize(
    ("directory", "missing"),
    [
        (manifest.PROMPTS_DIR, "01_core_personality.md"),
        (manifest.GUARDRAILS_DIR, "safety.md"),
        (manifest.GUARDRAILS_DIR, "escalation.md"),
        (manifest.GUARDRAILS_DIR, "compliance.md"),
        (manifest.WORKFLOWS_DIR, "discovery.md"),
        (manifest.TOOLS_DIR, "crm.md"),
    ],
)
def test_every_required_directory_fails_closed(
    tmp_path: pathlib.Path, directory: str, missing: str
) -> None:
    core = write_core(tmp_path, **{directory: (missing,)})
    with pytest.raises(MissingCoreFileError) as caught:
        CoreLoader(FilesystemCoreSource(core)).load()
    assert missing in str(caught.value)
    assert directory in str(caught.value)


def test_the_guardrail_bundle_is_atomic(tmp_path: pathlib.Path) -> None:
    """Two of three is not a partially-guarded runtime. It is one that must not start."""
    core = write_core(tmp_path, guardrails=("compliance.md",))
    with pytest.raises(MissingCoreFileError):
        CoreLoader(FilesystemCoreSource(core)).load()


def test_a_missing_required_directory_fails_closed(tmp_path: pathlib.Path) -> None:
    core = write_core(tmp_path)
    for path in (core / manifest.TOOLS_DIR).glob("*.md"):
        path.unlink()
    (core / manifest.TOOLS_DIR).rmdir()
    with pytest.raises(MissingCoreFileError, match="tools"):
        CoreLoader(FilesystemCoreSource(core)).load()


def test_an_absent_core_directory_fails_closed(tmp_path: pathlib.Path) -> None:
    with pytest.raises(CoreDirectoryNotFoundError, match="cannot start"):
        CoreLoader(FilesystemCoreSource(tmp_path / "nope")).load()


def test_nothing_is_returned_partially(tmp_path: pathlib.Path) -> None:
    """No degraded Core: a failure yields an exception, never a partial bundle."""
    core = write_core(tmp_path, workflows=("discovery.md",))
    loader = CoreLoader(FilesystemCoreSource(core))
    with pytest.raises(CoreLoaderError):
        loader.get_core_bundle()
    assert not loader.is_cached, "a failed load must not be cached"


# =============================================================================
# §1.12(c) — fails when a guardrail file is malformed
# =============================================================================
def test_c_fails_when_a_guardrail_is_malformed(tmp_path: pathlib.Path) -> None:
    core = write_core(tmp_path)
    (core / manifest.GUARDRAILS_DIR / "safety.md").write_text(
        "no heading here, just prose\n", encoding="utf-8"
    )
    with pytest.raises(MalformedCoreDocumentError) as caught:
        CoreLoader(FilesystemCoreSource(core)).load()
    assert "core/guardrails/safety.md" in str(caught.value)
    assert "no Markdown heading" in str(caught.value)


def test_an_empty_core_document_is_malformed(tmp_path: pathlib.Path) -> None:
    core = write_core(tmp_path)
    (core / manifest.PROMPTS_DIR / "02_mission.md").write_text("   \n\n", encoding="utf-8")
    with pytest.raises(MalformedCoreDocumentError, match="empty"):
        CoreLoader(FilesystemCoreSource(core)).load()


def test_a_malformed_document_names_the_specific_file(tmp_path: pathlib.Path) -> None:
    """§1.9 requires naming the file, not just reporting that Core is broken."""
    core = write_core(tmp_path)
    (core / manifest.WORKFLOWS_DIR / "follow_up.md").write_text("x\n", encoding="utf-8")
    with pytest.raises(MalformedCoreDocumentError) as caught:
        CoreLoader(FilesystemCoreSource(core)).load()
    assert caught.value.relative_path == "core/workflows/follow_up.md"


def test_an_unreadable_file_raises_a_read_error(tmp_path: pathlib.Path) -> None:
    core = write_core(tmp_path)
    (core / manifest.PROMPTS_DIR / "02_mission.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(CoreReadError):
        CoreLoader(FilesystemCoreSource(core)).load()


# =============================================================================
# §1.12(d) — playbook content never appears in the bundle
# =============================================================================
def test_d_playbook_content_is_never_in_the_bundle(loader: CoreLoader) -> None:
    """The source directory contains playbooks with a loud marker. None must load."""
    core = loader.load()
    for document in core.all_documents:
        assert "PLAYBOOK-CONTENT-MUST-NEVER-LOAD" not in document.raw_text
        assert manifest.PLAYBOOKS_DIR not in document.relative_path


def test_playbooks_yield_names_only(loader: CoreLoader) -> None:
    core = loader.load()
    assert core.playbook_names == frozenset({"healthcare", "hotel"})
    assert core.has_playbook("healthcare")
    assert core.has_playbook("healthcare.md")


def test_the_playbook_authoring_template_is_not_a_selectable_playbook(
    loader: CoreLoader,
) -> None:
    core = loader.load()
    assert "_template" not in core.playbook_names
    assert not core.has_playbook("_template")


def test_no_playbook_document_reaches_any_bundle_group(loader: CoreLoader) -> None:
    core = loader.load()
    for group in (
        core.prompts,
        core.guardrails,
        core.workflows,
        core.tool_contracts,
        core.knowledge_contracts,
        core.templates,
    ):
        assert not any("playbook" in path for path in
                       (d.relative_path for d in group.values()))


def test_the_leak_guard_catches_a_playbook_document() -> None:
    """Proves the §1.10 self-check fires — not merely that it never has to."""
    leaked = ProjectDocument(
        name="healthcare.md",
        relative_path="core/industry_playbooks/healthcare.md",
        exists=True,
        raw_text="leaked",
    )
    with pytest.raises(PlaybookContentLeakError, match="reference-only"):
        CoreLoader._assert_no_playbook_content(CoreBundle(prompts={"x": leaked}))


def test_the_leak_guard_tolerates_windows_separators() -> None:
    leaked = ProjectDocument(
        name="hotel.md",
        relative_path="core\\industry_playbooks\\hotel.md",
        exists=True,
    )
    with pytest.raises(PlaybookContentLeakError):
        CoreLoader._assert_no_playbook_content(CoreBundle(workflows={"x": leaked}))


# =============================================================================
# §1.12(e) — repeated getCoreBundle() returns the identical cached instance
# =============================================================================
def test_e_get_core_bundle_returns_the_identical_instance(loader: CoreLoader) -> None:
    first = loader.get_core_bundle()
    assert loader.get_core_bundle() is first, "identity, not equality (§1.12e)"
    assert loader.get_core_bundle() is first


def test_load_always_re_reads(loader: CoreLoader) -> None:
    """`load()` is the worker; `getCoreBundle()` is the cached accessor (§1.6)."""
    assert loader.load() is not loader.load()


def test_the_cache_is_not_populated_until_first_use(loader: CoreLoader) -> None:
    assert not loader.is_cached
    loader.get_core_bundle()
    assert loader.is_cached


def test_invalidating_forces_a_re_read(loader: CoreLoader) -> None:
    first = loader.get_core_bundle()
    loader.invalidate()
    assert loader.get_core_bundle() is not first


def test_the_cache_survives_source_changes_until_invalidated(
    loader: CoreLoader, core_dir: pathlib.Path
) -> None:
    """Core is immutable for the process lifetime — that is the point of caching."""
    first = loader.get_core_bundle()
    (core_dir / manifest.PROMPTS_DIR / "02_mission.md").write_text(
        "# changed\n\nnew body\n", encoding="utf-8"
    )
    assert loader.get_core_bundle() is first
    loader.invalidate()
    assert "new body" in loader.get_core_bundle().prompts["02_mission.md"].raw_text


# =============================================================================
# templates — the one interpretive decision (§1.3 vs the frozen CoreBundle)
# =============================================================================
def test_templates_are_recorded_as_present(loader: CoreLoader) -> None:
    core = loader.load()
    assert set(core.templates) == {"company.md", "services.md"}
    assert core.template("company.md").exists


def test_template_content_is_never_loaded(loader: CoreLoader) -> None:
    """§1.3: meta-documents must not become runtime content."""
    for document in loader.load().templates.values():
        assert document.raw_text == ""
        assert document.sections == ()
        assert document.preamble == ""


def test_the_validation_rule_that_needs_templates_can_answer(loader: CoreLoader) -> None:
    """Presence-only is enough for `knowledge.template_available`, which reads
    only `.exists`. Loading nothing would make it warn falsely, forever."""
    template = loader.load().template("company.md")
    assert template is not None and template.exists


def test_the_decision_is_recorded_where_a_reader_will_find_it() -> None:
    assert manifest.TEMPLATES_ARE_PRESENCE_ONLY is True
    src = (REPO_ROOT / "runtime" / "core_loader" / "manifest.py").read_text(
        encoding="utf-8"
    )
    assert "1.3" in src and "knowledge.template_available" in src


# =============================================================================
# the real repository core/ — a fixture-only loader proves nothing
# =============================================================================
@pytest.fixture(scope="module")
def real_core() -> CoreBundle:
    return CoreLoader(FilesystemCoreSource(REAL_CORE)).get_core_bundle()


def test_the_real_core_loads(real_core: CoreBundle) -> None:
    assert len(real_core.prompts) == 10
    assert len(real_core.guardrails) == 3
    assert len(real_core.workflows) == 6
    assert len(real_core.tool_contracts) == 5
    assert len(real_core.knowledge_contracts) == 8


def test_the_manifest_matches_what_is_actually_on_disk() -> None:
    """A transcription that drifts from `core/` must fail here, not in production."""
    for directory, required in manifest.REQUIRED_FILES.items():
        on_disk = {p.name for p in (REAL_CORE / directory).glob("*.md")}
        assert set(required) == on_disk, f"manifest drifted from core/{directory}/"


def test_the_real_core_carries_no_playbook_content(real_core: CoreBundle) -> None:
    assert real_core.playbook_names
    for document in real_core.all_documents:
        assert "industry_playbooks" not in document.relative_path


def test_the_real_playbooks_are_named_not_loaded(real_core: CoreBundle) -> None:
    assert "healthcare" in real_core.playbook_names
    assert "_template" not in real_core.playbook_names


def test_the_real_core_every_loaded_document_has_sections(real_core: CoreBundle) -> None:
    for document in real_core.all_documents:
        if document.relative_path.startswith("core/templates/"):
            continue  # presence-only by design
        assert document.sections, f"{document.relative_path} parsed into no sections"


def test_the_real_core_satisfies_the_prompt_assembler_contract(
    real_core: CoreBundle,
) -> None:
    """Every file the frozen assembly order names must be present and rendered."""
    from runtime.assembler.core_slots import CORE_PROMPT_FILES, GUARDRAIL_FILES

    for filename in CORE_PROMPT_FILES.values():
        assert filename in real_core.prompts
        assert real_core.prompts[filename].raw_text.strip()
    for filename in GUARDRAIL_FILES:
        assert filename in real_core.guardrails
        assert real_core.guardrails[filename].raw_text.strip()


def test_the_real_core_passes_the_validation_layer(real_core: CoreBundle) -> None:
    """The producer's output satisfies the module written to check it."""
    from runtime.validation import Validator

    result = Validator().validate_core(real_core)
    assert result.valid, [(i.code, i.message) for i in result.issues]


# =============================================================================
# architecture — §1.7 and the one recorded deviation
# =============================================================================
def test_the_source_protocol_is_structural() -> None:
    class Fake:
        def location(self) -> str: return "fake"
        def exists(self) -> bool: return True
        def directory_exists(self, relative_dir: str) -> bool:  # noqa: ARG002
            return False
        def list_documents(self, relative_dir: str) -> tuple[str, ...]:  # noqa: ARG002
            return ()
        def document_exists(self, relative_path: str) -> bool:  # noqa: ARG002
            return False
        def read_document(self, relative_path: str) -> str:  # noqa: ARG002
            return ""

    assert isinstance(Fake(), CoreSource)
    assert isinstance(FilesystemCoreSource("core"), CoreSource)


def test_the_loader_depends_on_no_module_except_the_recorded_one() -> None:
    """§1.7: a root module. `runtime.loader.markdown` is the one documented
    deviation, and it must stay the only one."""
    package = REPO_ROOT / "runtime" / "core_loader"
    allowed = {"runtime.loader.markdown", "runtime.models", "runtime.core_loader"}
    for path in package.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("from runtime", "import runtime")):
                continue
            module = stripped.split()[1]
            assert any(module.startswith(a) for a in allowed), (
                f"{path.name} imports {module}, which §1.7 forbids"
            )


def test_the_deviation_from_rule_seven_is_documented() -> None:
    src = (REPO_ROOT / "runtime" / "core_loader" / "core_loader.py").read_text(
        encoding="utf-8"
    )
    assert "Known deviation" in src
    assert "1.7" in src


def test_no_project_specific_content_is_loaded(loader: CoreLoader) -> None:
    """§1.3: never load anything project-specific."""
    for document in loader.load().all_documents:
        assert "projects/" not in document.relative_path


def test_traversal_outside_the_core_root_is_refused(core_dir: pathlib.Path) -> None:
    source = FilesystemCoreSource(core_dir)
    with pytest.raises(CoreReadError, match="outside the core root"):
        source.read_document("../../etc/passwd")
