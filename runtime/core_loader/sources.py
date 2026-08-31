"""Where Core bytes come from.

The same Dependency Inversion the Project Loader applies, for the same stated
reason. §1.11 records the extension point explicitly:

    "Load Core from a versioned package/registry instead of raw filesystem,
     supporting an eventual framework/runtime repo split."

Depending on this Protocol rather than on `pathlib` means that split costs one
new implementation here and touches nothing else. A source deals in **text and
names only** — it knows nothing about prompts, guardrails, playbooks or
Markdown, because loading semantics belong to the Loader and would make this
abstraction worthless if they leaked into it.

Deliberately separate from `runtime.loader.sources.ProjectSource`: that one is
keyed by `project_id` because it addresses many projects, while Core is a single
immutable bundle with no id. Reusing it would have meant passing a meaningless
project id through every call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from runtime.core_loader.errors import CoreReadError


@runtime_checkable
class CoreSource(Protocol):
    """Read-only access to one `core/` bundle."""

    def location(self) -> str:
        """A human-readable location for Core, used in failure messages."""
        ...

    def exists(self) -> bool:
        """Whether Core itself is present."""
        ...

    def directory_exists(self, relative_dir: str) -> bool:
        ...

    def list_documents(self, relative_dir: str) -> tuple[str, ...]:
        """Markdown file names in a directory, in deterministic order."""
        ...

    def document_exists(self, relative_path: str) -> bool:
        ...

    def read_document(self, relative_path: str) -> str:
        """Read a document as text. Raises `CoreReadError` on failure."""
        ...


class FilesystemCoreSource:
    """Reads Core from a directory on disk.

    Every path resolves beneath the configured root and is checked to remain
    inside it. Core file names come from this module's own manifest rather than
    from user input, so traversal is not an expected threat — the check is
    defence in depth against a future caller that is less careful.
    """

    __slots__ = ("_root",)

    def __init__(self, core_root: str | Path) -> None:
        self._root = Path(core_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, relative: str) -> Path:
        candidate = (self._root / relative).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise CoreReadError(
                str(candidate), ValueError("resolved outside the core root")
            )
        return candidate

    # -- CoreSource ---------------------------------------------------------
    def location(self) -> str:
        return str(self._root)

    def exists(self) -> bool:
        return self._root.is_dir()

    def directory_exists(self, relative_dir: str) -> bool:
        return self._resolve(relative_dir).is_dir()

    def list_documents(self, relative_dir: str) -> tuple[str, ...]:
        directory = self._resolve(relative_dir)
        if not directory.is_dir():
            return ()
        # Sorted so two loads of the same Core produce identical ordering.
        # Core is cached for the process lifetime, so a non-deterministic order
        # would be a defect nobody could reproduce.
        return tuple(sorted(p.name for p in directory.glob("*.md") if p.is_file()))

    def document_exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).is_file()

    def read_document(self, relative_path: str) -> str:
        path = self._resolve(relative_path)
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CoreReadError(str(path), exc) from exc
