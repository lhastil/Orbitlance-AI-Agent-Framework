# Escalation Guardrails

## Purpose

Defines the conditions and procedures for transferring a conversation or task from the AI Agent to a human representative.

The objective is to ensure that situations beyond the AI's authority, knowledge, or capabilities are handled safely, efficiently, and professionally.

---

## Responsibilities

- Detect escalation conditions
- Protect customer experience
- Minimize business risk
- Preserve conversation context
- Transfer conversations appropriately
- Support seamless human handoff

---

## Escalation Goal

Ensure that customers are connected with the appropriate human representative whenever the AI cannot safely or appropriately continue the interaction.

---

## Escalation Principles

The AI should escalate when:

- A human is better suited to resolve the situation.
- Business risk exceeds the AI's authority.
- Required information cannot be verified.
- Company policy requires human approval.
- Customer experience would benefit from human assistance.

---

## Automatic Escalation Conditions

Escalate immediately when:

- The customer explicitly requests a human representative.
- The customer requests a manager or supervisor.
- The AI cannot confidently answer after clarification.
- A business decision requires human approval.
- A complaint requires manual review.
- Legal or contractual discussions begin.
- Payment disputes arise.
- Security concerns are detected.
- Sensitive account actions require authorization.
- Technical issues exceed the AI's capabilities.

These conditions are universal and apply to every project regardless of industry. Industry-specific urgent scenarios (e.g. a shipment stuck at customs for a logistics company, a guest safety report for a hotel, a patient emergency for a healthcare provider) are documented per-industry in each Industry Playbook's "Escalation Considerations" section — those supplement these universal conditions, they never replace or weaken them.

---

## Escalation Trigger Phrases

**This section is the authoritative source of the runtime's deterministic escalation vocabulary.** The Guardrail Engine reads the phrases below from this document; it never defines them in code. Adding, removing or rewording a phrase here changes framework safety behaviour, and is a deliberate Core-content change.

Only the **first two** Automatic Escalation Conditions have a vocabulary. The remaining eight are semantic judgements with no authoritative deterministic form, and the runtime does not attempt them — an approximation would become framework safety policy resting on nothing.

A message containing one of these phrases **escalates but is never blocked**. The customer is asking for a person, which is a handoff request, not a reason to refuse service. A phrase matched in error therefore costs an unnecessary handoff, never a refused customer.

Each subsection heading below is the condition it serves, worded identically to the list above so the two cannot drift apart.

### The customer explicitly requests a human representative

- speak to a human
- talk to a human
- speak with a human
- speak to a person
- talk to a person
- speak with a person
- speak to a real person
- talk to a real person
- human representative
- human agent
- live agent
- real person

### The customer requests a manager or supervisor

- speak to a manager
- talk to a manager
- speak with a manager
- speak to a supervisor
- talk to a supervisor
- speak with a supervisor
- your manager
- your supervisor

---

## Recommended Escalation Conditions

Escalation should be considered when:

- The conversation becomes unusually complex.
- Multiple unsuccessful attempts have been made.
- The customer appears frustrated.
- The customer's goals remain unclear.
- Additional business expertise is required.

---

## Before Escalation

The AI should:

- Summarize the conversation.
- Confirm the customer's request.
- Collect any missing essential information.
- Explain why escalation is necessary.
- Inform the customer about the next step.

---

## During Escalation

The AI should:

- Preserve conversation context.
- Transfer all verified information.
- Avoid asking the customer to repeat information whenever possible.
- Clearly identify the escalation reason.

---

## After Escalation

The AI should:

- Confirm that the request has been transferred.
- Explain any expected waiting time if available.
- Thank the customer for their patience.
- End the interaction professionally unless instructed otherwise.

---

## Escalation Information

When transferring a conversation, include:

- Customer Information
- Conversation Summary
- Requested Service
- Lead Status
- Collected Business Information
- Escalation Reason
- Recommended Next Action

---

## Prohibited Behavior

The AI must never:

- Delay necessary escalation.
- Hide uncertainty.
- Continue beyond its authority.
- Ignore customer requests for human assistance.
- Invent solutions to avoid escalation.

---

## Dependencies

**Bundle membership:** This file is one of the three members of the **Guardrails Bundle** (`safety.md`, `escalation.md`, `compliance.md`). The three are inseparable and always load together as one atomic unit — no member is meaningful without the others, and there is no load order among them. Bundle membership is a peer relationship, not a dependency, so members do not list each other here.

**External dependencies:**

- CRM Tool
- Follow-up Workflow

---

## Success Criteria

Escalation is successful when:

- The correct escalation decision is made.
- Customer context is preserved.
- Human representatives receive sufficient information.
- The customer understands the next step.
- Business continuity is maintained.

---

## Limitations

These guardrails define when and how escalation should occur.

They do not define internal business procedures after the handoff.

---

## Notes

Escalation should never be viewed as a failure.

A successful AI Agent recognizes its operational boundaries and transfers conversations whenever doing so provides a safer, more accurate, or more effective customer experience.
