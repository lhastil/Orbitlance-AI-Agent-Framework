# Core/Project Override Contract

## Purpose

Defines exactly how a project in `projects/<client>/` relates to `core/` — what it may extend, what it may never touch, and how the framework resolves a resource when a project doesn't provide one itself.

This is the mechanism that makes "one framework, many clients" actually work. Without it, `core/` and `projects/` are just two folders with no defined relationship.

---

## The Six Rules

1. **Core is read-only.** Nothing in `core/` is ever edited to serve one specific client.
2. **Projects may extend Core.** A project adds client-specific content on top of the shared framework.
3. **Projects may override only documented extension points.** Not every part of the framework can be customized per client — only the four listed below.
4. **Missing project resources resolve per extension point.** What a missing resource means depends on *which* extension point is absent — there is no single uniform fallback. Branding and Config fall back to safe Core defaults; Integrations degrades the affected capability; Knowledge fails loudly before activation. The full per-extension-point behavior is defined in [Resolution Order](#resolution-order) below. In no case does the framework silently invent business content to fill a gap.
5. **Core is never modified for a specific client.** If a client needs something Core doesn't support, that need is met through an extension point — never by editing `core/`.
6. **Every project remains isolated from other projects.** A project may only read from `core/` and from itself. It never reads another project's folder.

---

## The Four Extension Points

These are the only parts of the framework a project may override. Everything else in `core/` is shared and fixed across every client.

### 1. Knowledge — `projects/<client>/knowledge/`

Overrides: `core/knowledge/` (the contract) via `core/templates/` (the worksheet).

A project fills in the 8 knowledge templates (Company, Services, FAQ, Process, Technologies, Pricing, Portfolio, Contact) with its own factual business information. This is the highest-volume, most-expected override — every project will have one.

### 2. Branding — `projects/<client>/branding/`

Overrides: tone-of-voice and identity details referenced by `core/prompts/01_core_personality.md` (e.g. brand personality, writing style).

Core Personality itself (the underlying behavioral contract — professional, honest, concise, etc.) is never overridden; only the client-specific *expression* of it (brand voice, visual identity direction) lives here.

**Relationship to `assets/branding/`:** these are two different things. `assets/branding/` at the repo root holds the Orbitlance Framework's *own* branding assets (e.g. for framework-level documentation or presentation material) — it is part of Core and is never client-specific. Each client's own visual identity (logo files, color assets, imagery) belongs under `projects/<client>/branding/` instead, never in the shared root `assets/` folder.

### 3. Integrations — `projects/<client>/integrations/`

Overrides: the concrete provider configuration (credentials, endpoints, provider selection) that fulfills the vendor-agnostic contracts defined in `core/tools/`. There are **five** such contracts: CRM, Calendar, Email, Consultation Form, and General Integrations.

`core/tools/*.md` defines *what* a CRM tool must do. `projects/<client>/integrations/` defines *which* CRM this client actually uses and how to reach it. The contract in Core never changes; only which provider satisfies it changes per project.

**Naming caution:** "Integrations" is used at two different levels and they are not the same thing. This extension point (`projects/<client>/integrations/`) is the umbrella covering provider configuration for **all five** tool contracts. `core/tools/integrations.md` — "General Integrations" — is just **one** of those five, the catch-all for connections the four named contracts don't cover. Configuring the extension point means addressing all five contracts, not only the similarly-named one.

### 4. Config — `projects/<client>/config.md`

Overrides: nothing in Core. This is primarily the **index** that tells the framework which Core resources this project selects and activates. It records:

- Which industry playbook(s) from `core/industry_playbooks/` apply to this project
- Which knowledge set is active
- Which of the five tool contracts have a configured provider
- Which LLM provider and model this project's agent runs on
- Any feature flags or workflow toggles (e.g., is Voice Agent enabled for this client?)
- **Operating Constraints** — industry- or client-specific behavioral limits (see below)

**On Operating Constraints:** Config is otherwise a pure selector, and this one section is the deliberate exception. It exists because industry-specific behavioral rules had nowhere else to live: Playbooks are reference-only and never load at runtime, Knowledge is facts-only, and Core Guardrails are universal and may never be modified per client. Rather than bend any of those three rules, Config gains one tightly-scoped section for this content.

Operating Constraints may only **add** restrictions. They may never relax, weaken, or override `core/guardrails/` — Core's universal guardrails always apply in full, and anything declared here layers strictly on top. A constraint that would loosen a Core guardrail is invalid and must fail validation.

**An Industry Playbook is reference-only.** Selecting one in Config is not the same as overriding it — the project points at the shared playbook; it does not fork or copy its content.

- A playbook is never copied into a project's Knowledge automatically. There is no mechanism, script, or process that does this, and none should ever be built.
- A playbook exists to **guide the human** who is writing that project's Knowledge (extension point 1) — it's reference material for what to consider (common challenges, typical services, terminology, KPIs), not source content to paste in.
- If a client's needs diverge from the shared playbook, that divergence belongs entirely in the client's own Knowledge — never in a client-specific copy of the playbook.

**Selecting more than one playbook is allowed and doesn't require a precedence rule.** A hotel that also runs its own restaurant can select both `hotel.md` and `restaurant.md`. Because playbooks are reference-only (never executed or merged at runtime — see above), there's no runtime conflict to resolve: the human writing that project's Knowledge simply consults every selected playbook and produces one coherent Knowledge base. If two playbooks' example guidance would conflict, neither playbook decides the answer — the project's actual business reality does, and that answer goes into Knowledge, not into a merged or prioritized playbook.

---

## What Is Never an Extension Point

Everything else in `core/` is shared, fixed, and identical across every client. A project cannot override:

- `core/prompts/` — behavioral contracts (personality, mission, conversation rules, guardrails injection, discovery/recommendation/consultation/lead-qualification/fallback/tool-instruction prompts)
- `core/guardrails/` — safety, escalation, and compliance rules
- `core/workflows/` — the step-by-step process logic
- `core/tools/` — the vendor-agnostic tool contracts themselves (as opposed to the per-project configuration that fulfills them)
- `core/templates/` — these are meta-documents (how to fill in Knowledge, Branding, Integrations, and Config), not runtime content a project consumes directly
- `core/industry_playbooks/` — shared per-industry knowledge, selected via Config, never forked per client

If a real client need doesn't fit anywhere above, that is a signal the framework itself needs a new module — not that this rule should be bent for one client (Rule 5).

---

## Resolution Order

When an AI Agent needs a resource, it resolves in this order:

1. Does `projects/<client>/` provide this resource, and is it one of the four documented extension points? If yes, use the project's version.
2. Otherwise, apply that extension point's documented missing-resource behavior, per the table below.

### Missing-resource behavior, per extension point

Rule 4 is **not uniform** — "fall back to Core" is only correct for two of the four extension points. Applying it uniformly would produce unsafe behavior for the other two.

| Extension point | If missing | Why |
|---|---|---|
| **Branding** | Fall back to Core's neutral default voice. | Core Personality already defines a complete, safe behavioral contract. A project without brand voice is under-styled, not incorrect. |
| **Config** | Fall back to documented defaults (no playbook selected; all workflows enabled). | Config only *selects* Core resources. Absent selections have safe, well-defined defaults. |
| **Integrations** | Degrade the affected capability. The agent declines that specific action honestly (per Fallback Responses) and continues serving everything else. | There is no "Core version" of a client's CRM connection to fall back to. Core has no opinion about which calendar this client uses. |
| **Knowledge** | **Fail loudly at project-activation time.** The agent does not go live. | There is no safe Core default for what a business's services or prices are. A silent fallback here would leave the LLM to fill the gap from its own training data — precisely what `core/guardrails/safety.md` forbids ("never invent business information"). An agent that refuses to start is strictly safer than one that confidently invents a client's pricing. |

There is no partial-merge behavior beyond what's defined per extension point above (e.g., Knowledge is filled in per the Template's fields; Config selects rather than merges). A project is never allowed to silently shadow a non-extension-point file — if it isn't Knowledge, Branding, Integrations, or Config, Core's version is the only version, always.

---

## Isolation Guarantee

A project's resolution only ever consults two sources: `core/` and its own `projects/<client>/` folder. It never reads, references, or depends on another `projects/<other-client>/` folder. This means:

- Deleting or modifying one client's project folder can never affect another client's agent.
- Two clients in the same industry each get their own Knowledge, even though they share the same Core and the same industry playbook.

---

## Dependencies

- Architecture (`docs/architecture.md`)
- Knowledge (`core/knowledge/`)
- Templates (`core/templates/`)
- Industry Playbooks (`core/industry_playbooks/`)
- Tools (`core/tools/`)

---

## Notes

This document is itself part of Core — it is the one place the override mechanism is defined, and it should never need a client-specific version. If this contract turns out to be insufficient for a real client, that's a framework-level design discussion, not a one-off exception.
