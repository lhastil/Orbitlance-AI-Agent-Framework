"""Typed representation of a project's `config.md`.

Produced exclusively by the Project Loader. This is the boundary between
Markdown and runtime objects: everything downstream of the Loader consumes
these types and never sees raw configuration text again (ADR 0004).

Deliberately *syntactic*, not semantic. The Loader reports what the document
says; it does not judge whether what it says is acceptable. So:

  * a field that is present but holds template placeholder text is returned
    verbatim -- deciding that a placeholder is not a real value is the
    Validation Layer's call, not the Loader's;
  * workflow and playbook names are returned as declared, not resolved against
    the framework's canonical lists -- resolving them requires framework
    knowledge the Loader has no business owning, and checking them is
    validation.

That split is what keeps the Loader free of validation logic while still
producing fully typed output.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class LlmProviderSelection:
    """The `LLM Provider` section, as declared.

    Every field is the literal text found after the label, or None when the
    labelled line is absent entirely. A placeholder such as
    `_(not yet selected)_` is returned as-is; it is not None.
    """

    primary: str | None = None
    model: str | None = None
    secondary: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.primary is None and self.model is None and self.secondary is None


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """`config.md` parsed into typed fields.

    `sections` retains every recognised section body so a future consumer can
    read a section this type does not yet model, without re-parsing Markdown.
    Unrecognised headings are dropped: they carry no contract.
    """

    #: Canonical names of the recognised sections this document declares.
    declared_sections: frozenset[str] = field(default_factory=frozenset)

    #: Canonical section name -> body text, for recognised sections only.
    sections: Mapping[str, str] = field(default_factory=dict)

    #: Industry playbooks named in `Active Industry Playbook`, as declared.
    active_playbooks: tuple[str, ...] = ()

    #: The `LLM Provider` selection, as declared.
    llm_provider: LlmProviderSelection = field(default_factory=LlmProviderSelection)

    #: Workflow labels from `Enabled Workflows`, as declared (never resolved).
    enabled_workflows: tuple[str, ...] = ()

    #: `Operating Constraints` body. Prose by design -- it is destined for a
    #: prompt, and the frozen spec lists structured constraints as a *future*
    #: extension point, so the Loader must not impose structure on it.
    operating_constraints: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", MappingProxyType(dict(self.sections)))
        object.__setattr__(self, "declared_sections", frozenset(self.declared_sections))

    def declares(self, canonical_section: str) -> bool:
        return canonical_section in self.declared_sections

    def section(self, canonical_section: str) -> str | None:
        return self.sections.get(canonical_section)

    @classmethod
    def empty(cls) -> ProjectConfig:
        """The config of a project whose `config.md` is absent.

        Distinct from a config that exists but declares nothing: that
        distinction is carried by `ProjectContext.config.exists`, so this type
        does not need to model absence itself.
        """
        return cls()


def freeze_sections(sections: Iterable[tuple[str, str]]) -> Mapping[str, str]:
    """Build a read-only section mapping, first occurrence winning.

    First-wins matters: a duplicated heading must not let later content
    silently replace what an earlier consumer already reasoned about.
    """
    collected: dict[str, str] = {}
    for name, body in sections:
        if name not in collected:
            collected[name] = body
    return MappingProxyType(collected)
