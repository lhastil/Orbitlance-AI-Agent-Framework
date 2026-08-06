"""Where project bytes come from.

The Loader depends on this Protocol, never on the filesystem directly. That is
Dependency Inversion applied to the spec's own stated extension point:

    "Future Extension Points: Load from a database/API instead of raw
     filesystem once project count grows into the hundreds."

Swapping the source later means adding an implementation here; the Loader,
`ProjectContext`, and every downstream module are untouched.

A source deals in *text and names only*. It knows nothing about config,
knowledge, extension points or Markdown -- otherwise loading semantics would
leak into the storage layer and the abstraction would be worthless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from runtime.loader.errors import DocumentReadError


@runtime_checkable
class ProjectSource(Protocol):
    """Read-only access to one repository of projects."""

    def project_exists(self, project_id: str) -> bool:
        """Whether `project_id` resolves to exactly one project."""
        ...

    def project_location(self, project_id: str) -> str:
        """A human-readable location for the project, used in messages."""
        ...

    def directory_exists(self, project_id: str, relative_dir: str) -> bool:
        """Whether an extension-point directory is present."""
        ...

    def list_documents(self, project_id: str, relative_dir: str) -> tuple[str, ...]:
        """Document file names in a directory, in deterministic order."""
        ...

    def document_exists(self, project_id: str, relative_path: str) -> bool:
        ...

    def read_document(self, project_id: str, relative_path: str) -> str:
        """Read a document as text. Raises DocumentReadError on failure."""
        ...


class FilesystemProjectSource:
    """Reads projects from a directory on disk.

    Every path is resolved beneath the configured root and checked to remain
    inside it. Combined with the Loader's project-id rejection of separators
    and traversal, that makes escaping a project's own directory structurally
    impossible rather than merely unlikely.
    """

    __slots__ = ("_root",)

    def __init__(self, projects_root: str | Path) -> None:
        self._root = Path(projects_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    # -- resolution ---------------------------------------------------------
    def _project_dir(self, project_id: str) -> Path:
        candidate = (self._root / project_id).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            # Defence in depth: the Loader already rejects separators and
            # traversal, so reaching here means a bug upstream, not user input.
            raise DocumentReadError(
                str(candidate),
                ValueError("resolved outside the projects root"),
            )
        return candidate

    def _resolve(self, project_id: str, relative: str) -> Path:
        base = self._project_dir(project_id)
        candidate = (base / relative).resolve()
        if base not in candidate.parents and candidate != base:
            raise DocumentReadError(
                str(candidate), ValueError("resolved outside the project directory")
            )
        return candidate

    # -- ProjectSource ------------------------------------------------------
    def project_exists(self, project_id: str) -> bool:
        return self._project_dir(project_id).is_dir()

    def project_location(self, project_id: str) -> str:
        return str(self._project_dir(project_id))

    def directory_exists(self, project_id: str, relative_dir: str) -> bool:
        return self._resolve(project_id, relative_dir).is_dir()

    def list_documents(self, project_id: str, relative_dir: str) -> tuple[str, ...]:
        directory = self._resolve(project_id, relative_dir)
        if not directory.is_dir():
            return ()
        # Sorted so two loads of the same project always produce identical
        # ordering -- determinism is a stated requirement of this module.
        return tuple(sorted(p.name for p in directory.glob("*.md") if p.is_file()))

    def document_exists(self, project_id: str, relative_path: str) -> bool:
        return self._resolve(project_id, relative_path).is_file()

    def read_document(self, project_id: str, relative_path: str) -> str:
        path = self._resolve(project_id, relative_path)
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DocumentReadError(str(path), exc) from exc
