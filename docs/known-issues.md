# Known Architectural Issues

## Purpose

Tracks confirmed architectural issues in the framework that have been identified but deliberately not yet fixed, so they aren't lost or rediscovered from scratch later.

Issues are recorded here as they're found. Per current direction, all open framework-level issues will be fixed together in one pass once the runtime design (`docs/runtime-architecture.md`, once written) is complete — fixing them piecemeal mid-design risks having the runtime design chase a moving target.

---

## Open Issues

### 1. Circular dependency: `core/workflows/recommendation.md` ↔ `core/workflows/consultation.md`

**Severity:** High
**Found during:** Runtime architecture design (Dependency Graph analysis)

`core/workflows/recommendation.md`'s Dependencies list includes "Consultation Request." `core/workflows/consultation.md`'s Dependencies list includes "Recommendation Workflow." This is a genuine cycle — Recommendation happens before Consultation in the actual business flow, so Recommendation should not depend on it.

**Root cause:** "Dependencies" was used inconsistently across these two files — sometimes meaning "requires as input," sometimes meaning "produces output consumed by."

**Recommendation:** Remove "Consultation Request" from Recommendation's Dependencies list. The relationship already exists correctly, one-directionally, in Consultation's own Dependencies list (which correctly lists Recommendation Workflow as something it depends on).

---

### 2. Mutual dependency triangle: `core/guardrails/safety.md` ↔ `escalation.md` ↔ `compliance.md`

**Severity:** Medium
**Found during:** Runtime architecture design (Dependency Graph analysis)

All three guardrail files list each other as Dependencies (Safety → Escalation, Compliance; Escalation → Safety, Compliance; Compliance → Safety, Escalation). Unlike Issue 1, this isn't necessarily a documentation mistake — these three concepts are genuinely inseparable in practice.

**Recommendation:** Decide whether to (a) leave the mutual references as-is in the docs, since the runtime resolves this by treating `core/guardrails/` as one atomic bundle rather than three independently-ordered modules (see `docs/runtime-architecture.md` once written), or (b) restructure the docs' Dependencies sections to describe this relationship without a literal cycle (e.g., a shared "Guardrails Bundle" concept each file points to instead of pointing at each other). Not urgent — the runtime-level resolution already sidesteps it — but worth a deliberate decision rather than leaving it as an unexamined cycle.

---

### 3. Rule 4 ("missing project resources fall back to Core") doesn't hold uniformly across the four extension points

**Severity:** High
**Found during:** Runtime architecture design (Module Responsibilities — Resolver)

`docs/project-configuration.md`'s Rule 4 states missing project resources fall back to Core's version. This works for Branding (fall back to a neutral default voice) and Config (fall back to sensible defaults). It does not work for:

- **Integrations** — there's no safe "Core version" of a CRM connection. Missing Integrations should mean the agent gracefully declines that specific capability, not "falls back" to anything Core provides.
- **Knowledge** — there's no safe Core default for what a business's services/pricing/etc. actually are. A literal fallback here risks the LLM quietly filling gaps from its own training data, which directly violates the Safety Guardrails' "never invent business information" rule. Missing Knowledge should fail loudly at project-activation time, before the agent goes live — not silently degrade at conversation time.

**Recommendation:** Qualify Rule 4 per extension point rather than stating it as one uniform rule.

---

### 4. Config Template has no field for LLM provider/model selection

**Severity:** Medium
**Found during:** Runtime architecture design (Provider Registry)

`core/templates/config.md` tracks Knowledge/Branding/Integrations status and Enabled Workflows, but nothing records which LLM provider or model a project uses — despite "support multiple LLM providers" being a stated scalability goal since the original architecture review.

**Recommendation:** Add an "LLM Provider" field to the Config Template and to `docs/project-configuration.md`'s description of the Config extension point.

---

### 5. No runtime-accessible home for industry-specific escalation/behavioral rules, given Playbooks are human-only and Knowledge is facts-only

**Severity:** High
**Found during:** Runtime Specification (Guardrail Engine module spec)

Each Industry Playbook has an "Escalation Considerations" section (e.g. Healthcare's "never diagnose," "direct medical emergencies to call emergency services"). But the framework establishes three constraints that, together, leave this content with nowhere to actually live at runtime:

1. Playbooks are reference-only and must never be loaded into the runtime automatically (per the QA-03 fix) — they only guide the human writing a project's Knowledge.
2. Knowledge stores facts, not behavior/conversation logic (per `docs/development-guidelines.md`'s Knowledge Guidelines) — "never diagnose" isn't a fact about the business, so it doesn't belong in Knowledge either.
3. Core Guardrails are universal and must never be modified per client or per industry (Rule 5) — so a Healthcare-specific rule can't simply be added to `core/guardrails/`.

The result: an industry-specific behavioral rule a human read in a Playbook has no correct, defined place to actually end up where the runtime can enforce it. The Runtime Specification's Guardrail Engine module is scoped to enforce only the universal Core guardrails bundle as a result — it does not (and per current framework rules, cannot) enforce industry-specific escalation rules like "never diagnose" today.

**Recommendation:** This needs a framework-level decision, not a runtime workaround: likely a new, explicitly-scoped extension point or Config field allowing a project to declare industry-informed behavioral additions in its own words (distinct from Knowledge's facts-only scope and from Core's universal-only scope). Not resolved now, per current direction.

---

## Notes

This file is itself part of Core and should never accumulate silently — issues here are either promoted to a fix (and removed from this list) or explicitly deferred with a reason, not forgotten.
