"""Core Loader — reads `core/` into an immutable `CoreBundle`, once per process.

Implements specification §1. The root module: it depends on no other runtime
module, and every module that consumes `CoreBundle` — Resolver, Prompt Assembler,
Validation Layer — has been waiting for a producer since it was written. Until
now only tests constructed one by hand.

**Fail closed, always.** §1.9 makes a missing required file or an unparseable
document a hard failure that stops the runtime starting. Nothing here degrades,
substitutes a default, or returns a partial bundle: Core is the framework's own
content, so a broken Core means every project built on it is broken, and
starting anyway would serve prompts assembled from something nobody verified.

**Three directories are treated differently, and the differences are the point:**

* `prompts/`, `guardrails/`, `workflows/`, `tools/`, `knowledge/` load fully.
* `templates/` records presence only — see `manifest.TEMPLATES_ARE_PRESENCE_ONLY`
  for why, and for the one interpretive decision this module makes.
* `industry_playbooks/` yields **names only**. Their content must never reach
  the runtime; §1.10 makes its presence in a `CoreBundle` a Core Loader defect,
  and this module asserts that on its own output before returning.

---

**Known deviation from §1.7, flagged for the system owner.**

§1.7 states this module "depends on no other runtime module". It imports one:
`runtime.loader.markdown`, a stateless text-parsing function that turns Markdown
into ordered sections.

The alternative is duplicating that parser here, and that is worse than the
deviation. `Section.ordinal` is the identity the Token Budget Manager selects
Knowledge by and the Prompt Assembler resolves it with; if Core documents and
project documents were parsed by two copies of the same logic, the copies would
eventually drift and the two would decompose identically-shaped Markdown
differently. That is precisely the class of silent divergence Module 2's lossless
decomposition was rebuilt to eliminate.

`split_sections` is shared infrastructure that happens to live inside Module 2's
package rather than Module 2 behaviour: no state, no configuration, no project
semantics. The correct fix is to promote it to a shared location, which means
editing Module 2 and needs its own authorization. Until then the edge is
documented here rather than hidden, and a test asserts that this is the *only*
cross-module import this package makes.
"""

from __future__ import annotations

from runtime.core_loader import manifest
from runtime.core_loader.errors import (
    CoreDirectoryNotFoundError,
    MalformedCoreDocumentError,
    MissingCoreFileError,
    PlaybookContentLeakError,
)
from runtime.core_loader.sources import CoreSource
from runtime.loader.markdown import split_sections
from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import ProjectDocument, Section


