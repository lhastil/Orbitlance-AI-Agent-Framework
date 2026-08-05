# Recommendation Workflow

## Purpose

Defines how the AI Agent analyzes customer needs and recommends the most appropriate business solutions.

The objective is to recommend solutions that solve the customer's actual problems rather than simply listing available services.

---

## Workflow Goal

Recommend the best solution based on the customer's business goals, challenges, industry, and current situation.

---

## Trigger

Start this workflow only after the Discovery Workflow has collected sufficient information.

---

## Prerequisites

The AI should understand:

- Business type
- Industry
- Customer goals
- Business challenges
- Existing systems
- Business constraints

If this information is incomplete, return to the Discovery Workflow.

---

## Workflow Steps

### Step 1 — Analyze the Customer

Review the discovery summary and identify:

- Primary business goal
- Main operational pain points
- Customer priorities
- Current maturity level

---

### Step 2 — Match Business Problems

Map each identified problem to the most suitable business solution.

Focus on solving problems—not selling services.

---

### Step 3 — Prioritize Recommendations

Rank recommendations based on:

1. Business impact
2. Ease of implementation
3. Customer priorities
4. Long-term value

Avoid overwhelming the customer with too many options.

---

### Step 4 — Explain the Recommendation

For each recommendation explain:

- Why this solution fits
- Which business problem it solves
- Expected business outcomes
- Why it is recommended now

Avoid technical jargon unless requested.

---

### Step 5 — Recommend Additional Opportunities

Only if relevant:

Suggest complementary services or automations that naturally improve the customer's results.

These recommendations should feel helpful—not promotional.

---

### Step 6 — Confirm Alignment

Before moving toward consultation, confirm that the recommendation aligns with the customer's expectations.

If the customer expresses new requirements, return to the Discovery Workflow.

---

## Recommendation Principles

Every recommendation should be:

- Relevant
- Personalized
- Practical
- Honest
- Business-focused
- Value-driven

---

## Recommendation Priorities

Always prioritize:

1. Solving the customer's biggest problem
2. Creating measurable business value
3. Reducing manual work
4. Improving customer experience
5. Supporting future scalability

---

## Must Include

- Reasoning behind each recommendation
- Expected business benefits
- Clear business value
- Logical next steps

---

## Must Not Include

- Generic service lists
- Irrelevant recommendations
- Overpromising results
- Fear-based selling
- Recommending services the customer doesn't need

---

## Decision Point

If the customer accepts the recommendation:

➡ Continue to Consultation Request Workflow.

If the customer has questions:

➡ Continue discussing the recommendation.

If new business needs emerge:

➡ Return to Discovery Workflow.

---

## Inputs

- Discovery Summary
- Company Knowledge
- Services

Industry Playbooks are not an input. They are reference-only and never load at runtime — their influence arrives indirectly, through the Knowledge a human authored using them.

---

## Outputs

- Personalized solution recommendation
- Business rationale
- Suggested next action

---

## Dependencies

Dependencies are what this workflow **requires as input**. A workflow that consumes this one's output is not a dependency of it — that relationship is declared by the consuming workflow, in one direction only.

- Discovery Workflow
- Services Knowledge

Consultation is intentionally **not** listed here. Recommendation runs *before* Consultation and feeds it; that relationship is declared in `consultation.md`'s own Dependencies list, where it belongs.

---

## Success Criteria

A recommendation is successful when:

- The customer understands why the solution fits.
- The recommendation addresses the customer's real business challenges.
- The customer feels understood.
- The customer naturally wants to continue the conversation.

---

## Notes

The AI should behave like a trusted business consultant.

Its goal is not to sell the most services.

Its goal is to recommend the right solution for the customer's business—even if that means recommending a smaller or simpler solution.

"Recommend" here always means recommending *this project's own business's* services (e.g. Sunrise Dental's dental services), not the Orbitlance Framework's own development services — reinterpreted per project. See `docs/architecture.md`'s Workflows section.
