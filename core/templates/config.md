# Config Template

## Purpose

Provides a standardized template for a project's `config.md` — the Config extension point defined in `docs/project-configuration.md`. This is the index that tells the framework which Core resources this project selects and activates. It never contains prompts, guardrails, workflows, or tool contracts of its own.

---

## Responsibilities

- Declare which industry playbook(s) apply to this project
- Point to this project's Knowledge, Branding, and Integrations folders and summarize their completion status
- Declare which optional workflows are enabled for this project
- Record nothing that belongs in Core

---

## Template Goal

Give anyone (human or AI) a single place to see exactly what this project has configured, without duplicating any of the actual content that lives in Knowledge, Branding, or Integrations.

---

## Active Industry Playbook(s)

Name the playbook(s) from `core/industry_playbooks/` this project selects. Remember: selecting a playbook is a reference, not a copy — see `docs/project-configuration.md`.

If more than one playbook applies (e.g. a hotel that also runs its own restaurant), list all of them. No precedence rule is needed: because playbooks are reference-only and never merged at runtime, the human writing this project's Knowledge consults every selected playbook and produces one coherent Knowledge base. See `docs/project-configuration.md`.

---

## Knowledge Status

Location: `projects/<client>/knowledge/`

List which of the 8 knowledge documents are complete (Company, Services, FAQ, Process, Technologies, Pricing, Portfolio, Contact).

---

## Branding Status

Location: `projects/<client>/branding/`

State whether brand voice and visual identity direction are complete.

---

## Integrations Status

Location: `projects/<client>/integrations/`

State which of the five `core/tools/` contracts have a provider configured: CRM, Calendar, Email, Consultation Form, General Integrations. An unconfigured contract degrades that capability at runtime, so note any left unconfigured deliberately.

---

## LLM Provider

Which provider and model this project's agent runs on, and optionally a secondary provider for failover.

The named provider must be registered in the runtime's Provider Registry — a project configured for an unregistered provider fails validation before activation, not at first request.

- **Primary:**
- **Model:**
- **Secondary (optional):**

---

## Enabled Workflows

List which workflows from `core/workflows/` are active for this project, and briefly note how each is reinterpreted for this specific business if it isn't a literal sales-consultation context (e.g., "Consultation" workflow maps to booking a stay for a hotel, a reservation for a restaurant, or a freight quote for a logistics company).

The six available workflows are: Discovery, Recommendation, Consultation, CRM Sync, Follow-up, Voice Agent.

---

## Operating Constraints

Industry- or client-specific behavioral limits this agent must observe, written in this project's own words.

**Why this section exists:** Industry Playbooks are reference-only and never load at runtime, and Knowledge holds facts rather than behavior — so an industry-specific rule a human read in a Playbook (e.g. a healthcare agent must never diagnose) needs a home the runtime can actually read. This is that home.

**Strict scope — these constraints may only ADD restrictions:**

- They may narrow what the agent is allowed to do beyond what Core already forbids.
- They may **never** relax, weaken, or override anything in `core/guardrails/`. Core's universal guardrails always apply in full; anything here is layered strictly on top.
- They are behavioral limits only — not facts (those belong in Knowledge), not tone (that belongs in Branding), not process steps (those belong in Core's workflows).

Leave empty if this project has no constraints beyond Core's universal guardrails.

---

## Validation Checklist

Before using this template, verify that:

- Every selected industry playbook actually exists in `core/industry_playbooks/`.
- Nothing here restates content that belongs in Knowledge, Branding, or Integrations — this file only points to and summarizes them.
- No prompt, guardrail, workflow, or tool contract is redefined here.

---

## Related Templates

- Company Template
- Branding Template
- Integrations Template

---

## Notes

If something in this file starts to look like a rule rather than a selection, it belongs in Core or in one of the other three extension points instead.
