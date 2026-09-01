# Fixture Clinic — Project Configuration

## Purpose

A deliberately small, fully valid project used **only** by the Runtime Engine's
integration tests. It is not a client, and it is not deployed. It exists because
neither real project under `projects/` can pass the Validation Layer — both
declare a placeholder LLM provider — and §14.10 makes a passed validation a hard
precondition for accepting any request. Without a valid project there is nothing
to run the pipeline against.

It is kept under `tests/fixtures/` rather than `projects/` so that production
projects stay untouched and nothing here is mistaken for a real configuration.

---

## Active Industry Playbook

`core/industry_playbooks/healthcare.md`

Selected as authoring reference only. Playbooks never load at runtime.

---

## Knowledge Status

Location: `tests/fixtures/projects/fixture_clinic/knowledge/`

Filled in — all 8 knowledge documents present and populated:
`01_company.md`, `02_services.md`, `03_faq.md`, `04_process.md`,
`05_technologies.md`, `06_pricing.md`, `07_portfolio.md`, `08_contact.md`

---

## Branding Status

Location: `tests/fixtures/projects/fixture_clinic/branding/`

Filled in — `brand.md` defines the voice this fixture uses.

---

## Integrations Status

Location: `tests/fixtures/projects/fixture_clinic/integrations/`

Filled in — `integrations.md` names a provider for all five `core/tools/`
contracts. No credentials appear anywhere in this fixture.

---

## LLM Provider

- **Primary:** fixture_provider
- **Model:** fixture-model-1
- **Secondary (optional):** none

This names an offline test double, not a vendor. The integration tests register
a conforming fake adapter under exactly this identity, so the fixture validates
genuinely against the real Validation Layer while the whole pipeline runs with
no credential, no network and no vendor SDK.

---

## Operating Constraints

Additive behavioural limits. These narrow what the agent may do; they never
relax `core/guardrails/`.

- **Never diagnose a condition.** The agent may describe services and general
  information, but must never assess symptoms.
- **Never quote a price that does not appear in Knowledge.**

---

## Enabled Workflows

From `core/workflows/`:

- **Discovery** — understand what the caller needs
- **Consultation** — book an appointment

Not enabled: Recommendation, CRM Sync, Follow-up, Voice Agent. This fixture
deliberately enables a subset, so the Prompt Assembler's project-scope
enforcement is exercised by real data rather than only by a constructed case.

---

## Dependencies

- Core/Project Override Contract (`docs/project-configuration.md`)
- Core Knowledge Templates (`core/templates/`)
- Tools (`core/tools/`)

---

## Notes

Every value here is invented for testing. Nothing in this directory describes a
real business, and nothing in it is authoritative for the framework.
