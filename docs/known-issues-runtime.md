# Known Runtime Issues

Tracks issues in `runtime/` — the implementation layer. Distinct from
`docs/known-issues.md`, which tracks framework architecture issues.

**Status:** V-1, V-2, V-4 and V-6 resolved in the stabilization sprint. **V-3
closed by decision** ([ADR 0004](adr/0004-config-stays-markdown-loader-owns-parsing.md)).
V-5 and V-7 postponed with ADRs. Four non-blocking observations recorded below.

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

Recorded, not fixed, per the sprint's no-silent-fixes rule. None blocks Task 3,
but **L-1 and L-3 concern the shape of `ProjectContext`**, which downstream
modules are about to depend on — so they are worth deciding before more
consumers arrive rather than after.

### L-1 — `root_path` is an absolute, environment-dependent path

**Severity: Medium** · Determinism across environments

`FilesystemProjectSource.project_location()` returns a resolved absolute path,
so `ProjectContext.root_path` is e.g.
`C:\Users\user\Desktop\Orbitlance-AI-Agent-Framework\projects\sunrise_dental_clinic`.

Two consequences:

1. **Validation output is not reproducible across machines.** Rules compose
   `file` fields from `root_path`, so the same project validated on two
   checkouts produces different `ValidationResult` content. The Validation
   Layer guarantees deterministic ordering *within* an environment; this
   weakens that guarantee *across* environments, which is where CI diffs live.
2. **Mixed separators.** Rules compose with `/` while the root uses `\` on
   Windows, yielding `...\projects\orbitlance/knowledge/01_company.md`.

The fix is a decision, not a patch: should `root_path` be repo-relative
(reproducible, friendlier in reports) or absolute (unambiguous for I/O)? It is
a public field of a model about to be depended on, so changing it later is a
breaking change.

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

### L-3 — `ProjectDocument.sections` is computed for every document and read by nothing

**Severity: Medium** · Dead computation and a redundant field

The Loader populates `sections` for every document it loads (~10 per project),
but a repository-wide search finds **zero** readers. Config meaning now flows
through `config_data`, and the rule that once compared knowledge documents
against template headings was removed in v1.1 as invented architecture.

So the runtime parses section structure for every project document on every
load and discards it. Wasted work is the smaller problem; the larger one is
that `sections` is a field on a model about to be frozen, and it currently has
no defined consumer — a future module could reasonably assume it is meaningful.

Related to L-2, but recorded separately because the decision differs: L-2 asks
"is this API supported?", L-3 asks "should the Loader compute this at all?"

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
