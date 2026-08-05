# Orbitlance Project Configuration

## Purpose

Project-level configuration for deploying the framework for Orbitlance itself, following the Core/Project override contract defined in `docs/project-configuration.md`.

This file is the Config extension point — it does not contain business knowledge itself. It only selects which shared Core resources this project activates and points to where the other three extension points (Knowledge, Branding, Integrations) live.

---

## Responsibilities

- Declare which industry playbook(s) apply to this project
- Point to this project's Knowledge, Branding, and Integrations folders
- Declare which optional workflows are enabled for this project
- Record nothing that belongs in Core — no prompts, guardrails, workflows, or tool contracts are redefined here

---

## Active Industry Playbook(s)

_(placeholder — e.g. none yet; Orbitlance sells to businesses across multiple industries rather than operating within one)_

---

## Knowledge Status

Location: `projects/orbitlance/knowledge/`

_(placeholder — not yet filled in; see `core/templates/` for the 8 required documents)_

---

## Branding Status

Location: `projects/orbitlance/branding/`

_(placeholder — not yet filled in)_

---

## Integrations Status

Location: `projects/orbitlance/integrations/`

_(placeholder — not yet filled in; see `core/tools/` for the contracts each integration must satisfy)_

---

## LLM Provider

- **Primary:** _(placeholder — not yet selected)_
- **Model:** _(placeholder)_
- **Secondary (optional):** _(placeholder)_

---

## Operating Constraints

Additive behavioral limits for this project. These narrow what the agent may do; they never relax `core/guardrails/`.

_(placeholder — none identified yet; Orbitlance operates across industries rather than within one regulated vertical.)_

---

## Enabled Workflows

Which of the six workflows from `core/workflows/` (Discovery, Recommendation, Consultation, CRM Sync, Follow-up, Voice Agent) are active for this project.

_(placeholder)_

---

## Dependencies

- Core/Project Override Contract (`docs/project-configuration.md`)
- Core Knowledge Templates (`core/templates/`)
- Industry Playbooks (`core/industry_playbooks/`)
- Tools (`core/tools/`)

---

## Notes

This file must never contain a prompt, guardrail, workflow, or tool contract of its own — those always come from Core. If something here starts to look like a rule rather than a selection, it belongs in Core or in one of the other three extension points instead.
