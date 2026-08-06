# ADR 0004 — config.md stays Markdown; the Project Loader is its sole parser

**Status:** Accepted — final
**Date:** 2026-08-06
**Supersedes:** [ADR 0001](0001-config-remains-prose-parsed.md)
**Relates to:** Principal Engineer Review finding V-3

> **This decision is closed.** It was reached after a second Architecture
> Decision Review that examined evidence the first review did not. Do not
> re-open it on the strength of ADR 0001, which is superseded and retained only
> as historical record. If you believe this needs revisiting, read
> "When this decision should be revisited" at the bottom first — it states the
> specific threshold, and that threshold is not currently met.

---

## Decision

`projects/<client>/config.md` **remains human-authored Markdown.** No YAML front
matter, TOML section, JSON block or any other machine-readable format is
introduced.

The concern ADR 0001 raised is real but is resolved **entirely inside
`runtime/`**, by placing config parsing where the frozen architecture already
assigned it.

---

## The original assumption behind ADR 0001

ADR 0001 rested on two premises:

1. **That config.md's format was under-specified**, so any parser was
   necessarily guessing at shape — making a demonstrated failure
   (`Primary provider: anthropic` producing `CONF004 provider not declared`) a
   *false positive on a correctly-configured project*.

2. **That the Project Loader would become a second, independent consumer** of
   config.md, duplicating the Validation Layer's regex heuristics — so the
   format had to be settled before Task 2, or the fragility would have to be
   unwound from two modules instead of one.

From those premises the conclusion followed: amend the framework now, while the
blast radius is small.

## Why that assumption turned out to be incorrect

**Premise 1 was wrong.** The format is not under-specified. `core/templates/config.md`
— a frozen Core file — states the shape explicitly:

```
- **Primary:**
- **Model:**
- **Secondary (optional):**
```

A project writing `Primary provider: anthropic` has therefore **deviated from a
frozen template**, and blocking it is correct behaviour. What was wrong was only
the *diagnostic*: the validator says "not declared" when the field is declared,
merely off-template. That is a message-quality defect, not a correctness defect,
and message quality is purely a runtime concern.

The framework's contract mechanism here is the same one already used for
Knowledge: **the template is the specification.** ADR 0001 treated
"specified by template" as equivalent to "unspecified". It is not.

**Premise 2 was wrong.** The frozen runtime specification already assigns config
parsing to exactly one module:

> **Project Loader — Responsibilities:** Read `projects/<client>/`;
> **parse `config.md`** and the three extension-point folders

and already defines the resolved, typed shape downstream modules consume:

> **ResolvedContext:** `resolvedConfig (incl. llmProvider and operatingConstraints)`

So the Project Loader is not a *second* consumer — it is the **only** sanctioned
one. The Validation Layer parsing config.md is a temporary overreach that
existed solely because Validation was built first, before the Loader existed.

The duplication ADR 0001 feared was never architecturally sanctioned. It was an
artefact of build order, and it is corrected by *following* the frozen
architecture rather than amending it.

## The evidence that changed the decision

| # | Evidence | Source | Effect |
|---|---|---|---|
| 1 | Template specifies the field shape by example | `core/templates/config.md`, LLM Provider section | Reclassifies the defect from correctness to diagnostics |
| 2 | Loader is the designated config parser | `docs/runtime-specification.md`, Project Loader §2 | Removes the "second consumer" premise entirely |
| 3 | Downstream modules consume typed fields, not raw markdown | `docs/runtime-specification.md`, ResolvedContext | Confirms typed config was always the intended shape |
| 4 | Machine-read surface is 4 sections, ~3 identifier fields | measured against `runtime/validation/rules/config.py` and a real project config | The problem is far narrower than "config is unstructured" |
| 5 | Operating Constraints is prose by design | Guardrail Engine spec; "structured constraints" listed as a *future extension point* | Structuring it would be actively wrong |
| 6 | Knowledge/Branding/Integrations "Status" sections are never parsed | only `declares()` is called, never `body()` | They are human bookkeeping, correctly outside the machine surface |

## Why the Architecture Freeze remains valid

