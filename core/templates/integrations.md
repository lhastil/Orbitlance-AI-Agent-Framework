# Integrations Template

## Purpose

Provides a standardized template for documenting which concrete provider fulfills each vendor-agnostic tool contract defined in `core/tools/`, for a specific project — the Integrations extension point defined in `docs/project-configuration.md`.

The objective is to record provider selection only. Credentials, API keys, and endpoints never belong in this document or anywhere in this repository.

---

## Responsibilities

- Record which provider satisfies each `core/tools/` contract for this project
- Keep provider selection separate from the tool contract itself
- Ensure no credentials or secrets are ever committed here

---

## Template Goal

Let an AI Agent (and any human reading this project) know *which* real-world system it's actually talking to for each tool contract, without exposing how to authenticate to it.

---

## CRM Tool

Contract: `core/tools/crm.md`

### Provider

### Configuration Notes

---

## Calendar Tool

Contract: `core/tools/calendar.md`

### Provider

### Configuration Notes

---

## Email Tool

Contract: `core/tools/email.md`

### Provider

### Configuration Notes

---

## Consultation Form Tool

Contract: `core/tools/consultation_form.md`

### Provider

Where completed consultation requests are actually delivered and stored (e.g. the CRM, a dedicated form backend, an email destination).

### Configuration Notes

---

## General Integrations

Contract: `core/tools/integrations.md`

This is the catch-all contract for connections not covered by the four named tools above — it is **not** the same thing as the Integrations extension point (this whole file). See `docs/project-configuration.md`.

### Additional Connections

List any other providers this project connects to that aren't covered by CRM/Calendar/Email/Consultation Form above.

---

## Validation Checklist

Before using this template, verify that:

- Every listed provider maps back to a real `core/tools/` contract.
- All five `core/tools/` contracts have been considered — CRM, Calendar, Email, Consultation Form, and General Integrations. A contract this project genuinely doesn't need may be left unconfigured, but that should be a deliberate choice, not an oversight (an unconfigured contract degrades that capability at runtime; see `docs/project-configuration.md`).
- No credentials, API keys, or endpoint secrets appear anywhere in this document.
- Providers are specific enough to be actionable (e.g., "Google Calendar," not just "a calendar").

---

## Related Templates

- Company Template

---

## Notes

Actual credentials belong in the runtime environment's secret storage, never in this repository. This document only records *which* provider fulfills each Core tool contract for this project.
