# Lead Qualification

## Purpose

Defines how the AI Agent evaluates whether a user is a qualified lead before initiating a consultation request or handing the conversation over to the business.

The objective is to collect only the information necessary to determine whether the user's needs align with the company's services.

---

## Responsibilities

- Determine whether the user is a qualified lead
- Identify the user's business needs
- Verify service alignment
- Collect essential qualification information
- Decide whether to proceed to Consultation Request

---

## Must Include

- Qualify before collecting contact information
- Keep qualification natural and conversational
- Collect only relevant information
- Focus on business needs rather than sales
- Respect the user's time
- Continue only when sufficient information has been collected

---

## Must Not Include

- Qualify users too early
- Ask unnecessary qualification questions
- Pressure users into booking a consultation
- Reject users without explanation
- Collect sensitive information unless required

---

## Qualification Criteria

The AI should determine:

- What service is the user interested in?
- What problem are they trying to solve?
- Is the request aligned with the company's services?
- Is enough information available to proceed?
- Is a consultation appropriate?

---

## Inputs

- Discovery Summary
- Recommendation
- Conversation Context
- Knowledge Base

---

## Outputs

- Qualified Lead
- Not Qualified
- More Information Required

---

## Dependencies

- Discovery Engine
- Recommendation Engine
- Knowledge Base

---

## Success Criteria

Lead qualification is complete when the AI can confidently determine:

- Whether the user is a potential customer
- Which service best matches their needs
- Whether a consultation should be offered
- Whether additional information is required

---

## Notes

The purpose of qualification is not to filter people out.

Its purpose is to ensure that users receive the most appropriate next step while helping the business focus on meaningful opportunities.

Reinterpreted per project — "qualifying a lead" means qualifying *that project's own* customers (e.g., whether a caller's dental issue matches Sunrise Dental's services), not qualifying prospects for the Orbitlance Framework itself. See `docs/architecture.md`'s Workflows section.
