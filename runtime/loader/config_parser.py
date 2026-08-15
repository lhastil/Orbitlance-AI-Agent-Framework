"""`config.md` text -> `ProjectConfig`.

The single place config Markdown becomes typed data (ADR 0004).

Strictly syntactic. This module reports what the document says and never judges
it: a placeholder value is returned verbatim, an unknown workflow name is
returned as written, and a playbook that does not exist is still reported as
declared. Deciding any of that is the Validation Layer's job, and doing it here
would make the Loader a validator -- which the frozen spec forbids.
"""

from __future__ import annotations

from runtime.loader import config_schema as schema
from runtime.loader import markdown
from runtime.models.project_config import (
    LlmProviderSelection,
    ProjectConfig,
    freeze_sections,
)


def parse_config(text: str) -> ProjectConfig:
    """Parse `config.md` content into typed fields.

    Never raises on unexpected content: absent or unrecognised material yields
    empty fields, which the Validation Layer then reports. The Loader raises
    only when a document cannot be read at all.
    """
    recognised: list[tuple[str, str]] = []
    for parsed_section in markdown.split_sections(text).sections:
        canonical = schema.canonical_section(
            markdown.normalise_heading(parsed_section.heading)
        )
        if canonical is not None:
            recognised.append((canonical, parsed_section.body))

    sections = freeze_sections(recognised)

    return ProjectConfig(
        declared_sections=frozenset(sections),
        sections=sections,
        active_playbooks=_parse_playbooks(sections.get(schema.ACTIVE_INDUSTRY_PLAYBOOK)),
        llm_provider=_parse_provider(sections.get(schema.LLM_PROVIDER)),
        enabled_workflows=_parse_workflows(sections.get(schema.ENABLED_WORKFLOWS)),
        operating_constraints=sections.get(schema.OPERATING_CONSTRAINTS, ""),
    )


def _parse_playbooks(body: str | None) -> tuple[str, ...]:
    """Playbooks named in the section, as declared.

    Prefers `inline code` spans, which is how both the template and the real
    project name a playbook. Falls back to the first token of each bullet so a
    plain list still yields something rather than silently nothing.
    """
    if not body:
        return ()

    named = [span for span in markdown.code_spans(body) if span]
    if not named:
        for item in markdown.list_items(body):
            label = markdown.leading_label(item)
            if label:
                named.append(label.split()[0])

    return _dedupe(named)


def _parse_provider(body: str | None) -> LlmProviderSelection:
    """The declared provider selection.

    A label that is present but empty yields an empty string, not None: the
    caller must be able to tell "the line is missing" from "the line is blank".
    """
    if not body:
        return LlmProviderSelection()

    values = {label.casefold(): value for label, value in markdown.labelled_values(body)}

    def find(prefix: str) -> str | None:
        for label, value in values.items():
            if label.startswith(prefix):
                return value
        return None

    return LlmProviderSelection(
        primary=find(schema.PRIMARY_LABEL),
        model=find(schema.MODEL_LABEL),
        secondary=find(schema.SECONDARY_LABEL),
    )


def _parse_workflows(body: str | None) -> tuple[str, ...]:
    """Workflow labels as declared, never resolved to canonical ids.

    Resolution needs the framework's canonical workflow list, and checking a
    name against it is validation. The Loader reports the label; the Validation
    Layer decides whether it names a real workflow.
    """
    if not body:
        return ()

    labels: list[str] = []
    for item in markdown.list_items(body):
        label = markdown.leading_label(item)
        if label:
            labels.append(label)
    return _dedupe(labels)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    """Order-preserving de-duplication, compared case-insensitively.

    Order is preserved so output is deterministic and reflects the document.
    """
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.casefold()
        if key and key not in seen:
            seen.add(key)
            unique.append(value)
    return tuple(unique)
