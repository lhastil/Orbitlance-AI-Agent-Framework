# Sunrise Dental Clinic — Project Configuration

## Purpose

Project-level configuration for the Sunrise Dental Clinic AI agent, following the Core/Project override contract defined in `docs/project-configuration.md`. This file selects which shared Core resources this project activates — it contains no prompts, guardrails, workflows, or tool contracts of its own.

---

## Active Industry Playbook

`core/industry playbooks/healthcare.md`

Sunrise Dental Clinic is a healthcare provider. The AI agent must follow the Healthcare Industry Playbook's boundary at all times: it may support scheduling, FAQ, and general information, but must never diagnose conditions, recommend treatment, or provide medical judgment.

---

## Knowledge Status

Location: `projects/sunrise_dental_clinic/knowledge/`

Filled in — all 8 knowledge documents completed:
`01_company.md`, `02_services.md`, `03_faq.md`, `04_process.md`, `05_technologies.md`, `06_pricing.md`, `07_portfolio.md`, `08_contact.md`

---

## Branding Status

Location: `projects/sunrise_dental_clinic/branding/`

Filled in — `brand.md` defines brand voice; visual assets (logo, color palette) not yet produced, direction only.

---

## Integrations Status

Location: `projects/sunrise_dental_clinic/integrations/`

Filled in — `integrations.md` documents provider selection for CRM, Calendar, Email, and SMS. No credentials stored in this repository.

---

## Enabled Workflows

From `core/workflows/`:

- **Discovery** — understand what the patient needs (routine care, emergency, cosmetic interest, etc.)
- **Recommendation** — recommend the most appropriate Sunrise Dental service based on discovery
- **Consultation** — book an appointment or consultation (functions as this project's "Consultation Request" — booking a visit, not a sales consultation)
- **CRM Sync** — record patient inquiries and appointment requests in the practice management system
- **Follow-up** — appointment reminders and post-treatment follow-up
- **Voice Agent** — enabled, since phone-based scheduling and after-hours calls are a core need for a dental practice

Not enabled: none of the six workflows were excluded — all apply naturally to this project.

---

## Dependencies

- Core/Project Override Contract (`docs/project-configuration.md`)
- Healthcare Industry Playbook (`core/industry playbooks/healthcare.md`)
- Core Knowledge Templates (`core/templates/`)
- Tools (`core/tools/`)

---

## Notes

This project demonstrates that the Core/Project override contract works end-to-end for a real (if fictional) client. It was built entirely from `core/`'s shared prompts, guardrails, workflows, tools, and templates, without modifying a single file inside `core/`, and does not read from or depend on any other project.
