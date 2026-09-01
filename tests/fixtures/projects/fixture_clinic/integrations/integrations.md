# Integrations — Fixture Clinic

## Purpose

Records which provider fulfils each vendor-agnostic contract in `core/tools/`.
Provider selection only — no credentials, keys or endpoints appear here or
anywhere else in this fixture.

---

## CRM Tool (`core/tools/crm.md`)

**Provider:** an in-memory test double supplied by the integration tests.

---

## Calendar Tool (`core/tools/calendar.md`)

**Provider:** an in-memory test double supplied by the integration tests.

---

## Email Tool (`core/tools/email.md`)

**Provider:** an in-memory test double supplied by the integration tests.

---

## Consultation Form Tool (`core/tools/consultation_form.md`)

**Provider:** an in-memory test double supplied by the integration tests.

---

## General Integrations (`core/tools/integrations.md`)

**Additional connections:** none. This fixture connects to nothing external.

---

## Notes

No tool implementation is registered by default, so the Tool Executor answers
"capability unavailable" for every contract unless a test registers one. That is
the honest state of a fixture that reaches no external system.
