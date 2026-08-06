# Known Runtime Issues

Tracks issues in `runtime/` — the implementation layer. Distinct from
`docs/known-issues.md`, which tracks framework architecture issues.

**Status:** V-1, V-2, V-4 and V-6 resolved in the stabilization sprint. **V-3
closed by decision** ([ADR 0004](adr/0004-config-stays-markdown-loader-owns-parsing.md)).
V-5 and V-7 postponed with ADRs.

**Open observations: L-1…L-3 (Project Loader) and R-1…R-4 (Validation Layer).
All non-blocking.** No open observation requires amending a frozen model or
rewriting a downstream module. Confidence in `ProjectContext` as a permanent
dependency is **≥95%** — see the assessment below the Task 2 heading.

---

## Resolved

| ID | Issue | Resolution |
|---|---|---|
| V-1 | Default `Validator()` was fail-open on provider validation | `NullProviderRegistry` deleted. An absent registry now means the rule cannot run, is recorded as a coverage gap, and `valid` is False. |
| V-2 | `valid` conflated "passed" with "never checked" | `ValidationResult` records a `RuleExecution` per rule; `coverage` is COMPLETE/PARTIAL; `valid` requires no blocking issues **and** complete coverage. |
| V-4 | Prefix section matching mis-bound headings | Exact resolution via `CONFIG_SECTION_ALIASES` + `canonical_config_section()`. No prefix, substring or fuzzy matching. |
| V-6 | `is_authoritative` was an out-of-band contract | Removed entirely with `NullProviderRegistry`. `ProviderRegistryPort` now declares every member runtime behaviour consults. |

---

## Closed by decision

### V-3 — Config meaning parsed from human prose by regex

**Closed, not postponed.** See [ADR 0004](adr/0004-config-stays-markdown-loader-owns-parsing.md),
which supersedes [ADR 0001](adr/0001-config-remains-prose-parsed.md).

`config.md` **remains Markdown**; no machine-readable block is introduced. A
second Architecture Decision Review found ADR 0001's two premises were false:
the format is specified by `core/templates/config.md`, and the frozen runtime
specification already makes the Project Loader the *only* config parser rather
than a second one.

The concern resolves entirely inside `runtime/` during Task 2: the Loader parses
`config.md` once and exposes typed fields on `ProjectContext`; the Validation
Layer deletes its temporary parsing helpers and reads those fields. That is a
**runtime refactor, not an architecture change** — no frozen file, released tag
or existing project is affected.

Do not re-open this on the strength of ADR 0001. ADR 0004 states the single
measurable threshold that would justify revisiting, and it is not met.

---

## Postponed (see ADRs)

| ID | Issue | ADR | Future owner |
|---|---|---|---|
| V-5 | Framework constants transcribed rather than Core-derived | [ADR 0002](adr/0002-framework-constants-are-transcribed.md) | Core Loader (Task 3) |
| V-7 | Rules are shared singletons with unenforced statelessness | [ADR 0003](adr/0003-rules-are-shared-singletons.md) | Validation Layer, before Runtime Engine adds concurrency |

---

## Open observations (found during the Task 2 Loader self-review)

Recorded, not fixed, per the sprint's no-silent-fixes rule.

> **Reassessed 2026-08-06.** These were first recorded with a warning that L-1
> and L-3 concerned the shape of `ProjectContext` and might force downstream
> redesign. A follow-up review tested that claim against the frozen
> specification and it did not hold. Both are reclassified below, and the
> confidence statement they qualified is corrected.
>
> **None of these is an architectural blocker. `ProjectContext` is stable as
> frozen, and Task 3 can proceed without amending it.**

### Confidence in `ProjectContext` as a permanent dependency: **≥95%**

The earlier figure of ~85% was based on L-1 and L-3 being unresolved questions
about the type. Two pieces of evidence from the frozen architecture remove that
doubt:

