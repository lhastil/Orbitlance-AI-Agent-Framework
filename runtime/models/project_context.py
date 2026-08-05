"""ProjectContext — the raw, unresolved view of one project's extension points.

Implements the `ProjectContext` data model from docs/runtime-specification.md
(project_id, knowledge map with possibly-absent entries, branding, integrations,
config, completeness flags).

Ownership note: the spec names Project Loader as this model's sole writer. The
Loader does not exist yet (Phase 2 Task 1 is Validation only), so the model
lives in `runtime/models/` where both the Loader and the Validation Layer can
depend on it without either depending on the other. This preserves the frozen
dependency direction (Validation reads Loader output; never calls back).

Everything here is read-only. The Validation Layer must never mutate what it
validates — a validator that edits its input is a design smell the spec
explicitly forbids.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


def _freeze(mapping: Mapping[str, str] | None) -> Mapping[str, str]:
    return MappingProxyType(dict(mapping or {}))


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    """One markdown document belonging to a project.

    `sections` maps a normalised heading (lower-cased, stripped) to its body
    text, so rules can ask "does this document declare section X?" without
    re-parsing markdown themselves.
    """

    name: str
    relative_path: str
    exists: bool = False
    raw_text: str = ""
    sections: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", _freeze(self.sections))

    @classmethod
    def missing(cls, name: str, relative_path: str) -> ProjectDocument:
        return cls(name=name, relative_path=relative_path, exists=False)

    @property
    def is_empty(self) -> bool:
        return not self.raw_text.strip()

    def has_section(self, title: str) -> bool:
        return _normalise(title) in self.sections

    def section_body(self, title: str) -> str:
        return self.sections.get(_normalise(title), "")


@dataclass(frozen=True, slots=True)
class ExtensionPoint:
    """One of the four documented extension points.

    `present` records whether the folder/file existed at all — distinct from
    "existed but was incomplete", which the rules report separately.
    """

    name: str
    present: bool = False
    documents: Mapping[str, ProjectDocument] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "documents", MappingProxyType(dict(self.documents)))

    @classmethod
    def absent(cls, name: str) -> ExtensionPoint:
        return cls(name=name, present=False)

    def document(self, name: str) -> ProjectDocument | None:
        return self.documents.get(name)

    @property
    def is_empty(self) -> bool:
        return not any(d.exists and not d.is_empty for d in self.documents.values())


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Everything the Validation Layer needs to judge one project."""

    project_id: str
    root_path: str
    root_exists: bool = False
    knowledge: ExtensionPoint = field(
        default_factory=lambda: ExtensionPoint.absent("knowledge")
    )
    branding: ExtensionPoint = field(
        default_factory=lambda: ExtensionPoint.absent("branding")
    )
    integrations: ExtensionPoint = field(
        default_factory=lambda: ExtensionPoint.absent("integrations")
    )
    config: ProjectDocument = field(
        default_factory=lambda: ProjectDocument.missing("config.md", "config.md")
    )

    @property
    def extension_points(self) -> tuple[ExtensionPoint, ...]:
        return (self.knowledge, self.branding, self.integrations)


def _normalise(title: str) -> str:
    """Normalise a heading for lookup: strip markdown hashes, case and spacing."""
    return title.strip().lstrip("#").strip().casefold()


normalise_section_title = _normalise
