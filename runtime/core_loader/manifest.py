"""What Core must contain, and which directories are loaded how.

Every value is **transcribed** from the frozen framework read against the actual
contents of `core/` — not invented. Each constant cites its source so a reader
can verify it without trusting this file.

**Why these are declared here rather than imported.** §1.7 states that the Core
Loader "is a root module — nothing else must run before it, and it depends on no
other runtime module." `runtime/validation/framework_spec.py` holds overlapping
constants, but importing it would make Module 1 depend on Module 13 and invert
the direction the whole architecture rests on: validation checks Core, so Core
cannot be built on validation.

That duplication is the subject of ADR 0002 (`docs/adr/`, "framework constants
are transcribed") and issue V-5, which record that these constants should
eventually be *derived* from Core rather than transcribed alongside it. This
module is the beginning of that: it is the first place the required set is
asserted against the real filesystem, so a transcription that drifts from
`core/` now fails a test instead of going unnoticed. Making the Validation Layer
read from `CoreBundle` instead of its own copy is the remaining half, and is not
in this module's scope.
"""

from __future__ import annotations

from typing import Final

# --- directories ------------------------------------------------------------
#: Loaded with full content. Source: §1.2, plus `core/knowledge/` which
#: `CoreBundle.knowledge_contracts` exists to hold and which the Resolver reads
#: to derive the required Knowledge document set.
PROMPTS_DIR: Final[str] = "prompts"
GUARDRAILS_DIR: Final[str] = "guardrails"
WORKFLOWS_DIR: Final[str] = "workflows"
TOOLS_DIR: Final[str] = "tools"
KNOWLEDGE_DIR: Final[str] = "knowledge"

#: Recorded by presence only, never by content. See `TEMPLATES_ARE_PRESENCE_ONLY`.
TEMPLATES_DIR: Final[str] = "templates"

#: Names only, never opened. §1.3 and §1.10.
PLAYBOOKS_DIR: Final[str] = "industry_playbooks"

#: The repository-relative prefix every Core document records as its provenance.
#: The Prompt Assembler already relies on this exact shape: it treats a path
#: starting with `core/` as repository-relative and anything else as
#: project-relative, so `core/prompts/02_mission.md` is a contract, not a
#: cosmetic choice.
CORE_PATH_PREFIX: Final[str] = "core/"


# --- required files (§1.10) --------------------------------------------------
#: Source: `core/prompts/` — ten modules. The frozen assembly order renders only
#: five of them and `CoreBundle.prompts` is keyed by filename, so all ten are
#: required to exist even though the Prompt Assembler deliberately omits several
#: (see `runtime/assembler/core_slots.py` and PA-3). A required file is about
#: Core being complete, not about what any one turn renders.
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

#: Source: the `CoreBundle` data-model row — "guardrailsBundle (atomic
#: Safety+Escalation+Compliance)" — and known-issues.md #2's resolution. Atomic:
#: a Core missing any one of the three is not a partially-guarded runtime, it is
#: a runtime that must not start.
REQUIRED_GUARDRAILS: Final[tuple[str, ...]] = (
    "safety.md",
    "escalation.md",
    "compliance.md",
)

#: Source: docs/architecture.md's workflow table and `core/workflows/` — exactly
#: six. Lead Qualification is deliberately prompt-only and is NOT a workflow.
REQUIRED_WORKFLOWS: Final[tuple[str, ...]] = (
    "discovery.md",
    "recommendation.md",
    "consultation.md",
    "crm_sync.md",
    "follow_up.md",
    "voice_agent.md",
)

#: Source: `core/tools/` — five contracts, matching the five the Tool Executor
#: spec names (CRM, Calendar, Email, Consultation Form, General Integrations).
REQUIRED_TOOL_CONTRACTS: Final[tuple[str, ...]] = (
    "crm.md",
    "calendar.md",
    "email.md",
    "consultation_form.md",
    "integrations.md",
)

#: Directory -> required file names, for the four §1.10 names explicitly.
#: `core/knowledge/` is loaded but not listed: §1.10 does not require it, and
#: the Validation Layer already reports a project's missing Knowledge documents
#: against its own required set. Requiring it here would fail the runtime for a
#: condition the framework treats as a project-level warning.
REQUIRED_FILES: Final[dict[str, tuple[str, ...]]] = {
    PROMPTS_DIR: REQUIRED_PROMPTS,
    GUARDRAILS_DIR: REQUIRED_GUARDRAILS,
    WORKFLOWS_DIR: REQUIRED_WORKFLOWS,
    TOOLS_DIR: REQUIRED_TOOL_CONTRACTS,
}


# --- the templates decision --------------------------------------------------
#: **`core/templates/` is recorded by presence, never by content.**
#:
#: §1.3 says the Core Loader must "Never load `core/templates/` (meta-documents,
#: not runtime content)". The frozen `CoreBundle` nevertheless carries a
#: `templates` field and a `template(name)` accessor, and the frozen Validation
#: Layer rule `knowledge.template_available` calls it — checking only
#: `template.exists`, never reading a byte of the body.
#:
#: Loading templates fully would contradict §1.3. Not loading them at all would
#: make that rule emit a false KNOW_TEMPLATE_UNAVAILABLE warning for every
#: Knowledge document in every project, permanently — a defect caused by this
#: module and reported against the project.
#:
#: Both are avoided the way the architecture already reconciles the same tension
#: for playbooks: record that the document exists, never what it says.
#: `raw_text` is empty and `sections` is empty, so no template text can reach a
#: prompt, `all_documents` scans see nothing to scan, and §1.3's stated concern —
#: meta-documents becoming runtime content — is satisfied literally.
#:
#: Flagged for the system owner as the one interpretive decision in this module.
TEMPLATES_ARE_PRESENCE_ONLY: Final[bool] = True
