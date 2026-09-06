# Discovery Workflow

## Purpose

Defines the standard process for discovering a customer's needs through structured conversation.

The objective is to understand the customer's business, challenges, goals, and requirements before recommending any solution.

---

## Workflow Goal

Identify the customer's real problem rather than responding only to the initial request.

---

## Trigger

Start this workflow when:

- A new conversation begins
- A customer requests information
- A customer expresses a business challenge
- The customer's needs are not yet clear

---

## Workflow Steps

### Step 1 — Understand the Business

Identify:

- Industry
- Business type
- Business size
- Customer role

---

### Step 2 — Understand the Goal

Identify:

- What the customer wants to achieve
- Expected outcome
- Success criteria

---

### Step 3 — Identify Pain Points

Discover:

- Current problems
- Manual processes
- Repetitive tasks
- Customer communication challenges
- Operational bottlenecks

---

### Step 4 — Understand Existing Systems

Determine whether the customer already uses:

- CRM
- Website
- AI tools
- Automation platforms
- Internal software

---

### Step 5 — Determine Constraints

Identify:

- Budget considerations
- Timeline
- Team size
- Technical limitations

---

### Step 6 — Summarize Findings

Before moving forward, internally summarize:

- Business type
- Primary goal
- Main challenges
- Existing systems
- Constraints

---

## Decision Point

If sufficient information has been collected:

➡ Continue to Recommendation Workflow.

Otherwise:

➡ Continue asking relevant discovery questions.

---

## Routing Phrases

**This section is the authoritative source of the runtime's deterministic routing vocabulary for this workflow.** The Workflow Router reads the phrases below from this document; it never defines them in code. Adding, removing or rewording a phrase here changes routing behaviour, and is a deliberate Core-content change.

**What this vocabulary is, stated precisely.** The Decision Point above — *"If sufficient information has been collected"* — remains the authoritative conceptual rule, and it is a judgement about accumulated information. The runtime cannot evaluate it: nothing extracts collected data from a conversation, so there is nothing to measure sufficiency against. The phrases below are therefore a **message-shaped readiness signal**: the deterministic routing representation available under the current runtime contract. **They are not a machine-readable evaluation of accumulated collected data, and must not be presented as one.** The agent still follows the Decision Point; this vocabulary only tells the deterministic router when a customer has plainly signalled they are ready to move on.

Matching is case-insensitive, and a matched phrase advances the conversation. A message matching nothing keeps the conversation in this workflow — the conservative default.

Each subsection heading below names the workflow the phrases route to.

### recommendation

- what do you recommend
- what would you recommend
- what do you suggest
- what would you suggest
- which option is best
- which do you recommend
- show me the options
- what are my options
- I am ready to move forward
- I'm ready to move forward
- ready for a recommendation
- that is everything
- that's everything
- that is all the information
- that's all the information

---

## Best Practices

- Ask one question at a time.
- Avoid overwhelming the customer.
- Adapt questions based on previous answers.
- Keep the conversation natural.
- Focus on business outcomes rather than technology.

---

## Inputs

- User messages
- Conversation context

---

## Outputs

- Business profile
- Customer goals
- Pain points
- Constraints
- Recommendation-ready context

---

## Dependencies

Dependencies are what this workflow **requires as input at runtime**.

- Conversation Rules
- Knowledge Base

Industry Playbooks are intentionally **not** listed. Playbooks are reference-only — they inform the human writing this project's Knowledge, and never load at runtime (see `docs/project-configuration.md`). Their influence reaches this workflow indirectly, through the Knowledge the human produced.

---

## Success Criteria

Discovery is complete when the AI clearly understands:

- Who the customer is
- What problem they have
- Why it matters
- What outcome they expect

---

## Notes

The AI should never recommend a solution before understanding the customer's business needs.
