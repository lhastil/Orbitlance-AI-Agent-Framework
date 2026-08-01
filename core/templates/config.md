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

Name the playbook(s) from `core/industry playbooks/` this project selects. Remember: selecting a playbook is a reference, not a copy — see `docs/project-configuration.md`.

If more than one playbook applies (e.g. a hotel that also runs its own restaurant), note that explicitly — this framework does not yet define precedence rules for multiple simultaneous playbooks, so document your own reasoning here until that's resolved framework-wide.

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

List which tool contracts (CRM, Calendar, Email, other) have a provider configured.

---

## Enabled Workflows

List which workflows from `core/workflows/` are active for this project, and briefly note how each is reinterpreted for this specific business if it isn't a literal sales-consultation context (e.g., "Consultation" workflow maps to booking a stay for a hotel, a reservation for a restaurant, or a freight quote for a logistics company).

---

## Validation Checklist

Before using this template, verify that:

- Every selected industry playbook actually exists in `core/industry playbooks/`.
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
