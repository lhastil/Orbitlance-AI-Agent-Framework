# Consultation Workflow

## Purpose

Defines the standard process for transitioning a qualified prospect into a consultation request.

The objective is to collect the right information, set clear expectations, and ensure a smooth handoff to the business team.

---

## Workflow Goal

Convert a qualified prospect into a consultation request without creating unnecessary friction.

---

## Trigger

Start this workflow when:

- The customer accepts a recommendation.
- The customer requests a consultation.
- The AI determines that a consultation is the appropriate next step.

---

## Prerequisites

Before starting, the AI should know:

- Customer name (if available)
- Business type
- Requested service
- Business goals
- Primary challenges

If important information is missing, collect it naturally before continuing.

---

## Workflow Steps

### Step 1 — Confirm Interest

Confirm that the customer would like to continue with a consultation.

---

### Step 2 — Collect Required Information

Collect only the information required by the business.

Typical fields include:

- Full Name
- Company Name
- Email Address
- Phone Number
- Requested Service
- Brief Project Description

Avoid asking for unnecessary information.

---

### Step 3 — Validate Information

Check that all required information has been provided.

If anything is missing or unclear, politely ask for clarification.

---

### Step 4 — Confirm the Submission

Summarize the collected information and ask the customer to confirm its accuracy before submission.

---

### Step 5 — Explain the Next Steps

Clearly explain what will happen next.

For example:

- The request has been received.
- The business team will review the information.
- The customer will be contacted according to the company's consultation policy.

Do not promise timelines unless they are defined in the client's knowledge base.

---

### Step 6 — Close Professionally

Thank the customer and end the conversation in a friendly and professional manner.

Leave the customer with confidence that the process is moving forward.

---

## Conversation Principles

The consultation process should be:

- Simple
- Professional
- Efficient
- Transparent
- Customer-focused

---

## Must Include

- Clear explanation of why information is requested
- Data validation before submission
- Confirmation before completion
- Professional closing message

---

## Must Not Include

- Request unnecessary personal information
- Schedule appointments without the appropriate tool
- Promise project approval
- Promise pricing
- Pressure the customer into continuing

---

## Decision Points

If the customer confirms the information:

➡ Submit the consultation request.

If the customer wants to modify information:

➡ Update the information and confirm again.

If the customer decides not to continue:

➡ Respect the decision and end the workflow professionally.

---

## Inputs

- Recommendation Summary
- Customer Information
- Company Knowledge

---

## Outputs

- Complete consultation request
- Qualified lead
- Structured customer information
- Ready for CRM or business follow-up

---

## Dependencies

- Discovery Workflow
- Recommendation Workflow
- Lead Qualification
- Contact Knowledge
- Tool Instructions

---

## Success Criteria

A consultation workflow is successful when:

- The customer feels understood.
- All required information has been collected.
- The information is accurate.
- The customer understands the next steps.
- The business team receives a complete, qualified consultation request.

---

## Notes

The AI should never rush the customer into requesting a consultation.

The objective is to make the transition feel natural, professional, and helpful.

A successful consultation request is built on trust—not persuasion.

"Consultation" here is generic and must be reinterpreted per project — it means booking a stay for a hotel, a table for a restaurant, an appointment for a healthcare provider, or a freight quote for a logistics company, not necessarily a sales call. See `docs/architecture.md`'s Workflows section.
