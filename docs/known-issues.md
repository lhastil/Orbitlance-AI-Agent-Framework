# Known Architectural Issues

## Purpose

Tracks confirmed architectural issues in the framework — those identified, those resolved, and how. Resolved entries are retained rather than deleted so the reasoning behind each decision stays discoverable.

**Status: all confirmed blockers resolved during the Architecture Freeze Sprint.** No open blockers remain.

---

## Resolution Summary

| ID | Issue | Severity | Status |
|---|---|---|---|
| KI-1 | Circular dependency: `recommendation.md` ↔ `consultation.md` | High | ✅ Resolved |
| KI-2 | Mutual dependency triangle across `core/guardrails/` | Medium | ✅ Resolved |
| KI-3 | Rule 4 fallback-to-Core not uniformly valid | High | ✅ Resolved |
| KI-4 | Config Template had no LLM provider field | Medium | ✅ Resolved |
| KI-5 | No runtime home for industry-specific behavioral rules | High | ✅ Resolved |
| FDR-1 | `development-guidelines.md` asserted a folder rename that never happened | Critical | ✅ Resolved |
| FDR-2 | `architecture.md` listed a non-existent workflow, omitted three real ones | High | ✅ Resolved |
| FDR-4 | "Integrations" named both the extension point and one of its members | Medium | ✅ Resolved |
| FDR-5 | Consultation Form Tool omitted from Integrations Template and all enumerations | High | ✅ Resolved |
| FDR-6 | `known-issues.md` referenced a non-existent document | Medium | ✅ Resolved |
| FS-1 | Workflows declared a runtime dependency on reference-only Playbooks | High | ✅ Resolved |
| FS-2 | Config Template contained a stale multi-playbook precedence claim | Low | ✅ Resolved |
| FS-3 | Stale counts and omissions in README and `projects/orbitlance/config.md` | Low | ✅ Resolved |

*(FDR-3 was the same defect as KI-3 and is tracked under KI-3.)*

---

## KI-1 — Circular dependency: `recommendation.md` ↔ `consultation.md` ✅ Resolved

**Was:** `core/workflows/recommendation.md` listed "Consultation Request" as a dependency while `core/workflows/consultation.md` listed "Recommendation Workflow" — a genuine cycle. Root cause: "Dependencies" was used to mean both "requires as input" and "produces output consumed by."

**Fixed by:** Removing "Consultation Request" from Recommendation's Dependencies, and adding an explicit definition at the top of that section: dependencies are what a workflow *requires as input*; a workflow that consumes this one's output declares that relationship itself, one-directionally.

**Why sufficient:** The cycle is gone, and the ambiguity that caused it is now defined in-place rather than left to interpretation, so the same mistake can't recur silently. The real Recommendation→Consultation ordering is preserved — it remains declared in `consultation.md`, where it belongs.

**Verified:** `recommendation.md` no longer references Consultation; `consultation.md` unchanged and still correctly declares its inputs.

---

## KI-2 — Mutual dependency triangle across `core/guardrails/` ✅ Resolved

**Was:** `safety.md`, `escalation.md`, and `compliance.md` each listed the other two as Dependencies — a three-way cycle.

**Fixed by:** Option (b) from the original recommendation. Each file now declares **Guardrails Bundle membership** — an explicitly-named peer relationship — and lists only its genuine external dependencies. Members no longer point at each other.

**Why sufficient:** This removes the literal cycle at the documentation level while preserving the architectural truth that the three are inseparable. It also matches what the runtime already specifies (Core Loader treats `core/guardrails/` as one atomic unit with no internal load order), so docs and runtime now describe the same thing.

**Verified:** No guardrail file lists another guardrail file as a dependency. All three retain their original responsibilities unchanged.

---

## KI-3 — Rule 4 fallback-to-Core not uniformly valid ✅ Resolved

**Was:** `docs/project-configuration.md` stated Rule 4 as one uniform rule ("missing project resources fall back to Core"), while `docs/runtime-specification.md`'s Resolver specified differentiated per-extension-point behavior. Two authoritative documents contradicted each other, and an engineer reading either alone would build a different Resolver.

**Fixed by:** Rewriting Rule 4 to state that resolution is per extension point, and adding a **missing-resource behavior table** to the Resolution Order section covering all four: Branding → Core default voice; Config → documented defaults; Integrations → capability degradation; Knowledge → fail loudly at activation. The runtime spec's footnote was updated to reference the now-aligned framework rule instead of asserting a contradiction.