class CoreLoader:
    """Loads and caches the immutable Core bundle (§1.6).

    `load()` always reads. `get_core_bundle()` reads once and returns the
    identical instance thereafter — §1.2 requires caching for the process
    lifetime, and §1.12(e) requires repeated calls to return the same object,
    not merely an equal one. Identity matters because `CoreBundle` is large and
    every module holds it for the process lifetime; two equal copies would be
    silent memory duplication and a source of confusing debugging.
    """

    __slots__ = ("_cached", "_source")

    def __init__(self, source: CoreSource) -> None:
        self._source = source
        self._cached: CoreBundle | None = None

    # -- §1.6 public interface ----------------------------------------------
    def load(self) -> CoreBundle:
        """Read Core from the source and validate it. Never cached."""
        if not self._source.exists():
            raise CoreDirectoryNotFoundError(self._source.location())

        self._assert_required_files_present()

        bundle = CoreBundle(
            prompts=self._load_directory(manifest.PROMPTS_DIR),
            guardrails=self._load_directory(manifest.GUARDRAILS_DIR),
            workflows=self._load_directory(manifest.WORKFLOWS_DIR),
            tool_contracts=self._load_directory(manifest.TOOLS_DIR),
            knowledge_contracts=self._load_directory(manifest.KNOWLEDGE_DIR),
            templates=self._load_presence_only(manifest.TEMPLATES_DIR),
            playbook_names=self._playbook_names(),
        )
        self._assert_no_playbook_content(bundle)
        return bundle

    def get_core_bundle(self) -> CoreBundle:
        """The cached bundle, loading it on first call (§1.2, §1.12e)."""
        if self._cached is None:
            self._cached = self.load()
        return self._cached

    def invalidate(self) -> None:
        """Drop the cache so the next `get_core_bundle()` re-reads.

        Not part of §1.6 and not for production use — Core is immutable for the
        process lifetime. It exists so a test can prove the cache is real by
        observing that clearing it changes the answer.
        """
        self._cached = None

    @property
    def is_cached(self) -> bool:
        return self._cached is not None

    # -- loading -------------------------------------------------------------
    def _load_directory(self, relative_dir: str) -> dict[str, ProjectDocument]:
        """Every `.md` in a directory, parsed, keyed by filename."""
        return {
            name: self._read_document(relative_dir, name)
            for name in self._source.list_documents(relative_dir)
        }

    def _load_presence_only(self, relative_dir: str) -> dict[str, ProjectDocument]:
        """Record that each document exists, without reading any of it.

        `raw_text` and `sections` stay empty deliberately. See
        `manifest.TEMPLATES_ARE_PRESENCE_ONLY`.
        """
        return {
            name: ProjectDocument(
                name=name,
                relative_path=self._relative_path(relative_dir, name),
                exists=True,
            )
            for name in self._source.list_documents(relative_dir)
        }

    def _playbook_names(self) -> frozenset[str]:
        """Playbook stems. The files are listed, never opened (§1.3).

        `_template.md` is excluded: it is the authoring scaffold for writing a
        playbook, not a playbook a project could select.
        """
        return frozenset(
            name[:-3]
            for name in self._source.list_documents(manifest.PLAYBOOKS_DIR)
            if name.endswith(".md") and not name.startswith("_")
        )

    def _read_document(self, relative_dir: str, name: str) -> ProjectDocument:
        relative_path = self._relative_path(relative_dir, name)
        text = self._source.read_document(f"{relative_dir}/{name}")
        parsed = split_sections(text)

        if not text.strip():
            raise MalformedCoreDocumentError(relative_path, "the file is empty")
        if not parsed.sections:
            raise MalformedCoreDocumentError(
                relative_path,
                "it contains no Markdown heading, so it parses into no sections; "
                "every Core document is structured Markdown",
            )

        return ProjectDocument(
            name=name,
            relative_path=relative_path,
            exists=True,
            raw_text=text,
            sections=tuple(
                Section(
                    ordinal=ordinal,
                    heading_text=section.heading,
                    heading_level=section.level,
                    body=section.body,
                )
                for ordinal, section in enumerate(parsed.sections)
            ),
            preamble=parsed.preamble,
        )

    @staticmethod
    def _relative_path(relative_dir: str, name: str) -> str:
        """Repository-relative, e.g. `core/prompts/02_mission.md`.

        The Prompt Assembler reads this as provenance and distinguishes
        `core/`-prefixed paths from project-relative ones, so the prefix is part
        of the contract rather than a formatting choice.
        """
        return f"{manifest.CORE_PATH_PREFIX}{relative_dir}/{name}"

    # -- §1.10 validation ----------------------------------------------------
    def _assert_required_files_present(self) -> None:
        """Every §1.10 required file exists, or the runtime does not start.

        Checked before anything is read so the failure names the first missing
        file rather than surfacing later as a confusing absence downstream.
        """
        for relative_dir, required in manifest.REQUIRED_FILES.items():
            searched = f"{manifest.CORE_PATH_PREFIX}{relative_dir}/"
            if not self._source.directory_exists(relative_dir):
                raise MissingCoreFileError(f"{searched}{required[0]}", searched)
            present = set(self._source.list_documents(relative_dir))
            for name in required:
                if name not in present:
                    raise MissingCoreFileError(f"{searched}{name}", searched)

    @staticmethod
    def _assert_no_playbook_content(bundle: CoreBundle) -> None:
        """§1.10: playbook content in the bundle is this module's defect.

        Checked structurally, by provenance, because that is what this module
        controls: a document is playbook content precisely when it was read from
        the playbook directory. Scanning text for playbook-shaped phrases is the
        Validation Layer's CORE005, and it looks for a different thing — content
        that *resembles* a playbook, wherever it came from.
        """
        marker = f"{manifest.CORE_PATH_PREFIX}{manifest.PLAYBOOKS_DIR}/"
        for document in bundle.all_documents:
            path = (document.relative_path or "").replace("\\", "/")
            if path.startswith(marker):
                raise PlaybookContentLeakError(path)
