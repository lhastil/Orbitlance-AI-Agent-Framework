"""Shared fixtures and in-memory builders for Validation Layer tests.

These builders construct ProjectContext / CoreBundle directly. That is
deliberate: the Project Loader and Core Loader do not exist yet (Phase 2 Task 1
is Validation only), and the Validation Layer's contract is defined against
those models, not against the filesystem. Building them in memory tests the
module's real interface and keeps these tests fast and hermetic.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from runtime.models.core_bundle import CoreBundle
from runtime.models.project_context import (
    ExtensionPoint,
    ProjectContext,
    ProjectDocument,
)
from runtime.validation import framework_spec as spec

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.MULTILINE)


def parse_sections(markdown: str) -> dict[str, str]:
    """Split markdown into {normalised heading: body}.

    Mirrors what the future Project Loader must produce, so tests exercise
    realistic ProjectDocument shapes rather than hand-written section maps.
    """
    sections: dict[str, str] = {}
    matches = list(_HEADING_RE.finditer(markdown))
    for index, match in enumerate(matches):
        title = match.group(2).strip().casefold()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[title] = markdown[start:end].strip()
    return sections


def document(
    name: str, text: str = "content", *, relative_path: str | None = None
) -> ProjectDocument:
    return ProjectDocument(
        name=name,
        relative_path=relative_path or name,
        exists=True,
        raw_text=text,
        sections=parse_sections(text),
    )


def extension_point(
    name: str, documents: Iterable[ProjectDocument] = (), *, present: bool = True
) -> ExtensionPoint:
    return ExtensionPoint(
        name=name,
        present=present,
        documents={d.name: d for d in documents},
    )


VALID_CONFIG = """# Example Project Configuration

## Active Industry Playbook

`core/industry_playbooks/healthcare.md`

## Knowledge Status

Filled in — all 8 documents complete.

## Branding Status

Filled in.

## Integrations Status

CRM, Calendar, Email, Consultation Form, General Integrations configured.

## LLM Provider

- **Primary:** anthropic
- **Model:** claude-sonnet-5
- **Secondary (optional):** none

## Enabled Workflows

- **Discovery** — understand the need
- **Recommendation** — recommend a service
- **Consultation** — book a visit
- **CRM Sync** — record the enquiry
- **Follow-up** — reminders
- **Voice Agent** — phone scheduling

## Operating Constraints

- Never diagnose a condition.
- Escalate suspected emergencies immediately.
"""


VALID_INTEGRATIONS = """# Integrations

## CRM Tool (`core/tools/crm.md`)
Provider: practice management system.

## Calendar Tool (`core/tools/calendar.md`)
Provider: practice management scheduler.

## Email Tool (`core/tools/email.md`)
Provider: Google Workspace.

## Consultation Form Tool (`core/tools/consultation_form.md`)
Provider: intake module.

## General Integrations (`core/tools/integrations.md`)
SMS reminder platform.
"""


def knowledge_documents(
    *, omit: Iterable[str] = (), body: str = "Real business content."
) -> list[ProjectDocument]:
    omitted = set(omit)
    return [
        document(name, f"# {name}\n\n## Overview\n\n{body}\n", relative_path=f"knowledge/{name}")
        for name in spec.REQUIRED_KNOWLEDGE_DOCUMENTS
        if name not in omitted
    ]


def make_project(
    project_id: str = "example_client",
    *,
    knowledge: ExtensionPoint | None = None,
    branding: ExtensionPoint | None = None,
    integrations: ExtensionPoint | None = None,
    config: ProjectDocument | None = None,
    root_exists: bool = True,
) -> ProjectContext:
    return ProjectContext(
        project_id=project_id,
        root_path=f"projects/{project_id}",
        root_exists=root_exists,
        knowledge=knowledge or extension_point("knowledge", knowledge_documents()),
        branding=branding
        or extension_point("branding", [document("brand.md", "# Brand\n\nWarm.\n")]),
        integrations=integrations
        or extension_point("integrations", [document("integrations.md", VALID_INTEGRATIONS)]),
        config=config or document("config.md", VALID_CONFIG),
    )


def make_core(
    *,
    playbooks: Iterable[str] = ("healthcare", "hotel", "restaurant"),
    templates: Mapping[str, str] | None = None,
) -> CoreBundle:
    template_docs = {
        name: document(name, text, relative_path=f"core/templates/{name}")
        for name, text in (templates or {}).items()
    }
    return CoreBundle(
        prompts={
            n: document(n, "# prompt", relative_path=f"core/prompts/{n}")
            for n in spec.REQUIRED_PROMPTS
        },
        guardrails={
            n: document(n, "# guardrail", relative_path=f"core/guardrails/{n}")
            for n in spec.GUARDRAIL_BUNDLE
        },
        workflows={
            f"{n}.md": document(f"{n}.md", "# workflow", relative_path=f"core/workflows/{n}.md")
            for n in spec.CANONICAL_WORKFLOWS
        },
        tool_contracts={
            f"{n}.md": document(f"{n}.md", "# tool", relative_path=f"core/tools/{n}.md")
            for n in spec.TOOL_CONTRACTS
        },
        templates=template_docs,
        playbook_names=frozenset(playbooks),
    )
