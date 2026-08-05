# Integrations — Sunrise Dental Clinic

## Purpose

Records which concrete providers fulfill each vendor-agnostic tool contract defined in `core/tools/` for this project. Contains provider selection only — no credentials, API keys, or secrets are ever stored in this repository.

---

## CRM Tool (`core/tools/crm.md`)

**Provider:** Practice management software's built-in patient CRM (e.g., a Dentrix/Open Dental-style system)

**Notes:** Patient records, appointment history, and insurance information all live here. The AI agent reads/writes through this system's API rather than a separate general-purpose CRM.

---

## Calendar Tool (`core/tools/calendar.md`)

**Provider:** Practice management software's built-in scheduling calendar

**Notes:** Appointment availability, booking, and rescheduling all go through the same system as the CRM, since dental practice software typically combines both.

---

## Email Tool (`core/tools/email.md`)

**Provider:** Google Workspace (Gmail)

**Notes:** Used for appointment confirmations, new-patient intake forms, and follow-up communication.

---

## Consultation Form Tool (`core/tools/consultation_form.md`)

**Provider:** Practice management software's patient intake/appointment-request module, fed by the website booking widget.

**Notes:** For this project, a "consultation request" is an appointment request (see `config.md`'s workflow interpretation). Completed requests land directly in the practice management system alongside the patient record, rather than in a separate forms backend — the same system already serving as this project's CRM and Calendar.

---

## General Integrations (`core/tools/integrations.md`)

**Additional connections:**
- SMS reminder platform (for the Patient Communication & Reminder System documented in `knowledge/05_technologies.md`)
- Website booking widget, embedded on the public website

---

## Notes

Actual API keys, credentials, and endpoint URLs are never committed to this repository — they belong in the runtime environment's secret storage, not in `projects/sunrise_dental_clinic/`. This file only documents *which* provider is used, consistent with the vendor-agnostic contracts in `core/tools/`.
