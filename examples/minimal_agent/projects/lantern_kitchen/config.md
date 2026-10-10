# Lantern Street Kitchen — Project Configuration

## Purpose

The project behind `examples/minimal_agent`. Lantern Street Kitchen is a
fictional neighbourhood restaurant; every fact in this directory is invented.

---

## Active Industry Playbook

`core/industry_playbooks/restaurant.md`

Authoring reference only. Playbooks never load at runtime.

---

## Knowledge Status

Location: `knowledge/`

Filled in — all 8 knowledge documents present and populated.

---

## Branding Status

Location: `branding/`

Filled in — `brand.md` defines the voice.

---

## Integrations Status

Location: `integrations/`

Filled in — `integrations.md` covers all five `core/tools/` contracts. Tools
are never invoked: the runtime does not yet produce tool requests.

---

## LLM Provider

- **Primary:** google
- **Model:** gemini-3.6-flash
- **Secondary (optional):** none

The identity the framework's Gemini adapter binds to. The Provider Registry
refuses to route this project to an adapter bound to any other provider or
model.

---

## Operating Constraints

- **Never quote a price that does not appear in Knowledge.**
- **Never confirm a reservation.** The agent collects the details and says the
  restaurant will confirm.
- **Never give allergy guarantees.** Refer allergy questions to the kitchen.

---

## Enabled Workflows

- **Discovery** — understand what the guest is looking for
- **Recommendation** — suggest dishes or a seating option
- **Consultation** — take a table reservation request

Not enabled: CRM Sync, Follow-up, Voice Agent.
