"""ProjectLoader -- runtime module 2 of docs/runtime-specification.md.

Loads one project into a fully typed `ProjectContext`. Nothing more.

Public interface (frozen spec §6):

    load(project_id) -> ProjectContext
    invalidate(project_id) -> None

What this module does NOT do, by design and by the frozen spec's
non-responsibilities: it does not validate, does not decide whether a project
is valid, does not know workflows, prompts, providers, routing or runtime
behaviour, does not resolve playbooks, and does not decide what a missing
extension point *means* -- that is the Resolver's decision, and pre-empting it
here would collapse two modules into one.

Caching
-------
The frozen spec requires "cache per project; invalidate on detected change" and
puts `invalidate` on the public interface. Task 2's engineering rules forbid
hidden state and global caches. Both hold here because the cache is an
**injected collaborator**, not built-in state:

    ProjectLoader(source)                 -> pure; loads every time
    ProjectLoader(source, cache=...)      -> caching is explicit and visible

The default is pure. `invalidate` remains on the interface as the spec
requires and is meaningful whenever a cache is supplied.
"""

from __future__ import annotations

from runtime.loader import config_parser, markdown
from runtime.loader.cache import ProjectCache
from runtime.loader.errors import (
    DocumentReadError,
    InvalidProjectIdError,
    MalformedConfigError,
    ProjectNotFoundError,
)
from runtime.loader.sources import ProjectSource
from runtime.models.project_context import (
    ExtensionPoint,
    ProjectContext,
    ProjectDocument,
    Section,
)

#: The three directory extension points, and the config file. Names come from
#: the frozen framework; the Loader reads them, it does not decide them.
_KNOWLEDGE_DIR = "knowledge"
_BRANDING_DIR = "branding"
_INTEGRATIONS_DIR = "integrations"
_CONFIG_FILE = "config.md"

_FORBIDDEN_IN_ID = ("/", "\\", "..", "\0")


class ProjectLoader:
    """Loads projects from a `ProjectSource`.

    Holds no per-load state. Two concurrent `load()` calls share nothing, and
    every `ProjectContext` returned is immutable, so callers cannot affect each
    other through a loaded project.
    """

    __slots__ = ("_source", "_cache")

    def __init__(self, source: ProjectSource, *, cache: ProjectCache | None = None) -> None:
        self._source = source
        self._cache = cache

    # -- public interface (frozen spec §6) ---------------------------------
    def load(self, project_id: str) -> ProjectContext:
        """Load one project.

        Raises `InvalidProjectIdError` for an unusable id and
        `ProjectNotFoundError` when the id does not resolve to a project --
        the two failure modes the frozen spec names. A missing extension point
        is reported as absent, never raised: deciding what absence means
        belongs to the Resolver.
        """
        self._guard_project_id(project_id)

        if self._cache is not None:
            cached = self._cache.get(project_id)
            if cached is not None:
                return cached

        context = self._load_uncached(project_id)

        if self._cache is not None:
            self._cache.put(project_id, context)
        return context

    def invalidate(self, project_id: str) -> None:
        """Drop any cached context for `project_id`.

        A no-op when no cache was injected, which is the default. Kept on the
        interface because the frozen spec defines it there.
        """
        if self._cache is not None:
            self._cache.invalidate(project_id)

    # -- loading ------------------------------------------------------------
    def _load_uncached(self, project_id: str) -> ProjectContext:
        source = self._source
        if not source.project_exists(project_id):
            raise ProjectNotFoundError(project_id, source.project_location(project_id))

        root_path = source.project_location(project_id)
        config_document = self._load_config(project_id)

        return ProjectContext(
            project_id=project_id,
            root_path=root_path,
            root_exists=True,
            knowledge=self._load_extension_point(project_id, _KNOWLEDGE_DIR),
            branding=self._load_extension_point(project_id, _BRANDING_DIR),
            integrations=self._load_extension_point(project_id, _INTEGRATIONS_DIR),
            config=config_document,
            config_data=config_parser.parse_config(config_document.raw_text),
        )

    def _load_config(self, project_id: str) -> ProjectDocument:
        """Load `config.md`, mapping a read failure to the spec's named error.

        The frozen spec lists "Malformed `config.md` -> error" as a failure
        mode of this module. A config file that cannot be decoded or read is
        exactly that; anything about its *content* being wrong or incomplete is
        a Validation Layer finding, never raised here.
        """
        try:
            return self._load_document(project_id, _CONFIG_FILE, _CONFIG_FILE)
        except DocumentReadError as exc:
            raise MalformedConfigError(exc.path, str(exc.cause)) from exc

    def _load_extension_point(self, project_id: str, directory: str) -> ExtensionPoint:
        if not self._source.directory_exists(project_id, directory):
            return ExtensionPoint.absent(directory)

        documents = {
            name: self._load_document(project_id, f"{directory}/{name}", name)
            for name in self._source.list_documents(project_id, directory)
        }
        return ExtensionPoint(name=directory, present=True, documents=documents)

    def _load_document(
        self, project_id: str, relative_path: str, name: str
    ) -> ProjectDocument:
        if not self._source.document_exists(project_id, relative_path):
            return ProjectDocument.missing(name, relative_path)

        text = self._source.read_document(project_id, relative_path)
        parsed = markdown.split_sections(text)
        return ProjectDocument(
            name=name,
            relative_path=relative_path,
            exists=True,
            raw_text=text,
            sections=tuple(
                Section(
                    ordinal=ordinal,
                    heading_text=parsed_section.heading,
                    heading_level=parsed_section.level,
                    body=parsed_section.body,
                )
                for ordinal, parsed_section in enumerate(parsed.sections)
            ),
            preamble=parsed.preamble,
        )

    # -- guards -------------------------------------------------------------
    @staticmethod
    def _guard_project_id(project_id: str) -> None:
        """Reject ids that could address anything but their own directory.

        This is where the framework's project-isolation rule is structurally
        enforced: an id containing a separator or traversal is rejected before
        it ever reaches the source, so no project can read another's data even
        if a caller supplies a hostile id.
        """
        if not project_id or not project_id.strip():
            raise InvalidProjectIdError(project_id, "must not be empty")
        for token in _FORBIDDEN_IN_ID:
            if token in project_id:
                raise InvalidProjectIdError(
                    project_id,
                    f"must not contain {token!r} -- a project id addresses exactly "
                    "one directory and can never traverse outside it",
                )