1. **No downstream module may touch the filesystem.** Exactly two modules
   declare filesystem access in their External Dependencies rows — Core Loader
   (`core/`) and Project Loader (`projects/<client>/`). Every other module
   consumes `ResolvedContext`, whose fields are content, not paths. So no
   downstream module can consume `root_path` as a path, and L-1 cannot
   propagate beyond report text. Confirmed in the current runtime: all
   filesystem I/O is confined to `runtime/loader/sources.py`.
2. **`sections` already has a named future consumer.** Token Budget Manager's
   responsibility is to "select which Knowledge sections to include", and its
   non-responsibilities restrict it to selecting or omitting "whole sections".
   That is precisely the decomposition the Loader produces.

Neither issue can force a downstream module to be rewritten.

### L-1 — `root_path` is an absolute, environment-dependent path

**Severity: Low** · Reporting quality · **Non-blocking**

*Reclassified from Medium. Originally recorded as a determinism risk that might
constitute a breaking change to `ProjectContext`; it is neither.*

`FilesystemProjectSource.project_location()` returns a resolved absolute path,
so `ProjectContext.root_path` is e.g.
`C:\Users\user\Desktop\Orbitlance-AI-Agent-Framework\projects\sunrise_dental_clinic`.

Two visible consequences, both confined to report text:

1. **Report text differs per checkout.** Rules compose `file` fields from
   `root_path`, so the same project validated on two machines produces
   different `ValidationIssue.file` strings. Ordering determinism within an
   environment is unaffected; only the rendered path differs.
