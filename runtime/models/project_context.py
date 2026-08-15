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

from runtime.models.project_config import ProjectConfig


@dataclass(frozen=True, slots=True)
class Section:
    """One heading occurrence in a document, addressable by ordinal.

    Identity is `(document name, ordinal)` — never the heading. Headings repeat
    legitimately: `02_services.md` contains `Category` five times, once per
    service. Keying by heading collapsed four of the five, so identity is
    positional and the heading is an attribute.

    `heading_text` is the original text verbatim, and `heading_level` the `#`
    count. Both were previously discarded, making the original capitalisation
    and document structure unrecoverable.
    """

    ordinal: int
    heading_text: str
    heading_level: int
    body: str

    @property
    def normalised_heading(self) -> str:
        """Lookup form. Derived on demand — never stored in place of the original."""
        return _normalise(self.heading_text)


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    """One markdown document belonging to a project.

    `sections` is the **authoritative, lossless, ordered decomposition**: every
    heading occurrence in document order, duplicates included. `preamble` holds
    any content before the first heading.

    It replaced a `Mapping[str, str]` keyed on normalised headings, which was
    built for lookup and could not represent a document faithfully — duplicate
    headings collapsed, heading text was casefolded, heading level was dropped
    and preamble was discarded, losing 27.8% of the reference project's
    Knowledge. `has_section` and `section_body` remain as **derived**
    conveniences over this sequence; there is deliberately no second mapping
    kept alongside it, so the two cannot drift.

    `raw_text` is unchanged and remains byte-exact — it is the authoritative
    record from which this decomposition is derived, and the source every
    byte-sensitive consumer (secret scanning and its line numbers, client-content
    patterns) already reads.
    """

    name: str
    relative_path: str
    exists: bool = False
    raw_text: str = ""
    sections: tuple[Section, ...] = ()
    preamble: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", tuple(self.sections))

    @classmethod
    def missing(cls, name: str, relative_path: str) -> ProjectDocument:
        return cls(name=name, relative_path=relative_path, exists=False)

    @property
    def is_empty(self) -> bool:
        return not self.raw_text.strip()

    def section(self, ordinal: int) -> Section | None:
        """The section at `ordinal`, or None. The authoritative addressing mode."""
        for candidate in self.sections:
            if candidate.ordinal == ordinal:
                return candidate
        return None

    def sections_named(self, title: str) -> tuple[Section, ...]:
        """Every occurrence of a heading, in document order.

        The honest answer when a heading repeats — `section_body` can only
        return one.
        """
        key = _normalise(title)
        return tuple(s for s in self.sections if s.normalised_heading == key)

    def has_section(self, title: str) -> bool:
        return bool(self.sections_named(title))

    def section_body(self, title: str) -> str:
        """The body of the **first** occurrence, or "" when absent.

        First-wins matches the policy `freeze_sections` already documents: a
        duplicated heading must not let later content silently replace what an
        earlier consumer reasoned about. The previous `dict()` construction was
        last-wins, contradicting that rule. Use `sections_named` when a document
        may legitimately repeat a heading.
        """
        found = self.sections_named(title)
        return found[0].body if found else ""


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
    """One project, loaded.

    Produced by the Project Loader; consumed by the Validation Layer, the
    Resolver, and everything downstream of them.

    `config` is the raw `config.md` document; `config_data` is that same file
    parsed into typed fields. Downstream modules read `config_data` and should
    never re-parse `config.raw_text` -- the Loader is the only Markdown parser
    in the runtime (ADR 0004). `config` is retained because rules legitimately
    need the document's path and existence for reporting, and because a future
    consumer may need a section this type does not yet model.
    """

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
    config_data: ProjectConfig = field(default_factory=ProjectConfig.empty)

    @property
    def extension_points(self) -> tuple[ExtensionPoint, ...]:
        return (self.knowledge, self.branding, self.integrations)


def _normalise(title: str) -> str:
    """Normalise a heading for lookup: strip markdown hashes, case and spacing."""
    return title.strip().lstrip("#").strip().casefold()


normalise_section_title = _normalise