The freeze was not the obstacle — it was the mechanism that forced this to be
examined twice instead of once. Specifically:

- **No frozen file needs to change.** The defect and the duplication risk are
  both resolvable within `runtime/`.
- **The frozen spec already contained the correct answer.** Loader parses;
  everything downstream consumes typed fields. The architecture anticipated
  this; the implementation simply ran ahead of it.
- **The freeze surfaced the real question.** Requiring a deliberate,
  evidence-backed review before amendment is precisely what caused the faulty
  premises to be caught. Had amendment been casual, three frozen files and two
  projects would have been migrated for a problem that did not exist.

## Why no framework amendment is required

Every concern ADR 0001 raised maps to a runtime-only resolution:

| ADR 0001 concern | Resolution | Where |
|---|---|---|
| Heuristics spread across consumers | Loader parses once; Validation consumes typed fields | `runtime/` — already mandated by frozen spec |
| Validation Layer's regex helpers | Deleted when it stops parsing | `runtime/validation/rules/config.py` |
| No type safety at the boundary | `ProjectContext` carries typed config fields | `runtime/models/project_context.py` — additive |
| Confusing `CONF004` on off-template input | Distinct diagnostic naming the expected shape and quoting what was found | `runtime/` |

None of these touches `core/`, `docs/architecture.md`,
`docs/project-configuration.md`, or any released tag.

---

## Architectural conclusion (normative)

1. **`config.md` remains Markdown.** No machine-readable block is introduced.
2. **The Project Loader is the ONLY component that parses `config.md`.**
3. **The Validation Layer consumes typed `ProjectContext` produced by the
   Loader.** It does not parse config.md itself.
4. **Downstream runtime modules consume resolved, typed configuration** via
   `ResolvedContext`, never raw markdown.
5. **Parsing logic must never spread across runtime modules.** A second module
   parsing config.md is a defect, not a design choice — regardless of how
   convenient it appears locally.

**`core/templates/config.md` is the authoritative specification of config
shape.** Enforcing it strictly, with an actionable diagnostic, is enforcing
Core — not imposing a runtime-invented convention.

---

## Classification

> **This is a Runtime refactor. This is NOT an Architecture change.**

- Frozen architecture: **unchanged**
- `core/`: **unchanged**
- `docs/architecture.md`, `docs/project-configuration.md`: **unchanged**
- Released tags `v1.0-architecture-freeze`, `v1.1-validation-layer`: **unchanged**
- Existing projects: **no migration required**

## Implementation consequence — during Task 2 (Project Loader)

1. **Parsing responsibility moves into the Loader.** It parses `config.md` once
   and exposes typed fields on `ProjectContext`, keeping
   `operating_constraints` as prose (it is destined for a prompt).
2. **The Validation Layer removes its temporary parsing logic** —
   `_LIST_ITEM_RE`, `_BOLD_LABEL_RE`, `_CODE_TOKEN_RE`,
   `_declared_primary_provider` and `ConfigSectionIndex` — and reads typed
   fields instead. This is a **net deletion**.
3. **Public interfaces introduced in v1.1 remain stable.** `Validator`,
   `ValidationResult`, `ValidationIssue`, `Severity`, `Collaborator`,
   `ProviderRegistryPort` and every issue code are unaffected. Only the private
   internals of `rules/config.py` change.
4. **No released architecture artifact is modified.** The change lands as a
   normal runtime version bump.

The Loader should also emit a precise diagnostic when a section is present but
off-template, quoting the offending line and the expected form — converting
today's confusing block into an actionable one.

---

## When this decision should be revisited

One threshold, stated so it can be checked rather than argued:

> If the number of **machine-read identifier fields** in `config.md` grows
> substantially beyond the current three (provider, model, secondary), the cost
> of expressing each as a bespoke Markdown shape may exceed the cost of a format
> change.

That threshold is **not currently met**, and [ADR 0002](0002-framework-constants-are-transcribed.md)'s
resolution — deriving workflow and playbook identifiers from `CoreBundle` rather
than config — moves the project further from it, not closer.

Absent that threshold being crossed, re-opening this is re-litigating a decision
that has already been reviewed twice against evidence.
