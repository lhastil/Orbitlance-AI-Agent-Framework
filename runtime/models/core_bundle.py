"""CoreBundle — the immutable in-memory view of `core/`.

Implements the `CoreBundle` data model from docs/runtime-specification.md.
Owned (written) by the Core Loader, which does not exist yet; defined here so
the Validation Layer can validate Core without depending on the Loader.

Critically, CoreBundle carries **no industry playbook content**. Playbooks are
reference-only and must never load at runtime — the spec makes the presence of
playbook content inside a CoreBundle a Core Loader defect. `playbook_names`
holds names only, because Config validation must confirm a project's selected
playbook actually exists without ever reading its content.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from runtime.models.project_context import ProjectDocument


@dataclass(frozen=True, slots=True)
class CoreBundle:
    """Immutable representation of everything loaded from `core/`."""

    prompts: Mapping[str, ProjectDocument] = field(default_factory=dict)
    guardrails: Mapping[str, ProjectDocument] = field(default_factory=dict)
    workflows: Mapping[str, ProjectDocument] = field(default_factory=dict)
    tool_contracts: Mapping[str, ProjectDocument] = field(default_factory=dict)
    knowledge_contracts: Mapping[str, ProjectDocument] = field(default_factory=dict)
    templates: Mapping[str, ProjectDocument] = field(default_factory=dict)
    playbook_names: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for attr in (
            "prompts",
            "guardrails",
            "workflows",
            "tool_contracts",
            "knowledge_contracts",
            "templates",
        ):
            object.__setattr__(
                self, attr, MappingProxyType(dict(getattr(self, attr)))
            )
        object.__setattr__(self, "playbook_names", frozenset(self.playbook_names))

    def has_playbook(self, name: str) -> bool:
        return _playbook_key(name) in {_playbook_key(p) for p in self.playbook_names}

    def template(self, name: str) -> ProjectDocument | None:
        return self.templates.get(name)

    @property
    def all_documents(self) -> tuple[ProjectDocument, ...]:
        groups = (
            self.prompts,
            self.guardrails,
            self.workflows,
            self.tool_contracts,
            self.knowledge_contracts,
            self.templates,
        )
        return tuple(doc for group in groups for doc in group.values())


def _playbook_key(name: str) -> str:
    """Compare playbooks by bare stem so `healthcare`, `healthcare.md` and
    `core/industry_playbooks/healthcare.md` all match."""
    stem = name.strip().replace("\\", "/").rsplit("/", 1)[-1]
    return stem[:-3].casefold() if stem.casefold().endswith(".md") else stem.casefold()


playbook_key = _playbook_key
