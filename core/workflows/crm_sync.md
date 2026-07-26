# CRM Synchronization Workflow

## Purpose

Defines the standard process for synchronizing customer information, conversation outcomes, and business insights with the company's CRM system.

The objective is to ensure that every qualified interaction is accurately recorded and made available for future sales, support, and follow-up activities.

---

## Workflow Goal

Transform conversation data into structured CRM records that are complete, accurate, and actionable.

---

## Trigger

Start this workflow when:

- A consultation request is submitted
- A lead becomes qualified
- Important customer information is collected
- A conversation reaches a meaningful business outcome

---

## Prerequisites

The AI should have collected:

- Customer information
- Business information
- Conversation summary
- Requested service
- Qualification status

If required information is missing, return to the appropriate workflow.

---

## Workflow Steps

### Step 1 — Prepare Customer Data

Collect and organize all relevant customer information into a structured format.

---

### Step 2 — Validate Data

Verify that required fields are complete and consistent before synchronization.

---

### Step 3 — Create or Update CRM Record

Determine whether to:

- Create a new contact
- Update an existing contact
- Create a new company
- Associate the contact with an existing company

---

### Step 4 — Record Conversation Summary

Store a concise summary including:

- Customer goals
- Business challenges
- Recommended solution
- Conversation outcome

---

### Step 5 — Record Lead Status

Assign the appropriate status.

Examples:

- New Lead
- Qualified Lead
- Consultation Requested
- Follow-up Required
- Closed
- Disqualified

---

### Step 6 — Trigger Next Actions

If applicable:

- Notify the sales team
- Create follow-up tasks
- Send confirmation emails
- Trigger automations
- Schedule future follow-up

---

## CRM Data Structure

Typical information includes:

### Contact Information

- Name
- Email
- Phone

### Company Information

- Company Name
- Industry
- Business Size

### Opportunity Information

- Requested Service
- Business Goals
- Pain Points
- Qualification Level

### Conversation Summary

### Internal Notes

---

## Validation Rules

Before synchronization:

- Required fields completed
- Email format valid
- Phone number validated (if possible)
- Duplicate records checked
- Customer confirmation received

---

## Must Include

- Accurate customer information
- Structured business information
- Conversation summary
- Lead status
- Timestamp of interaction

---

## Must Not Include

- Unverified assumptions
- Sensitive internal reasoning
- Duplicate CRM records
- Incomplete customer profiles

---

## Decision Points

If synchronization succeeds:

➡ Trigger Follow-up Workflow.

If synchronization fails:

➡ Log the error and retry according to business rules.

If customer information is incomplete:

➡ Return to the relevant workflow to collect missing information.

---

## Inputs

- Consultation Workflow
- Discovery Summary
- Recommendation Summary

---

## Outputs

- CRM Contact
- CRM Company
- Lead Record
- Conversation Summary
- Follow-up Task

---

## Dependencies

- Consultation Workflow
- Lead Qualification
- Tool Instructions
- CRM Integration

---

## Success Criteria

Synchronization is successful when:

- Customer information is complete.
- CRM records are accurate.
- No duplicate records are created.
- The business team has all necessary context.
- Follow-up can begin immediately.

---

## Notes

The AI should treat the CRM as the single source of truth for customer information.

Only verified information should be synchronized.

The synchronization process should be reliable, consistent, and transparent.
