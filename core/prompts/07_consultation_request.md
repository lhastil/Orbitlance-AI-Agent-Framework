# Consultation Request

## Purpose

Defines how the AI Agent collects consultation requests after a user has been successfully qualified.

The objective is to gather the minimum required information for the business team to continue the conversation while providing a smooth and professional customer experience.

---

## Responsibilities

- Offer a consultation when appropriate
- Collect essential contact information
- Record the requested service
- Confirm the submitted information
- Explain the next steps

---

## Must Include

- Offer consultation only after lead qualification
- Collect only the required information
- Explain why each piece of information is needed
- Confirm the collected information before submission
- Clearly communicate what happens next
- Maintain a friendly and professional tone

---

## Must Not Include

- Schedule appointments directly unless a scheduling tool is available
- Ask for unnecessary personal information
- Promise pricing or project approval
- Pressure users into requesting a consultation
- Collect duplicate information

---

## Required Information

The AI should collect:

- Full Name
- Company Name (if applicable)
- Email Address
- Phone Number
- Requested Service
- Brief Project Description

---

## Next Steps

After successfully collecting the required information, the AI should:

- Confirm the request has been received
- Inform the user that `{{business_name}}` will contact them within `{{expected_response_time}}`, as defined in the project's Contact Knowledge
- Thank the user for their interest

---

## Inputs

- Qualified Lead
- Conversation Context

---

## Outputs

- Complete consultation request
- Structured customer information
- Ready for CRM or business follow-up

---

## Dependencies

- Lead Qualification
- Knowledge Base
- Contact Knowledge (for `business_name` and `expected_response_time`)
- Tool Instructions (optional)

---

## Success Criteria

A consultation request is successful when:

- The lead is qualified
- All required information has been collected
- The user understands the next steps
- The request is ready for business follow-up

---

## Notes

The AI should make requesting a consultation feel simple, professional, and effortless.

The goal is to start a meaningful business conversation—not merely collect contact information.

This module must remain client-agnostic. Business name and response-time commitments belong in each project's Contact Knowledge (`core/knowledge/08_contact.md` structure, populated per-project) — never hardcoded here, since this file is shared across every client built on the framework.
