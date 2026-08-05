"""Frozen framework facts the validator checks against.

Every value here is transcribed from the v1.0-architecture-freeze framework —
not invented. Each constant cites its source so a reader can verify it without
trusting this file.

This module exists so no rule hardcodes framework structure inline. When the
framework changes (a new knowledge document, a seventh workflow), exactly one
file changes and every rule follows — Open/Closed at the data level.

There are deliberately NO project names here. Rules must work for any project.
"""

from __future__ import annotations

from typing import Final

# --- Knowledge -------------------------------------------------------------
# Source: core/knowledge/ (8 contracts) and core/templates/ (8 worksheets).
# All 8 are currently required; docs/runtime-specification.md notes that
# splitting these into critical vs. optional is a future refinement, so until
# the framework says otherwise a missing document fails closed.
REQUIRED_KNOWLEDGE_DOCUMENTS: Final[tuple[str, ...]] = (
    "01_company.md",
    "02_services.md",
    "03_faq.md",
    "04_process.md",
    "05_technologies.md",
    "06_pricing.md",
    "07_portfolio.md",
    "08_contact.md",
)

# Maps a knowledge document to the template that defines its required shape.
# Source: docs/architecture.md — "A Template is always a strict superset of its
# matching Knowledge contract."
KNOWLEDGE_TEMPLATE_BY_DOCUMENT: Final[dict[str, str]] = {
    "01_company.md": "company.md",
    "02_services.md": "services.md",
    "03_faq.md": "faq.md",
    "04_process.md": "process.md",
    "05_technologies.md": "technologies.md",
    "06_pricing.md": "pricing.md",
    "07_portfolio.md": "portfolio.md",
    "08_contact.md": "contact.md",
}

# --- Workflows -------------------------------------------------------------
# Source: docs/architecture.md workflow table + core/workflows/ (exactly six).
# Lead Qualification is deliberately prompt-only and is NOT a workflow.
CANONICAL_WORKFLOWS: Final[tuple[str, ...]] = (
    "discovery",
    "recommendation",
    "consultation",
    "crm_sync",
    "follow_up",
    "voice_agent",
)

# Accepted human spellings seen in config files, mapped to canonical ids.
WORKFLOW_ALIASES: Final[dict[str, str]] = {
    "discovery": "discovery",
    "recommendation": "recommendation",
    "consultation": "consultation",
    "consultation request": "consultation",
    "crm sync": "crm_sync",
    "crm_sync": "crm_sync",
    "crm synchronization": "crm_sync",
    "crm synchronisation": "crm_sync",
    "follow up": "follow_up",
    "follow-up": "follow_up",
    "follow_up": "follow_up",
    "voice agent": "voice_agent",
    "voice_agent": "voice_agent",
}

# --- Tools -----------------------------------------------------------------
# Source: core/tools/ (five contracts) and core/templates/integrations.md.
TOOL_CONTRACTS: Final[tuple[str, ...]] = (
    "crm",
    "calendar",
    "email",
    "consultation_form",
    "integrations",
)

TOOL_CONTRACT_LABELS: Final[dict[str, str]] = {
    "crm": "CRM Tool",
    "calendar": "Calendar Tool",
    "email": "Email Tool",
    "consultation_form": "Consultation Form Tool",
    "integrations": "General Integrations",
}

# --- Guardrails ------------------------------------------------------------
# Source: core/guardrails/ — loaded as one atomic bundle, no internal ordering.
GUARDRAIL_BUNDLE: Final[tuple[str, ...]] = (
    "safety.md",
    "escalation.md",
    "compliance.md",
)

# --- Prompts ---------------------------------------------------------------
# Source: core/prompts/ (ten modules).
REQUIRED_PROMPTS: Final[tuple[str, ...]] = (
    "01_core_personality.md",
    "02_mission.md",
    "03_conversation_rules.md",
    "04_discovery_engine.md",
    "05_recommendation_engine.md",
    "06_lead_qualification.md",
    "07_consultation_request.md",
    "08_guardrails.md",
    "09_fallback_responses.md",
    "10_tool_instructions.md",
)

# --- Config ----------------------------------------------------------------
# Source: core/templates/config.md — the content sections a project's config
# must declare. Template-only scaffolding sections (Purpose, Responsibilities,
# Template Goal, Validation Checklist, Related Templates, Notes) are excluded
# because they describe the template itself, not a project's configuration.
REQUIRED_CONFIG_SECTIONS: Final[tuple[str, ...]] = (
    "Active Industry Playbook",
    "Knowledge Status",
    "Branding Status",
    "Integrations Status",
    "LLM Provider",
    "Enabled Workflows",
    "Operating Constraints",
)