**Why sufficient:** There is now exactly one authoritative statement of this behavior, in the framework doc, and the runtime spec points at it rather than restating it. The unsafe case (Knowledge silently falling back, letting the LLM invent business facts) is explicitly forbidden with its safety rationale attached.

**Verified:** Both documents describe identical behavior; no remaining reference in the runtime spec claims a divergence.

---

## KI-4 — Config Template had no LLM provider field ✅ Resolved

**Was:** Multiple-LLM-provider support was a stated goal, but nothing in Config recorded which provider or model a project uses — leaving the Provider Registry with nothing to read.

**Fixed by:** Adding an **LLM Provider** section (primary, model, optional secondary) to `core/templates/config.md`, listing it in `docs/project-configuration.md`'s Config description, adding it to `ResolvedContext`, and adding a Validation Layer rule that a project's declared provider must be registered — failing before activation rather than at first request.

**Why sufficient:** The Provider Registry now has a defined input, and misconfiguration is caught at validation time rather than mid-conversation. Both existing projects were updated with the new section.

**Verified:** Template, framework doc, runtime spec, and both project configs all carry the field consistently.

---

## KI-5 — No runtime home for industry-specific behavioral rules ✅ Resolved

**Was:** Industry-specific rules (e.g. healthcare's "never diagnose") had nowhere to live that the runtime could read. Three framework rules boxed the content out: Playbooks are reference-only and never load at runtime; Knowledge is facts-only; Core Guardrails are universal and may never be modified per client.

**Fixed by:** Adding a tightly-scoped **Operating Constraints** section to the Config extension point. Constraints are **additive only** — they may narrow what an agent may do, but may never relax, weaken, or override anything in `core/guardrails/`; Core always wins on conflict. The Guardrail Engine now enforces Core's bundle *plus* the project's constraints, and the Validation Layer rejects any constraint attempting to loosen a Core guardrail.

**Why this is not a redesign:** None of the three boxing-in rules were bent — Playbooks stay reference-only, Knowledge stays facts-only, Core Guardrails stay universal and unmodified. Config was already an extension point; it gains one bounded section. This also formalizes what the one real project had already done spontaneously: `sunrise_dental_clinic/config.md` was *already* carrying "must never diagnose conditions" in prose, which is strong evidence Config is the natural home rather than an invented one.

**Acknowledged trade-off:** This does modestly widen Config's responsibility from pure selector to selector-plus-constraints. That was done deliberately under the "may change responsibilities where required to resolve a confirmed issue" allowance, because every alternative required breaking a frozen rule. The scope is explicitly bounded in both the template and the framework doc to prevent Config becoming a general dumping ground.

**Verified:** Guardrail Engine purpose, non-responsibilities, validation rules and test scenarios all updated; both project configs carry the section; Sunrise Dental's previously-prose constraint is now a structured, enforceable declaration.

---

## FDR-1 — Documentation asserted a fix that never happened ✅ Resolved

**Was:** `docs/development-guidelines.md` claimed `core/industry playbooks/` had already been renamed to comply with the lowercase-underscore convention. It had not — the folder still contained a space, making the doc's claim factually false in the one place that defines naming rules.

**Fixed by:** Actually performing the rename via `git mv` to `core/industry_playbooks/`, then updating all 15 references across 9 files.

**Why sufficient:** Documentation and filesystem now agree. The rename was chosen over correcting the claim because the convention itself is sound and was already documented as binding — bringing reality into line preserves the rule rather than carving an exception.

**Verified:** Zero references to the old name remain; all 7 playbook files preserved through the rename; the guidelines claim is now true.

---

## FDR-2 — `architecture.md` misdescribed the workflow set ✅ Resolved

**Was:** The canonical Module Overview listed "Consultation Request, Lead Qualification, CRM Sync, Voice Call Flow" — naming a Lead Qualification workflow that doesn't exist, using a wrong name for Voice Agent, and omitting Discovery, Recommendation, and Follow-up entirely.

**Fixed by:** Replacing the example list with a complete table of all six real workflows and their filenames, explicitly marked as the complete set rather than a sample. Also added an explanation of why **Lead Qualification is deliberately prompt-only**: it's a continuous judgment applied *within* other workflows, not a process with its own step sequence, so modelling it as a workflow would produce an empty shell.

**Why sufficient:** The Module Overview now matches `core/workflows/`, the runtime spec's repeated "6 workflows," and the real project's Enabled Workflows list. The Lead Qualification question that prompted the finding is answered explicitly rather than left for each engineer to guess.

**Verified:** Table matches directory listing exactly.

---

## FDR-4 — "Integrations" naming collision ✅ Resolved

**Was:** "Integrations" named both the extension point (`projects/<client>/integrations/`) and one of the five member contracts it configures (`core/tools/integrations.md`), making scope ambiguous.

**Fixed by:** Retaining both names (renaming files would have rippled widely for modest benefit) but adding an explicit **naming caution** in `docs/project-configuration.md` stating the two levels are different things, and clarifying in the Integrations Template that "General Integrations" is one member contract, not the umbrella.

**Why sufficient:** The ambiguity was that a reader couldn't tell whether the extension point covers all contracts or only the same-named one. That question is now answered directly at both places a reader would encounter it.

**Verified:** Extension point description and template both state the distinction.

---

## FDR-5 — Consultation Form Tool omitted everywhere ✅ Resolved

**Was:** `core/tools/consultation_form.md` is a fully-specified contract that the Consultation workflow depends on, yet it appeared in no enumeration — not the Integrations Template, not `project-configuration.md`, not the runtime spec's Tool Executor, and not the one real project's integrations file. Corroborated across four documents plus a real project, making it systemic rather than a one-off.

**Fixed by:** Adding a Consultation Form Tool section to `core/templates/integrations.md`; correcting all enumerations to name all five contracts; adding a validation-checklist item requiring all five be considered; and configuring it in `projects/sunrise_dental_clinic/integrations/integrations.md`.

**Why sufficient:** Every path by which a project gets configured now surfaces the contract, so a client's consultation submissions can no longer end up with no defined destination.

**Verified:** All five contracts enumerated consistently in template, framework doc, runtime spec, and the real project.

---

## FDR-6 — Dead cross-references ✅ Resolved

**Was:** This file twice referenced a document named *runtime-architecture.md* (under `docs/`), which was never created; the document that actually exists is `docs/runtime-specification.md`.

*(The old name is written without path formatting above so automated link checks don't flag this historical note as a broken reference.)*

**Fixed by:** Correcting both references.

**Verified:** Zero references to the non-existent filename remain repository-wide.

---

## FS-1 — Workflows declared a runtime dependency on reference-only Playbooks ✅ Resolved

*Surfaced during the Freeze Sprint while fixing KI-1.*

**Was:** `core/workflows/discovery.md` and `core/workflows/recommendation.md` both listed "Industry Playbooks" under Dependencies. This directly contradicts the frozen reference-only rule — a runtime Dependencies entry implies the workflow loads playbook content, which the framework explicitly forbids and the Core Loader is specified never to do.

**Fixed by:** Removing the entry from both files and replacing it with an explicit note that playbooks influence the workflow *indirectly*, through the Knowledge a human authored using them.

**Why sufficient:** Dependency declarations now describe only genuine runtime inputs, so the dependency graph is consistent with the reference-only rule. Nothing about how playbooks are actually used changed.

**Verified:** No workflow declares a playbook dependency; the two edited files retain their original responsibilities.

---

## FS-2 — Stale multi-playbook precedence claim ✅ Resolved

*Surfaced during the Freeze Sprint.*

**Was:** `core/templates/config.md` told authors "this framework does not yet define precedence rules for multiple simultaneous playbooks... document your own reasoning until that's resolved." That question was already resolved — `project-configuration.md` establishes that no precedence rule is needed, because reference-only playbooks are never merged at runtime.

**Fixed by:** Replacing the stale instruction with the resolved rule.

**Verified:** Template and framework doc now agree.

---

## FS-3 — Stale counts and omissions in README and `orbitlance/config.md` ✅ Resolved

*Surfaced during the Freeze Sprint.*

**Was:** `projects/orbitlance/config.md` referenced "the 7 required documents" (there are 8). `README.md`'s structure tree omitted three of the five `docs/` files and the entire `sunrise_dental_clinic` project, and described playbooks as "layered on top of the base agent" — language implying the runtime layering the reference-only rule forbids.

**Fixed by:** Correcting the count to 8; adding the missing docs and project to the README tree; linking all five docs; and correcting the playbook/tools/templates descriptions in the Module Overview.

**Verified:** README tree matches the filesystem; counts match reality.

---

## Notes

This file should never accumulate silently — issues are either resolved (and retained here with their reasoning) or explicitly deferred with a stated reason. Nothing is deleted, so the decision history behind the architecture stays readable.