2. **Mixed separators.** Rules compose with `/` while the root uses `\` on
   Windows, yielding `...\projects\orbitlance/knowledge/01_company.md`.

**Why this cannot force a rewrite.** Every consumer of `root_path` composes a
display string; none performs path arithmetic, resolution or I/O:

```
runtime/validation/rules/structure.py:103        file=f"{root_path}/{dir}"
runtime/validation/rules/knowledge.py:41         base = f"{root_path}/{KNOWLEDGE_DIR}"
runtime/validation/rules/extension_points.py:35  file=f"{root_path}/{BRANDING_DIR}"
```

Changing the value's format would not change the field's type (`str`), its
presence on the model, or any function signature. A consumer could only break
if it assumed absoluteness and performed I/O with it — and the frozen
architecture grants filesystem access to the two Loaders only, so such a
consumer cannot exist by construction.

**Why documented rather than fixed.** The choice between repo-relative
(reproducible, better for CI diffs) and absolute (unambiguous for operators)
depends on how validation output is actually consumed. The Runtime Engine and
Observability modules are those consumers and neither exists yet. Deciding now
means deciding without the requirement, and amending a just-frozen model on
speculation costs more stability than the issue costs in noise.

### L-2 — Dead API surface on frozen models

**Severity: Low** · Public API hygiene

Now that Validation reads typed config, several members are used nowhere
outside their own module: `ProjectDocument.has_section`,
`ProjectDocument.section_body`, `normalise_section_title`,
`ProjectConfig.empty`, `ProjectConfig.section`.

They are harmless but they are *public surface on models being frozen* — every
one is something a future consumer may build on, making it harder to remove
later. Deciding now whether they are supported API or leftovers is cheaper than
deciding after something depends on them.

**Note after the L-3 reclassification:** `has_section` and `section_body` are
accessors for `ProjectDocument.sections`, which L-3 establishes is provisioned
for the Token Budget Manager. Those two are therefore better read as *unused
accessors for a provisioned field* than as leftovers, and should not be removed
on the strength of "nothing calls them today". The remaining three
(`normalise_section_title`, `ProjectConfig.empty`, `ProjectConfig.section`) have
no named future consumer and remain genuinely open. Non-blocking either way.

### L-3 — `ProjectDocument.sections` is provisioned for a future consumer

**Severity: Low** · Unread-yet, not dead · **Non-blocking**

*Reclassified from Medium. Originally recorded as "dead computation and a
redundant field" on the grounds that nothing reads it. The first half of that
claim is true; the conclusion drawn from it was wrong.*

The Loader populates `sections` for every document it loads, and a
repository-wide search finds **zero** current readers — config meaning now
flows through `config_data`, and the rule that compared knowledge documents
against template headings was removed in v1.1 as invented architecture.

**But the frozen specification names its consumer.** Token Budget Manager:

> **Responsibilities:** …select which Knowledge *sections* to include (Phase 1:
> all of them; later: retrieval-based).
>
> **Non-responsibilities:** Never edit, paraphrase, or summarize Knowledge
> content — only selects/omits **whole sections**.

A module whose defined job is selecting and omitting whole Knowledge sections
requires exactly the decomposition the Loader already produces. `sections` is
therefore **provisioned ahead of its consumer**, not dead.

**Why documented rather than fixed.** Removing the field would delete the data
structure a specified future module needs, and it would have to be
reintroduced — the precise rewrite this review exists to prevent. The only
residual cost is parsing sections before anything reads them, which at
deploy-time validation of a handful of documents per project is negligible
against the filesystem I/O in the same operation.

Related to L-2, but the decisions differ: L-2 asks "is this accessor supported
API?", L-3 asked "should the Loader compute this at all?" — and the answer to
L-3 is now settled: yes.

---

## Open observations (found during the stabilization self-review)

Recorded rather than fixed, per the sprint's no-silent-fixes rule. None
requires an architectural change; none blocks the Project Loader.

### R-1 — Collaborator check precedes applicability, so coverage loss is over-reported

**Severity: Low** · Precision, not correctness

`ValidationPipeline._run_rule` checks `required_collaborators` before calling
`is_applicable`. A rule that would have skipped anyway for a precondition
reason is therefore reported as `COLLABORATOR_UNAVAILABLE` when the
collaborator is absent.

Observed against the real repository: `sunrise_dental_clinic` declares a
placeholder provider, so `config.llm_provider_registered` would have skipped
with `PRECONDITION_ABSENT` regardless — yet it reports a collaborator gap.

The ordering is deliberate: calling `is_applicable` first would let a future
rule's `is_applicable` touch an absent collaborator and raise. Erring toward
reporting *more* coverage loss is the fail-closed direction. The cost is that
`coverage=partial` is occasionally pessimistic.

**Not fixed because:** the safe ordering is the current one, and making it
precise means letting `is_applicable` run without collaborator guarantees —
trading a reporting imprecision for a correctness hazard.

### R-2 — Collaborators are injected asymmetrically

**Severity: Low** · Interface consistency

`CoreBundle` is a per-call parameter (`validate_project(project, core)`), while
`ProviderRegistryPort` is constructor-injected (`Validator(provider_registry=)`).

The asymmetry has a rationale — a registry is a long-lived service, a
CoreBundle varies per call and may legitimately be absent in CI — but two
collaborators of the same kind reaching the same context by different routes is
an inconsistency a new contributor will notice and may copy inconsistently.

**Not fixed because:** unifying them means either forcing a long-lived registry
through every call site, or hiding the per-call CoreBundle in construction and
losing CI's ability to validate without Core. The right answer depends on how
the Runtime Engine actually wires these, which does not exist yet.

### R-3 — `ConfigSectionIndex` is rebuilt several times per validation

**Severity: Low** · Redundant work

Six config rules each construct a `ConfigSectionIndex`, and the two provider
rules construct one in both `is_applicable` and `evaluate` — roughly eight
constructions per project validation, each a dict comprehension over ~10
headings.

Negligible today. At thousands of agents validated at deploy time it remains
negligible (microseconds against filesystem and network costs). Recorded only
so it is a known, measured choice rather than an oversight.

**Not fixed because:** the obvious remedy is caching the index on the context,
which adds mutable state to a frozen context object — precisely the kind of
shared-state hazard ADR 0003 exists to avoid. Not worth it for this saving.

### R-4 — `ValidationResult.valid` changed meaning

**Severity: Low** · Migration note, not a defect

`valid` is now conjunctive (no blocking issues **and** complete coverage).
Callers wanting the older, narrower question must use `has_blocking_issues`.

No consumer exists yet — the Project Loader has not been written — so nothing
breaks. Recorded so the change is explicit rather than discovered later.

---

## Notes

Nothing here is deleted once resolved; resolved entries keep their reasoning so
the decision history stays readable.