# Heading spellings that resolve to a canonical required section.
#
# Resolution is an exact lookup on the normalised heading -- deliberately NOT
# prefix or fuzzy matching. An earlier revision matched prefixes in both
# directions, which meant a heading of "Knowledge" satisfied the requirement for
# "Knowledge Status" and bound the wrong body to every downstream check.
#
# Every alias below is a spelling that actually occurs in the frozen framework
# (core/templates/config.md writes the plural form; the projects write the
# singular). Adding an entry is a deliberate act, not a heuristic side effect.
CONFIG_SECTION_ALIASES: Final[dict[str, str]] = {
    "active industry playbook": "Active Industry Playbook",
    "active industry playbook(s)": "Active Industry Playbook",
    "knowledge status": "Knowledge Status",
    "branding status": "Branding Status",
    "integrations status": "Integrations Status",
    "llm provider": "LLM Provider",
    "enabled workflows": "Enabled Workflows",
    "operating constraints": "Operating Constraints",
}


def canonical_config_section(heading: str) -> str | None:
    """Resolve a config.md heading to its canonical section name.

    Returns None for headings that are not one of the required sections, so an
    unrecognised heading is simply ignored rather than absorbing a requirement.
    """
    return CONFIG_SECTION_ALIASES.get(heading.strip().lstrip("#").strip().casefold())

# --- Extension points ------------------------------------------------------
# Source: docs/project-configuration.md — the four documented extension points.
KNOWLEDGE_DIR: Final[str] = "knowledge"
BRANDING_DIR: Final[str] = "branding"
INTEGRATIONS_DIR: Final[str] = "integrations"
CONFIG_FILE: Final[str] = "config.md"

# --- Naming ----------------------------------------------------------------
# Source: docs/development-guidelines.md — lowercase, underscores, no spaces
# or hyphens; explicitly extended to project folder names under projects/.
PROJECT_ID_PATTERN: Final[str] = r"^[a-z0-9]+(_[a-z0-9]+)*$"

# --- Placeholders ----------------------------------------------------------
# Markers used throughout the framework's own scaffolding to mean "not filled
# in yet". A required field still carrying one of these is not configured.
PLACEHOLDER_MARKERS: Final[tuple[str, ...]] = (
    "_(placeholder",
    "(placeholder",
    "_(not yet",
    "(not yet",
    "tbd",
    "todo",
    "<fill in>",
    "xxx",
)

# --- Operating Constraints -------------------------------------------------
# Source: docs/project-configuration.md — constraints are ADDITIVE ONLY and may
# never relax, weaken or override core/guardrails/. These phrases indicate an
# attempt to loosen rather than narrow, which must be rejected.
RELAXING_PHRASES: Final[tuple[str, ...]] = (
    "ignore core",
    "ignore the core",
    "ignore guardrail",
    "override core",
    "override the core",
    "override guardrail",
    "bypass core",
    "bypass guardrail",
    "disable guardrail",
    "disable the guardrail",
    "skip guardrail",
    "skip the guardrail",
    "relax core",
    "relax the guardrail",
    "without escalating",
    "no escalation",
    "need not escalate",
    "does not need to escalate",
    "exempt from core",
    "exempt from guardrail",
    "notwithstanding core",
    "may diagnose",
    "is allowed to diagnose",
)

# --- Secrets ---------------------------------------------------------------
# Source: core/templates/integrations.md — "No credentials, API keys, or
# endpoint secrets appear anywhere in this document."
SECRET_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"(?i)\bsk-[A-Za-z0-9]{16,}\b", "OpenAI-style secret key"),
    (r"(?i)\bsk-ant-[A-Za-z0-9\-_]{16,}\b", "Anthropic-style secret key"),
    (r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b", "GitHub token"),
    (r"(?i)\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"(?i)\bxox[abprs]-[A-Za-z0-9\-]{10,}\b", "Slack token"),
    (r"(?i)\b(api[_\- ]?key|secret|password|passwd|client[_\- ]?secret)\b\s*[:=]\s*\S{8,}",
     "inline credential assignment"),
    (r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
)

# --- Client-specific content in Core --------------------------------------
# Source: docs/runtime-specification.md Validation Layer — "no client-specific
# content pattern appears in what should be Core-shared files (defence-in-depth
# against a repeat of the earlier hardcoded-SLA class of bug)".
CLIENT_SPECIFIC_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"(?i)\bwithin\s+\d+\s*(hour|hours|business day|business days|day|days)\b",
     "hardcoded response-time commitment (SLA)"),
    (r"\+?\d[\d\s().-]{8,}\d", "hardcoded phone number"),
    (r"(?i)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "hardcoded email address"),
    (r"(?<![A-Za-z0-9])\$\s?\d[\d,]*(\.\d{2})?", "hardcoded price"),
)

# Core files legitimately allowed to discuss the framework's own identity.
# Everything else in core/ must stay client-agnostic.
CLIENT_PATTERN_EXEMPT_FILES: Final[frozenset[str]] = frozenset()
