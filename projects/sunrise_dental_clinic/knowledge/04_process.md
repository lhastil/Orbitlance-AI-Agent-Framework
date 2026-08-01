# Process — Sunrise Dental Clinic

Each entry follows the Process Overview / Steps / Responsibilities / Escalation structure from `core/templates/process.md`.

---

## New Patient Onboarding

**Category:** Onboarding

**Purpose:** Get a new patient scheduled and prepared for their first visit.

**Trigger:** A new patient contacts the practice (via phone, website, or AI agent) requesting an appointment.

**Steps:**
1. Collect patient name, contact info, and reason for visit.
2. Ask whether the patient has dental insurance and collect provider/plan info if so.
3. Offer available first-visit appointment times.
4. Send new-patient intake forms to complete before arrival.
5. Confirm the appointment 24 hours in advance.

**Customer Responsibilities:** Provide accurate contact/insurance information and complete intake forms before arrival.

**Business Responsibilities:** Verify insurance coverage before the visit and prepare the patient's chart.

**Required Information:** Full name, date of birth, contact info, insurance details (if applicable), reason for visit.

**Decision Points:** If the patient describes a dental emergency during intake, redirect to the Emergency Walk-in Process instead.

**Expected Outcomes:** Patient arrives for their first visit with forms completed and insurance pre-verified.

**Escalation Conditions:** Complex insurance situations (e.g., out-of-network plans) should be handed to front-desk staff.

**Related Services:** General Checkups & Cleanings

---

## Appointment Scheduling

**Category:** Customer Support

**Purpose:** Book, reschedule, or cancel a routine appointment.

**Trigger:** An existing patient requests to schedule, move, or cancel an appointment.

**Steps:**
1. Look up the patient's existing record.
2. Confirm the reason for the visit.
3. Offer available appointment slots matching the patient's preferred days/times.
4. Confirm the appointment and send a reminder closer to the date.

**Customer Responsibilities:** Provide at least 24 hours' notice to reschedule or cancel when possible.

**Business Responsibilities:** Send appointment reminders and hold the slot until confirmed.

**Decision Points:** If no suitable slot exists within the patient's timeframe and the reason is urgent, redirect to the Emergency Walk-in Process.

**Expected Outcomes:** Patient has a confirmed appointment time.

**Escalation Conditions:** Repeated no-shows or scheduling disputes should be handled by front-desk staff.

---

## Emergency Walk-in Process

**Category:** Customer Support

**Purpose:** Get a patient with urgent dental pain or injury seen as quickly as possible.

**Trigger:** A patient reports significant pain, trauma, or a dental emergency.

**Steps:**
1. Ask about the nature and severity of the issue.
2. Provide immediate first-aid guidance if applicable (e.g., for a knocked-out tooth).
3. Offer the next available same-week emergency slot.
4. Flag the case as urgent for the front desk.

**Business Responsibilities:** Hold daily emergency slots and prioritize urgent cases.

**Decision Points:** Severe trauma or uncontrolled bleeding should be escalated immediately to a human and, if life-threatening, the patient should be directed to call emergency services.

**Expected Outcomes:** Patient is seen the same day or within the same week, with pain addressed as quickly as possible.

**Escalation Conditions:** Any sign of a medical emergency (not just dental) should be escalated immediately and the patient advised to seek emergency medical care.

**Related Services:** Emergency Dental Care

---

## Insurance Claim Submission

**Category:** Billing

**Purpose:** Submit a claim to the patient's insurance provider after treatment.

**Trigger:** A covered treatment has been completed.

**Steps:**
1. Confirm treatment codes with the treating dentist.
2. Submit the claim to the patient's insurance provider.
3. Notify the patient of any remaining balance once the claim is processed.

**Business Responsibilities:** Submit claims promptly and follow up on denials or delays.

**Expected Outcomes:** Claim is processed and the patient is billed only for their actual remaining balance.

**Escalation Conditions:** Denied claims or billing disputes should always go to front-desk/billing staff, never resolved by the AI directly.

---

## Notes

This file was populated from `core/templates/process.md` as part of onboarding the Sunrise Dental Clinic project. All content above is fictional, created for framework demonstration purposes.
