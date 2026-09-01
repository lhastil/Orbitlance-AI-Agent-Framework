# Known Runtime Issues

Tracks issues in `runtime/` — the implementation layer. Distinct from
`docs/known-issues.md`, which tracks framework architecture issues.

**Status:** V-1, V-2, V-4 and V-6 resolved in the stabilization sprint. **V-3
closed by decision** ([ADR 0004](adr/0004-config-stays-markdown-loader-owns-parsing.md)).
V-5 and V-7 postponed with ADRs.

**No issue in this register is Blocking.** No open item breaks a published
signature or requires rewriting a shipped module. Confidence in
`ProjectContext` as a permanent dependency is **≥95%** — see the assessment
below the Task 2 heading.

**Thirteen open Architecture Issues: PR-1, TE-2, TE-3, TE-5, TE-6, TE-7, RE-1,
RE-3, RE-4, RE-5, AUDIT-6, OB-1, OB-3**, recorded during Modules 10, 11, 14 and
15, and the §14 post-implementation audit. None blocks the module it was found in; each needs a
system-owner decision because closing it means ruling between frozen clauses,
supplying a policy the framework does not define, or amending a frozen artifact.

**AUDIT-1, AUDIT-2 and AUDIT-4 shared one cause** — the absence of a production
composition root — and were **closed together on 2026-09-01** by
`runtime/runtime_engine/activation.py` plus the removal of `token_budget` from
`RuntimeEngine.__init__`. AUDIT-1 is closed *globally*; **AUDIT-2 is closed for
the production activation path only**, because the low-level constructor still
accepts externally supplied session and workflow stores. That distinction is
preserved deliberately in AUDIT-2's entry and must not be collapsed.

PA-3 was recorded as an Architecture Issue on 2026-08-09 and
**reclassified to Documentation / Reporting on 2026-08-09** after a final
evidence review found its behavioural premise unsupported. The system owner
decided Interpretation B: `core/prompts/06_lead_qualification.md` is **not**
assembled into the runtime `PromptBundle`. The Architecture Freeze was not
amended.

---

## Classification

Assigned at the Module 2 release gate (2026-08-07). Every issue carries exactly
one class.

| Class | Meaning | Blocks a freeze? |
|---|---|---|
| **Blocking** | Freezing forces a later redesign: a breaking signature change, an amended frozen model, or a rewritten downstream module. | **Yes** |
| **Architecture Issue** | The runtime is implementable, but a design question is unsettled and closing it amends a frozen document. Only the system owner may decide. | **Blocks freeze, not implementation** |
| **Additive Extension** | A new field, method or type will be added later. Nothing existing changes shape. | No |
| **Runtime Improvement** | Internal quality, precision or hygiene. Invisible across the module boundary. | No |
| **Documentation / Reporting** | The behaviour is correct and tested; what is open is that a future module must *know* it. Nothing to build. | No |
| **Closed** | Resolved, or settled by decision. Retained for decision history. | No |

| ID | Title | Class |
|---|---|---|
| V-1 | Fail-open default provider validation | Closed |
| V-2 | `valid` conflated "passed" with "never checked" | Closed |
| V-3 | Config meaning parsed from prose | Closed (ADR 0004) |
| V-4 | Prefix section matching | Closed |
| V-5 | Framework constants transcribed, not Core-derived | Runtime Improvement (ADR 0002) |
| V-6 | `is_authoritative` out-of-band contract | Closed |
| V-7 | Rules are shared singletons | Runtime Improvement (ADR 0003) |
| L-1 | `root_path` is absolute and environment-dependent | Runtime Improvement |
| L-2 | Unused public surface on frozen models | Runtime Improvement (partly Closed) |
| L-3 | `ProjectDocument.sections` has no current reader | Closed |
| **L-4** | **Integrations exposed untyped; per-contract state deferred to the Tool Executor** | **Additive Extension** |
| **L-5** | **`ProjectSource` exposes no change-detection signal** | **Additive Extension** |
| R-1 | Coverage loss over-reported | Runtime Improvement |
| R-2 | Collaborators injected asymmetrically | Runtime Improvement |
| R-3 | `ConfigSectionIndex` rebuilt per rule | Runtime Improvement |
| R-4 | `ValidationResult.valid` changed meaning | Closed |
| **R3-1** | **Validation accepted three workflow spellings the Resolver drops** | **Closed** |
| **R3-2** | **`ResolvedContext` caching ownership unassigned** | **Documentation / Reporting** |
| **R3-3** | **Missing Branding resolves to an empty overlay** | **Documentation / Reporting** |
| **R3-4** | **`ResolvedContext` has no consumer yet** | **Additive Extension** |
| **PA-3** | **`06_lead_qualification.md` is not assembled; its behaviour is delivered distributively** | **Documentation / Reporting** (was: Architecture Issue) |
| **PR-1** | **§10.10 and §13.10 disagree about whether the secondary provider must be registered** | **Architecture Issue** |
| **PR-2** | **The declared Model is required at routing time but not at validation** | **Documentation / Reporting** |
| **PR-3** | **`ProviderRequest` deferred; sole ownership reserved to the Provider Registry** | **Additive Extension** |
| **TE-1** | **`ToolRequest` exists as a type with no writer** | **Documentation / Reporting** |
| **TE-2** | **§11.12(c)'s retry scenario is unenforceable; no retry implemented** | **Architecture Issue** |
| **TE-3** | **§11.2's integrations path unexecutable; §11.9's Resolver cross-reference diverges** | **Architecture Issue** |
| **TE-4** | **`ToolResponse` has no diagnostic channel** | **Documentation / Reporting** |
| **TE-5** | **No path from a tool result back to the model** | **Architecture Issue** |
| **TE-6** | **`core/tools/` declares mutual dependency cycles** | **Architecture Issue** |
| **TE-7** | **`ToolRequest.project_id` is never checked against the context's** | **Architecture Issue** |
| **RE-1** | **Module 4 still accepts an unbudgeted assembly; §14 never uses it** | **Architecture Issue** |
| **RE-2** | **`RuntimeRequest` / `RuntimeResponse` are framework-introduced** | **Documentation / Reporting** |
| **RE-3** | **§14 establishes no concurrent runtime contract** | **Architecture Issue** |
| **RE-4** | **The default runtime keeps no audit trail** | **Architecture Issue** |
| **RE-5** | **§14 composes no customer-facing fallback text** | **Architecture Issue** |
| **RE-6** | **A blocked answer is not recorded as an agent turn** | **Documentation / Reporting** |
| **RE-7** | **§14 publishes no camelCase alias; the convention is unsettled** | **Documentation / Reporting** |
| **AUDIT-1** | **Budget and provider are never proven to describe the same model** | **Closed** — resolved globally |
| **AUDIT-2** | **Cross-project session/workflow contamination via shared stores** | **Closed for the production activation path** (constructor escape hatch remains) |
| **AUDIT-3** | **`transition_history` grows with no-op entries** | **Runtime Improvement** |
| **AUDIT-4** | **No production composition/activation root** | **Closed** — `activation.py` |
| **AUDIT-5** | **Channel semantics after the first turn** | **Documentation / Reporting** |
| **AUDIT-6** | **A degraded turn always returns `escalate=False`** | **Architecture Issue** |
| **AUDIT-7** | **`RuntimeEngine` inspection surface beyond §14.6** | **Documentation / Reporting** |
| **OB-1** | **Audit persistence is in-memory and not durable (§15.8 partial)** | **Architecture Issue** |
| **OB-2** | **§15.12(d) duplicate-ID scenario cannot arise; not faked** | **Documentation / Reporting** |
| **OB-3** | **§15.9 audit-gap alert has no seam** | **Architecture Issue** |
| **PA-4** | **§4 cites an assembly order in a section that does not exist** | **Documentation / Reporting** |
| **PA-5** | **Playbook provenance check inspected only the first source** | **Closed** |
| **PA-6** | **Runtime provenance cannot prove content origin** | **Documentation / Reporting** |
| **PA-7** | **Section provenance listed documents that were not rendered** | **Closed** |
| **PA-8** | **Spec §12(b) known-playbook-string fixture test was missing** | **Closed** |

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
| V-7 | Rules are shared singletons with unenforced statelessness | [ADR 0003](adr/0003-rules-are-shared-singletons.md) | Validation Layer, **before concurrent request handling or parallel validation is introduced** — §14 introduces neither, so its existence does not trigger the deadline |

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

**Class: Runtime Improvement**, partly **Closed** — `has_section` and
`section_body` are settled by L-3 and are no longer open questions. The
remaining three are hygiene: leaving them costs unused surface, and removing
them later is a deletion from a model no external consumer has yet built on.
Neither direction forces a redesign.

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
L-3 is now settled: yes. **Class: Closed.**

---

## Found at the Module 2 release gate (2026-08-07)

Both are **Additive Extension**. Neither changes an existing field, signature or
model shape, so neither blocks the freeze.

### L-4 — Integrations are exposed untyped, but the Resolver needs per-contract state

**Class: Additive Extension** · **Non-blocking**

`ResolvedContext` must carry `degraded_capabilities`, and the frozen resolution
rule for Integrations is *per-contract*, not all-or-nothing:

> **Integrations** — "Degrade **the affected** capability."

So the Resolver must determine which of the five `core/tools/` contracts have a
provider configured. `ProjectContext` exposes `config_data` as typed
(`ProjectConfig`) but `integrations` only as raw `ProjectDocument`s. The only
mechanism in the runtime today is substring search over concatenated raw text
(`runtime/validation/rules/extension_points.py`, `IntegrationsCoverageRule._mentions`).

When the Resolver is built it will have three options:

| Option | Verdict |
|---|---|
| Re-implement the substring interpretation in the Resolver | **Invalid** — the duplication class [ADR 0004](adr/0004-config-stays-markdown-loader-owns-parsing.md) forbids; `rules/config.py` already states "extend the Loader — never parse here" |
| Depend on the Validation Layer | **Invalid** — inverts the frozen dependency direction; Validation reads Loader output, never the reverse |
| **Loader exposes typed integrations** | **Correct** — and additive |

**Why this is not blocking.** The correct option adds a field to
`ProjectContext`. `config_data` was added the same way during Task 2 without
altering a single existing consumer, so the additive path is demonstrated, not
assumed. No published signature changes, no frozen model is amended, and no
downstream module is rewritten.

**Why not built now.** Building typed integrations before the Resolver exists
means guessing its requirements — the exact error [ADR 0001](adr/0001-config-remains-prose-parsed.md)
made once and ADR 0004 had to reverse. The Resolver is the module that knows
what shape it needs; it should specify it.

**Owner:** Tool Executor.

> **Evidence added 2026-08-07, after Runtime Module 3 was implemented.**
>
> **The Resolver was built without requiring typed integration data, so L-4
> remains an Additive Extension rather than a blocker.** This is now measured,
> not predicted.
>
> This entry originally named the Resolver as owner, on the assumption that
> computing `degraded_capabilities` would force it to interpret `integrations/`
> document text. That assumption was wrong on two counts:
>
> 1. **The spec assigns per-tool provider resolution elsewhere.** Tool Executor
>    responsibility 2: *"resolve the project's configured concrete provider from
>    `ResolvedContext.integrations`."* Deciding which individual tool has a
>    configured provider is that module's job, not the Resolver's.
> 2. **The granularity the Resolver actually needs is derivable from Core.** The
>    Resolver's test scenario (c) requires a per-tool capability-disabled state
>    when Integrations is *missing*, and the capability set comes from
>    `core/tools/` via `CoreBundle`. No document text is read.
>
> The Resolver therefore degrades every Core capability when Integrations is
> absent, and claims no degradation when it is present — leaving per-tool
> resolution to its documented owner. Typed integration data, if it is ever
> wanted, should be specified by the Tool Executor, which is the module that
> knows what shape it needs.

### L-5 — `ProjectSource` exposes no change-detection signal

**Class: Additive Extension** · **Non-blocking**

The specification's Loader responsibility reads "cache per project; invalidate
on **detected change**". The current design delegates that policy to the
injected `ProjectCache`, but a cache can only detect change through the data it
is given, and `ProjectSource` exposes no mtime, hash, version or etag — its
surface is `project_exists`, `project_location`, `directory_exists`,
`list_documents`, `document_exists`, `read_document`.

**Why this is not blocking.** A change-detecting cache for the filesystem case
can `stat()` directly: the cache lives in `runtime/loader/`, and the Project
Loader is one of only two modules the frozen architecture grants filesystem
access, so this violates nothing. The Protocol only needs extending for a
source that is *not* the filesystem — the spec's own future extension point,
which does not exist yet. At that point there is exactly one implementer
(`FilesystemProjectSource`) to update, and the capability can be introduced as a
separate optional Protocol rather than a breaking edit to this one.

**Owner:** whoever introduces the second `ProjectSource` implementation.

---

## Found during Runtime Module 3 (Resolver), 2026-08-07

### R3-1 — Validation accepted three workflow spellings the Resolver drops

**Class: Closed** (recorded as Runtime Improvement; resolved the same day)

**Evidence, reproduced by executing both modules against the same labels:**

| Declared label | Validation Layer | Resolver |
|---|---|---|
| `Consultation Request` | accepted → `consultation` | unresolved, dropped |
| `CRM Synchronization` | accepted → `crm_sync` | unresolved, dropped |
| `CRM Synchronisation` | accepted → `crm_sync` | unresolved, dropped |

A project declaring any of the three passed validation and then lost that
workflow from `ResolvedConfig.enabled_workflows`. The loss was recorded as a
`DECLARATION_UNRESOLVED` entry in `fallback_log`, so it was never silent — but
the two modules genuinely disagreed about the same input.

**The divergence was in Validation, not the Resolver.**
`core/templates/config.md` states: *"The six available workflows are: Discovery,
Recommendation, Consultation, CRM Sync, Follow-up, Voice Agent."* It sanctions
none of the three. The Resolver derives its vocabulary from `core/workflows/`
via `CoreBundle` and transcribes nothing, so it followed the frozen template
exactly. `WORKFLOW_ALIASES` is a *transcription* of that template, and the
transcription had drifted — the same class of problem [ADR 0002](adr/0002-framework-constants-are-transcribed.md)
records for V-5.

**This was a runtime consistency issue, not an architecture issue.** No frozen
document was wrong, no model changed shape, and no public interface moved.

**Resolution.** The three unsupported aliases were removed from
`runtime/validation/framework_spec.py`. Nothing was added to the Resolver: the
frozen template is authoritative, and broadening the Resolver to match a drifted
transcription would have inverted that authority.

Measured before changing anything:

- Exactly those three entries were load-bearing. The other ten aliases are
  redundant with `ConfigWorkflowsRule._resolve`'s underscore fallback, so
  removing three entries is the smallest change that closes the gap.
- **No existing project is affected.** Neither `orbitlance` nor
  `sunrise_dental_clinic` declares any of the three; sunrise's only occurrence
  of the phrase "Consultation Request" is prose *inside* a `**Consultation**`
  bullet, and its parsed declarations are the six template spellings.
- End-to-end validation output is unchanged: core `VALID`; orbitlance 9 errors
  + 2 warnings; sunrise 1 error.

`tests/test_vocabulary_alignment.py` now asserts the property that was violated:
everything Validation accepts, the Resolver must also resolve — checked
exhaustively over the alias table, so the two can never drift apart again
without a test failing.

### PA-5 — The playbook provenance check inspected only the first source

**Class: Closed** · fixed 2026-08-09

`PromptSection.source` was a single comma-joined string and `is_from_playbook`
tested it with `startswith`, so for any multi-document slot — Guardrails,
Knowledge, Branding — only the first path was ever examined. A section sourced
from `"projects/x/knowledge/a.md, core/industry_playbooks/healthcare.md"`
reported `False` and the rule-10 assertion did not fire.

Not reachable in the shipped code, because no path produced a playbook source,
but a logic defect in a safety assertion nonetheless.

**Fixed** by making provenance structured: `PromptSection.sources` is a tuple
and every entry is checked. `source` is retained as a joined property for
display. Regression test: `test_playbook_source_is_detected_in_any_position`.

### PA-6 — Runtime provenance cannot prove content origin

**Class: Documentation / Reporting** · **Open by necessity, not by choice**

Rule 10 requires that assembled output never contain a string sourced from
`core/industry_playbooks/`, *"enforced as a hard runtime assertion, not just a
design intention"*.

**What was wrong.** The first implementation asserted on a label the assembler
assigned itself from the slot it was filling, which made the check tautological:
it could never fail. Injecting the full text of `core/industry_playbooks/healthcare.md`
into `CoreBundle.prompts["02_mission.md"]` — exactly the Core Loader defect the
rule exists to catch — assembled cleanly with playbook text in the Mission slot.

**What was fixed.** Provenance now comes from `ProjectDocument.relative_path`,
which the Loader records from where the file was actually read. This is existing
evidence, not invented metadata. The realistic defect — a Loader globbing
`core/industry_playbooks/*.md` into another group while carrying the true path —
**is now detected** and raises `PlaybookLeakError`.

**What remains impossible.** A document carrying playbook *text* under a
falsified `relative_path` is indistinguishable from a genuine prompt. The
assembler receives no content-origin metadata and no playbook text to compare
against: `CoreBundle` carries `playbook_names` only, with no content field, by
deliberate design. Establishing this would require adding provenance or playbook
content to `CoreBundle` — a frozen data model — so it is **not** done.

**Enforcement boundary.** For that residual case the spec's own rule-12(b)
fixture test is the enforcement mechanism: it checks real assembled output
against real playbook strings. Both halves are covered by tests that state
plainly which is which — `test_playbook_document_misfiled_into_a_prompt_slot_is_detected`
and `test_playbook_content_with_a_falsified_path_is_not_detectable`.

This entry stays open as documentation so no future reader assumes the runtime
assertion proves more than it does.

### PA-7 — Section provenance listed documents that were not rendered

**Class: Closed** · fixed 2026-08-09

`sources` for Knowledge and Branding was built from every candidate document
while `content` was built only from live ones, so an empty document appeared in
the provenance record without contributing text. Both are now derived in one
pass over the documents actually rendered. Regression test:
`test_sources_record_only_documents_actually_rendered`.

### PA-8 — Spec §12(b)'s known-playbook-string fixture test was missing

**Class: Closed** · fixed 2026-08-09

Spec §12(b) requires *"output never contains a known playbook string
(snapshot/fixture test)"*. The original suite tested provenance only; no test
read `core/industry_playbooks/` content, so the required check did not exist.

**Fixed** with a parametrised fixture test that takes a distinctive prose line
verbatim from each real playbook file and asserts it never appears in assembled
output — for the normal bundle and the degraded bundle — using a `CoreBundle`
built from the real `core/` tree. A guard test asserts the fixture corpus is
non-empty, so the check cannot silently become vacuous. `core/` is read, never
modified.

---

### R3-2 — `ResolvedContext` caching ownership is unassigned

**Class: Documentation / Reporting** · **Non-blocking**

The frozen data-model row says `ResolvedContext` is *"Created per project by
Resolver, typically once per activation/deploy, cached; recomputed on underlying
change."* But the Resolver's own module rows assign it no caching duty:
responsibility 2 covers only per-extension-point decisions and recording them,
and external dependencies are *"None (pure in-memory transformation)."*

Contrast the Project Loader, whose responsibility 2 says explicitly *"cache per
project; invalidate on detected change"*. That module was given the duty; this
one was not.

**No caching owner has been invented.** The Resolver is implemented as the pure
function the spec describes — no cache, no collaborator, no hidden state. A pure
function may be cached by any caller, so nothing is lost by leaving this open.

Recorded as an ownership clarification for whoever implements the Runtime Engine
or the first `ResolvedContext` consumer. That module should claim the duty
deliberately rather than discover the gap.

### R3-3 — Missing Branding resolves to an empty overlay

**Class: Documentation / Reporting** · **Non-blocking**

`docs/project-configuration.md` says missing Branding should *"Fall back to
Core's neutral default voice"*, because *"Core Personality already defines a
complete, safe behavioral contract."*

The Prompt Assembler's order emits **Core Personality in its own slot**, and
Branding later as an **overlay**. Copying Core Personality into the overlay slot
would therefore emit the same text twice in a single prompt.

The Resolver returns an **empty overlay** and records a
`CORE_DEFAULT_APPLIED` decision naming the reason. Both frozen statements hold:
the voice is Core's, and it is delivered exactly once.

Implemented and covered by tests. Recorded here because the **Prompt Assembler
must know this contract** — an empty `ResolvedContext.branding` means "Core's
default voice applies", never "branding data is missing and must be sourced".

### R3-4 — `ResolvedContext` has no consumer yet

**Class: Additive Extension** · **Non-blocking**

`ResolvedContext` is written solely by the Resolver. Its future readers —
Prompt Assembler, Token Budget Manager, Guardrail Engine, Tool Executor and
Provider Registry — do not exist, so the type has been designed against the
frozen specification rather than against an observed consumer.

This is the same condition `ProjectContext` was in before the Project Loader
was built, and it resolved additively: `config_data` was added during Task 2
without altering a single existing consumer.

**Do not pre-build speculative fields.** A consumer that needs something absent
should specify it, exactly as the Resolver specified nothing until the frozen
spec required it. Any such addition is expected to be additive, not a redesign.

---

## Found during the Runtime Module 4 (Prompt Assembler) architecture study, 2026-08-09

No code was written and no frozen document was modified. Module 4 is **not**
implemented.

### PA-3 — `06_lead_qualification.md` is not assembled; its behaviour is delivered distributively

**Class: Documentation / Reporting** · **Decided** · Reclassified 2026-08-09
from ARCHITECTURE ISSUE

> **Decision — Interpretation B.** The system owner decided that
> `core/prompts/06_lead_qualification.md` is **not** assembled into the runtime
> `PromptBundle`. Runtime Module 4 implements `runtime-specification.md` §4's
> nine slots verbatim and adds no slot for it. **The Architecture Freeze was not
> amended.**
>
> `06` remains **validator-required** (`REQUIRED_PROMPTS` lists all ten). It is
> authoritative design and authoring documentation describing a cross-cutting
> judgment the framework implements *distributively* rather than as one injected
> block.
>
> **Optional, deferred, non-blocking:** `docs/architecture.md:123` says the
> judgment is one "the agent applies", which reads as implying injection.
> Clarifying that it describes distributed implementation is documentation debt
> with no runtime consequence. It is deliberately **not** done here, because it
> would modify a frozen document.

The record below is preserved because it contains three corrections to earlier
analysis that a future reader should not have to rediscover.

#### What each frozen document says

**`docs/runtime-specification.md` §4, Prompt Assembler, row 2** — the assembly
order, stated in full:

> Core Personality → Mission → Conversation Rules → Guardrails bundle →
> Fallback Responses → Tool Instructions → Branding overlay → Knowledge (per
> Token Budget Manager's selection) → active Workflow's instructions (others
> present only as an index).

Nine slots. `06_lead_qualification.md` is not among them. The frozen `CoreBundle`
data-model row independently names the same six prompt modules
(*personality, mission, conversationRules, guardrailsBundle, fallbackResponses,
toolInstructions*) and likewise excludes it.

**`docs/architecture.md:123`:**

> **Lead Qualification is deliberately prompt-only.** It exists as
> `core/prompts/06_lead_qualification.md` with no corresponding workflow file.
> … Lead Qualification is a continuous *judgment* the agent applies while inside
> those workflows … Workflow files referencing "Lead Qualification" as a
> dependency refer to this prompt module.

**`docs/architecture.md:42–55`** describes `core/prompts/` as *"Defines the AI's
behavior"* and lists Lead Qualification among its examples: *"Prompts define
how the AI behaves."*

#### There is no literal textual contradiction — the gap is behavioural

This entry deliberately does **not** claim the two documents contradict each
other, and an earlier draft of this finding that did so was wrong.

`architecture.md:123`'s subject is **why no workflow file exists**. "Prompt-only"
is a statement about *where the file lives* — in `core/prompts/`, not
`core/workflows/` — and that statement is true regardless of assembly. **No
frozen document anywhere states that every file in `core/prompts/` is injected
into the assembled prompt.** Verified: `08_guardrails.md` describes injection,
but only of `core/guardrails/`; §4 is the sole frozen statement about assembly,
and it is complete and unambiguous.

So both documents are simultaneously true as written. What is missing is a
**mechanism**: `architecture.md` describes an agent behaviour — a continuous
qualification judgment — that the frozen assembly order provides no way to
produce. That is an incompleteness in the design, not a defect in either
document's text.

#### Why the two interpretations cannot both be satisfied

The documents can coexist; the two *runtime behaviours* cannot. Either the
module is assembled or it is not.

| | Interpretation A — assemble it | Interpretation B — do not |
|---|---|---|
| Runtime behaviour | The qualification criteria are in every prompt; the agent can apply the continuous judgment `architecture.md` describes. | The criteria never reach the model. The agent cannot apply the judgment; `06` becomes an authoring reference, like a template. |
| Consequence for `06` | A live behavioural prompt module. | A file the Validation Layer requires to exist (`REQUIRED_PROMPTS` lists all ten) that no runtime path ever uses. |
| What must change | `runtime-specification.md` §4 row 2 **and** the `CoreBundle` data-model row. | `architecture.md:123`'s phrasing, to stop asserting a behaviour no mechanism produces. |

**Both resolutions amend a frozen document.** There is no third option that
closes the issue without touching the Architecture Freeze.

#### Why `06` is uniquely affected

`04_discovery_engine.md`, `05_recommendation_engine.md` and
`07_consultation_request.md` are also absent from the assembly order, but each
has a workflow counterpart carrying a full step sequence — `discovery.md` has
six steps, `consultation.md` has six — so their omission is de-duplication, not
loss. `06` has **no workflow counterpart by explicit design**.

> **Correction (2026-08-09).** An earlier version of this entry stated that
> `consultation.md` *"consumes qualification rather than performing it"* and that
> *"its declared input is 'Qualified lead'"*. **Both claims are false.**
> `consultation.md`'s Inputs are *Recommendation Summary, Customer Information,
> Company Knowledge*; "Qualified lead" appears in its **Outputs**.
> `consultation.md` **produces** a qualified lead. Its **Prerequisites**
> (*business type, requested service, business goals, primary challenges*) also
> map closely onto `06`'s **Qualification Criteria**, so the qualification
> information-gathering is operationalised inside an already-assembled slot.
> This removed the producer/consumer gap the finding originally rested on.

An earlier argument that workflow **Dependencies** lists prove `06` must be
injected was withdrawn: `consultation.md` lists *"Discovery Workflow"* as a
dependency, and §4 explicitly says non-active workflows appear *"only as an
index"*. A Dependencies entry therefore does not imply injection.

#### Why the behavioural premise did not survive review

The finding's last surviving pillar was that `06`'s *"Not Qualified"* branch had
no delivery path. It does:

- **`09_fallback_responses.md` (assembled, slot 5)** lists Fallback Scenarios
  including *"Unsupported requests"*, *"Questions outside the Knowledge Base"*
  and *"Requests requiring human assistance"*. A prospect whose need does not
  match the business is an unsupported request.
- **`core/guardrails/escalation.md` (assembled, slot 4)** escalates when *"The
  AI cannot confidently answer after clarification"* or *"A human is better
  suited to resolve the situation."*
- **`06`'s own Notes** state its purpose *"is not to filter people out… [but] to
  ensure that users receive the most appropriate next step"* — which is exactly
  what those two assembled slots produce.
- **`discovery.md`'s Decision Point** (*"Otherwise: continue asking relevant
  discovery questions"*) already implements `06`'s *"More Information
  Required"* outcome.

So two of `06`'s three outputs are already live in assembled content and the
third is delivered behaviourally. What `06` uniquely contributes is a **naming
vocabulary**, not an unimplemented behaviour.

#### Two further corrections to earlier analysis

1. **Prompt section structure does not predict assembly.**
   `09_fallback_responses.md` and `10_tool_instructions.md` are assembled and
   share `04/05/06/07`'s exact shape. There is no "unassembled family".
2. **`docs/architecture.md:42–55` provides no support for assembling `06`.**
   Its example list — *"Personality, Mission, Conversation Rules, Discovery,
   Recommendation, Lead Qualification"* — also names Discovery and
   Recommendation (`04`, `05`), which are indisputably delivered via workflows.
   If that list implied assembly it would demand slots for those too. It
   describes the directory, not the assembly order.

#### Evidence sweep — no product requirement exists

A repository-wide sweep for an explicit product or business requirement that an
agent must reject or decline an unqualified prospect, or must emit `06`'s
three-valued outcome, returned **nothing**. `"Not Qualified"` and `"More
Information Required"` appear nowhere outside `06` itself; `projects/` contains
no qualification vocabulary at all; and no `must`/`shall` sentence anywhere ties
a requirement to declining a prospect. The nearest candidate,
`core/workflows/crm_sync.md`'s *"Disqualified"*, is explicitly labelled
**"Examples"**, describes a CRM record status rather than agent behaviour, and
does not match `06`'s vocabulary.

**If that business requirement is ever established, this entry should be
re-opened** — the correct owner would then be `core/workflows/recommendation.md`,
whose Decision Point is the Recommendation → Consultation boundary, **not**
`consultation.md`, whose purpose already presupposes a qualified prospect.

### PA-4 — §4 cites an assembly order in a section that does not exist

**Class: Documentation / Reporting** · **Non-blocking**

`runtime-specification.md` §4 row 1 says the bundle is built *"per the assembly
order in the Runtime Architecture"*. `docs/architecture.md` contains no assembly
order; its "High-Level Architecture" is a conceptual pipeline (Prompts →
Knowledge Base → Reasoning → Workflows → Tools → Response) that the §4 order is
consistent with but does not restate.

Nothing is ambiguous — **the order is stated inline and in full in §4 row 2**,
which is the authoritative text. Only the cross-reference is dangling. Recorded
so a future reader does not go looking for a section that was never written.

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

**Class: Closed** · Migration note, not a defect

`valid` is now conjunctive (no blocking issues **and** complete coverage).
Callers wanting the older, narrower question must use `has_blocking_issues`.

**Closed 2026-08-07.** This entry was recorded while the Project Loader did not
yet exist, and it was left open pending that module. The Loader is now
feature-complete and does not consume `ValidationResult` at all — it performs no
validation, by design. The migration therefore completed with zero affected
consumers, and the concern the entry was holding open no longer exists.

---

## Found during Runtime Module 10 (Provider Registry), 2026-08-31

### PR-1 — §10.10 and §13.10 disagree about which providers must be registered

**Class: Architecture Issue** · Recorded under system-owner ruling D-9(d);
Module 13 deliberately **not** modified.

Two frozen clauses do not describe the same scope:

| Source | Says |
|---|---|
| **§10.10** | "A project must never route to **an unregistered provider** — caught as a configuration error at Validation Layer time, not mid-conversation." |
| **§13.10** | "Config's declared **LLM provider** is registered in the Provider Registry." *(singular)* |
| **§10.1 / §10.9** | The **secondary is a routing destination**: "with secondary-provider fallback"; "Primary fails → attempt configured secondary". |
| [KI-4](known-issues.md) | "a Validation Layer rule that **a project's declared provider** must be registered." *(singular)* |

`ConfigProviderRegisteredRule` reads `llm_provider.primary` only, matching
§13.10 and KI-4. So a project may declare an **unregistered secondary**, pass
validation, activate, and then reach that secondary mid-conversation on the
first transient primary failure — the precise outcome §10.10 forbids.

**Why it is not fixed here.** Closing it means changing the Validation Layer,
which was explicitly out of scope for the Module 10 milestone. The scope
disagreement is also between two frozen documents, so which one yields is a
system-owner decision, not an implementation choice.

**Current behaviour, and why it is not dangerous today:** an unregistered
secondary is simply not found, and `generate_with_fallback` raises
`AllProvidersFailedError` — §10.9's "if none configured or it also fails"
branch. Nothing routes to an unregistered adapter; the defect is that the
condition surfaces mid-conversation instead of at validation time.

**Options when this is taken up:**

| Option | Consequence |
|---|---|
| Extend `ConfigProviderRegisteredRule` to check the secondary | Smallest change; modifies a committed rule and its tests |
| Add a separate rule and code beside `CONF005` | Purely additive; two rules covering one clause |
| Amend §13.10 to name both | Amends a frozen document |

Pinned by `test_d9_the_secondary_is_not_validated_and_the_gap_is_recorded`.

---

### PR-2 — The declared Model is required at routing time but not at validation

**Class: Documentation / Reporting** · Behaviour is correct and tested; what is
open is that the Validation Layer does not enforce the same precondition.

Ruling D-1(b) routes on `provider_id` and then asserts the resolved adapter's
bound `model_id` equals the project's declared **Model**. An **absent or
placeholder** Model fails that assertion — it is the same comparison, not a
special case, and it is the fail-closed direction: the alternative is routing a
project's traffic to a model nothing confirmed it chose.

The consequence is a seam: `ConfigProviderDeclaredRule` requires only the
**Primary** to be a real value (its recommendation text says "Set the Primary
provider and Model", but the check reads `primary` alone). A project declaring a
registered Primary and no Model therefore **passes validation and fails at
`get_provider`** — a configuration error surfacing later than §10.10's activation
gate intends.

Both repository projects currently declare placeholder Primaries, so neither
reaches this state today; both fail `config.llm_provider_declared` first.

**Not fixed because:** the remedy is a Validation Layer change, the same
out-of-scope module as PR-1, and the two are best decided together. The
alternative — skipping the model check when no Model is declared — was rejected
as fail-open: "could not be checked" has never counted as "passed" in this
framework.

Pinned by `test_d1_an_undeclared_model_is_refused`.

---

### PR-3 — `ProviderRequest` is deferred, its ownership reserved

**Class: Additive Extension** · Recorded under system-owner ruling D-8(b).

The frozen Data Models table defines `ProviderRequest` (`promptBundle`,
`conversationHistoryWindow`, `providerCapabilitiesUsed`) and names the
**Provider Registry its sole writer**. It is deliberately **not implemented**:

* no clause requires it to be constructed — §10.6's two members neither accept
  nor return it, and §9.6's `generate` does not take it;
* nothing reads it — §15 names it nowhere, listing only "structured event
  objects (type, `project_id`, `conversation_id`, payload)";
* built now it would be a **PII-bearing object with no consumer and no
  retention rule**, holding the full assembled prompt while §15.3 forbids
  logging "raw credentials or PII beyond what Compliance's data-handling rules
  allow".

Deferring costs nothing: the frozen table reserves sole ownership to this
module, so no other module can claim it in the meantime. Its natural moment is
when Observability defines what may be recorded.

Note for that work: `providerCapabilitiesUsed` is the field that would record
*which provider's capabilities the bundle was actually budgeted against* — the
one residual worth capturing from the failover path, where a bundle budgeted
for the primary is delivered to the secondary.

Pinned by `test_d8_provider_request_is_not_implemented`.

---

## Found during Runtime Module 11 (Tool Executor), 2026-08-31

All seven were identified in the Module 11 pre-implementation audit and recorded
under explicit system-owner rulings. None is fixed in this milestone.

### TE-1 — `ToolRequest` exists as a type with no writer

**Class: Documentation / Reporting** · Ruling D-1(a).

The frozen Data Models table names the **Workflow State Manager** `ToolRequest`'s
sole writer. Nothing in the implemented runtime produces one:

* `WorkflowRouter.route()` returns only a `WorkflowTransitionDecision`
  (`target_workflow`, `collected_data`);
* `WorkflowState` carries four fields, none tool-related;
* the one provider adapter declares `tool_calling_support=False`, and §9.11
  defers native tool-calling *"once Tool Executor integrates with providers
  offering it"*.

That last point is circular in the frozen specification itself: provider
tool-calling waits for the Tool Executor, while the Tool Executor's input waits
for a producer. **Neither side can move first without a decision.**

The type is defined because §11.6's frozen signature cannot be written without
it. Module 11 never constructs one — pinned by
`test_the_executor_never_constructs_a_tool_request`.

**Not fixed because:** giving Module 7 a tool vocabulary means deciding *when a
workflow calls for an action*, which the workflow definitions express only as
prose. That is a separate authorization.

---

### TE-2 — §11.12(c)'s retry scenario is unenforceable; no retry is implemented

**Class: Architecture Issue** · Ruling D-5(a). Only the system owner can supply
a policy, and closing it may require amending a frozen document.

§11.2 and §11.9 defer to *"the error-handling behavior already documented in
each tool contract"* and to *"policy"*. The complete text of that documented
policy, across all five contracts:

| Contract | Retry text, verbatim |
|---|---|
| `crm.md` | "Retry only when appropriate." |
| `calendar.md` | "Retry only when appropriate." |
| `email.md` | "Retry only when appropriate." |
| `integrations.md` | "Retry when appropriate." |
| `consultation_form.md` | "Retry according to business rules." |

**No count, no backoff, no ceiling, no definition of "appropriate", and no
artifact named "business rules" exists anywhere in the repository.**

A retry policy invented to satisfy §11.12(c) would not be a convenience — it
would re-send a customer's email and re-create a CRM record, violating the same
contracts' *"Avoid sending duplicate emails"* and *"Never create duplicate
records intentionally"*. **A side-effecting operation is never retried merely
because its failure looked transient.**

The executor therefore attempts exactly once and surfaces the first failure, and
§11.12(c) is recorded as unimplementable rather than faked. Pinned by
`test_the_tool_is_called_exactly_once_on_failure` and
`test_no_retry_machinery_exists_in_the_source`.

**To close it:** the system owner supplies a deterministic policy (which failure
classes, how many attempts, what backoff, and how idempotency is established per
contract), or the tool contracts are amended to carry one.

---

### TE-3 — §11.2's literal integrations path is not executable, and §11.9's Resolver cross-reference does not match the committed Resolver

**Class: Architecture Issue** · Rulings D-3(b) and D-4(a). Continues [L-4](#l-4).

Two related divergences, recorded together because they share one root.

**(a) The §11.2 resolution path.** §11.2 says: *"resolve the project's configured
concrete provider from `ResolvedContext.integrations`."* That mapping holds raw
Markdown `ProjectDocument`s, and the real project's provider values are English
sentences ("Practice management software's built-in patient CRM"). Interpreting
them in Module 11 is ruled **Invalid** twice: ADR 0004 reserves parsing to the
Project Loader, and L-4 rejects both re-implementing the Validation Layer's
substring search and depending on that layer.

So Module 11 resolves implementations by **explicit registration under a
contract name**, and the literal §11.2 wording is **not implemented**. The
integrations document informs a human operator wiring the process; it does not
steer the runtime.

**(b) The §11.9 cross-reference.** §11.9 requires the capability-unavailable
outcome to be *"consistent with the Resolver's differentiated Integrations
handling."* The committed Resolver is **not** differentiated when integrations
are present — `resolve_integrations` returns `frozenset()` with the committed
rationale that *"Deciding which individual tool has a configured provider is
explicitly the Tool Executor's responsibility."* Module 11 then has no per-tool
data and may not parse for it.

Three documents assign the determination to three different parties, and no data
path connects any of them. Module 11 therefore treats a contract as unavailable
when **no implementation is registered for it**, and does not use
`degraded_capabilities` as a per-tool mechanism.

**To close it:** typed integration resolution in the Project Loader, per L-4's
one **Correct** option — a separately authorized change to Modules 2 and 3.

Pinned by `test_the_executor_does_not_parse_integration_markdown` and
`test_b_availability_is_what_was_registered`.

---

### TE-4 — `ToolResponse` has no diagnostic channel

**Class: Documentation / Reporting** · Consequence of the frozen four-field
model.

`ToolResponse` is frozen at `success, data, errorType, capability_unavailable`.
A failure therefore carries its normalised class and **nothing else** — no
message, no cause, no provider detail.

Detail is deliberately not smuggled through `data` either: a concrete tool's
exception text is the same credential-bearing channel the provider layer
already goes to lengths to redact (a vendor exception "whose message and request
URL may carry the credential"), and §11.3 forbids credentials crossing this
boundary. Pinned by `test_d_a_raising_tool_leaks_no_exception_detail`.

**Consequence for Observability:** when §15 is built it will be able to record
*that* a tool failed and in which class, but not *why*. If richer diagnostics
are wanted, they belong in an audit event emitted alongside the response — not
in a fifth field on a frozen model.

---

### TE-5 — No path from a tool result back to the model

**Class: Architecture Issue** · Ruling D-10(a). **For Module 14 to settle.**

§14.2 orders the pipeline: *"…provider call → post-response guardrail check →
workflow routing/state commit → **tool execution** → response delivery…"* — tool
execution runs **after** the answer has been generated and guardrail-checked,
and the pipeline contains **no second generation pass**.

A tool result therefore cannot influence what the customer is told on that turn.
Module 11 implements exactly what §11.6 declares: one request, one response, no
loop, no batching, no parallelism, no second provider call.

Whether that is intended — fire-and-forget side effects, which is precisely what
`core/workflows/crm_sync.md` describes — or an omission that a tool-use loop
would have to fill, **§14 does not settle**. It is recorded here so the Runtime
Engine milestone decides it deliberately rather than discovering it.

Pinned by `test_no_async_batching_or_parallel_surface_exists`.

---

### TE-6 — `core/tools/` declares mutual dependency cycles

**Class: Architecture Issue** · Ruling: **record, do not fix.** `core/` is out of
scope for this milestone.

The five tool contracts' Dependencies sections point at each other:

| File | Declares as dependencies |
|---|---|
| `integrations.md` | CRM Tool, Calendar Tool, Email Tool, Consultation Form Tool |
| `crm.md` | Consultation Form Tool, Consultation Workflow, Follow-up Workflow, **Integration Tool** |
| `calendar.md` | Consultation Workflow, CRM Tool, Email Tool, **Integration Tool** |
| `email.md` | Consultation Form Tool, CRM Tool, **Integration Tool** |
| `consultation_form.md` | Consultation Workflow, **CRM Tool**, **Email Tool**, Integration Tool |

Cycles present: `integrations` ↔ each of the other four; `crm` ↔
`consultation_form`; `email` ↔ `consultation_form`.

**This is the same defect class as [KI-1 and KI-2](known-issues.md)**, both
resolved — for `core/workflows/` and `core/guardrails/` respectively — by
defining that dependencies are what a module *requires as input*, with the
consuming side declaring the relationship one-directionally. **That definition
was never applied to `core/tools/`**, and the cycles were recorded in no
register until now.

**Not blocking Module 11:** §11 never reads a tool contract's Dependencies
section, and the executor does not resolve inter-tool ordering. This is a
documentation-level defect in a frozen artifact.

**No dependency-resolution mechanism has been invented.** What the Dependencies
sections mean for tools needs the same architectural ruling KI-1 gave workflows.

---

### TE-7 — `ToolRequest.project_id` is never checked against `ResolvedContext.project_id`

**Class: Architecture Issue** · Raised for ratification; deliberately **not**
implemented.

§11.4 takes both a `ToolRequest` (carrying `project_id`) and a `ResolvedContext`
(carrying its own `project_id`). **Nothing in §11 requires them to agree, and
Module 11 does not check.**

A mismatch would execute one project's tool call against another project's
resolved context — one clinic's appointment written with another clinic's
configuration. The failure would be silent, which is the class this framework has
removed repeatedly (`ModelBinding`'s T-1 identity check exists for exactly this
shape of hazard on the provider side).

**Why it is not implemented:** adding the check introduces a failure mode §11
does not describe, and the authorization for this milestone was explicit that no
additional behaviour be invented. It is recorded rather than added quietly.

**To close it:** a ruling on whether `execute()` must refuse a mismatch, and if
so whether that is a `capability_unavailable` decline, an `INVALID_REQUEST`
failure, or a raised error — noting that §11.5 makes `ToolResponse` the module's
only output.

---

## Found during Runtime Module 14 (Runtime Engine), 2026-09-01

Seven entries, all recorded under explicit system-owner rulings. None is fixed
in this milestone.

**Two questions the milestone settled rather than left open**, noted here so
neither is rediscovered as a defect:

* **Pipeline order.** The implementation authorization sketched the tool stage
  *before* workflow routing. §14.2 orders them the other way — *"post-response
  guardrail check → workflow routing/state commit → tool execution → response
  delivery"* — and the frozen clause was followed. Pinned by
  `test_the_pipeline_order_matches_the_frozen_sequence`.
* **Activation.** No public `activate()` was added. §14.6 declares one member,
  and activation is enforced at construction: `RuntimeEngine.__init__` refuses a
  `ValidationResult` that is not for this project, is not a project result, or is
  not valid. The activation state is the existing `ValidationResult` +
  `ResolvedContext` pair — no new model was introduced.

---

### RE-1 — Module 4 still accepts an unbudgeted assembly, and §14 must never use it

**Class: Architecture Issue** · Ruling D-1(b).

`PromptAssembler.__init__` defaults `token_budget=None`, and `_select` then
returns *all* Knowledge candidates and the *entire* history window without
counting anything, under an inline `# Phase 1: all of them.`

**Corrected 2026-09-01, after the §14 post-implementation audit.** An earlier
revision of this entry described the whole default as an unspecified fail-open
behaviour of the same shape as **V-1**. That overstated it, and the distinction
matters:

* **Selecting every Knowledge section is specified behaviour.** §5.2 assigns the
  Token Budget Manager the responsibility to *"select which Knowledge sections
  to include (**Phase 1: all of them**; later: retrieval-based)"*, and
  `runtime/assembler/ports.py` cites exactly that clause when defending the
  default. Returning all Knowledge is the Phase-1 behaviour the specification
  describes, not an invention.
* **The genuine concern is narrower**: the default also returns the **entire
  conversation history unmeasured**, and applies **no fixed-overhead budgeting**
  at all. Neither is covered by §5.2's Phase-1 sentence, which speaks only to
  Knowledge. §5.2 additionally requires the module to *"estimate Core + Branding
  + active Workflow overhead; compute remaining budget"* — and the absent-port
  path does none of that.

So the defect is the unmeasured history window and the missing overhead
computation, not the Knowledge selection.

Making the port required means editing Module 4 and roughly half of its
1,179-line committed test suite, which the authorization placed out of scope.

**What §14 does instead (ruling D-1(b)):** `RuntimeEngine.__init__` takes
`token_budget` as a required keyword argument with no default,
`PromptAssemblyStage` is the only place an assembler is constructed, and a
structural test asserts every `PromptAssembler(...)` call in
`runtime/runtime_engine/` passes `token_budget=`. **§14 therefore always
supplies a `TokenBudgetPort` and cannot reach Module 4's unbudgeted branch.**

**What remains open:** any *other* caller still can. The defect is scoped, not
removed.

**To close it:** make `TokenBudgetPort` a required argument of
`PromptAssembler`, and update Module 4's tests — a separately authorized change.

---

### RE-2 — `RuntimeRequest` is framework-introduced

**Class: Documentation / Reporting** · Approved by ruling.

§14.6 is `handleRequest(request) -> RuntimeResponse` and §14.4 defines the input
as *"Incoming request (`project_id`, `conversation_id`, message, channel)"* — but
the frozen Data Models table names **neither** `RuntimeRequest` nor
`RuntimeResponse`. The four request fields are authoritative; the type name is
introduced by this milestone, as is `RuntimeResponse`'s four-field shape, which
was ruled minimal.

Recorded so a later reader does not mistake either type for a frozen model. Both
live in `runtime/models/` with the same conventions as every other model.

---

### RE-3 — §14 establishes no concurrent runtime contract

**Class: Architecture Issue** · Ruling: §14 must not introduce concurrency.

One request is executed start to finish on the calling thread. There is no
async surface, no thread, no executor, no pool and no lock in
`runtime/runtime_engine/` — pinned by `test_18_no_concurrency_machinery_exists`.

**This does not make the repository thread-safe, and must not be read that way.**
Measured at this milestone:

| Component | State held | Guarded? |
|---|---|---|
| `WorkflowStateManager` | per-conversation workflow state | ✅ per-conversation locks (§7.10) |
| `SessionManager` | conversations and sessions | ❌ none |
| `ProviderRegistry` | registered adapters | ❌ none |
| `ToolExecutor` | registered tools | ❌ none |
| `CoreLoader` | process-lifetime cache | ❌ none |
| Validation rules | shared singletons | ❌ none (**V-7**) |
| Provider adapter | `_last` serialized prompt | ❌ none (**S-1**) |

**§7.10 is the only atomicity clause in the entire specification.** Running this
engine concurrently is unsupported. **V-7** and its ADR 0003 deadline
(*"before Runtime Engine adds concurrency"*) remain open, as does the §12
concurrency asymmetry.

---

### RE-4 — The default runtime keeps no audit trail

**Class: Architecture Issue** · Ruling D-4(a).

§14.2 ends its pipeline with observability logging and §15 is not implemented.
§14 defines a minimal `ObservabilitySink` Protocol — `record(event_type,
project_id, conversation_id, payload)`, taken from §15.4's stated inputs — and
defaults to `NullObservabilitySink`, which does nothing.

The engine emits exactly one event per turn, including for blocked and degraded
turns, and guards the call so a sink failure never blocks the conversation
(§15.9). The payload carries only outcome facts — never the message, the prompt
or the answer — because §15.3 forbids logging PII beyond an allowance nobody has
written.

**The gap is the default.** §15.9 also says a silent audit-logging gap *"is
itself a Compliance risk"*, and running on `NullObservabilitySink` is exactly
that. The seam is real; the recorder is not built.

**To close it:** implement §15. The Protocol here is §14-local and expected to be
replaced, not extended.

---

### RE-5 — §14 composes no customer-facing fallback text

**Class: Architecture Issue.**

When a turn is blocked, escalated or degraded, `RuntimeResponse.text` is empty
and the flags carry the outcome. `RuntimeResponse.__post_init__` refuses a
blocked response that carries text at all.

§8.3 assigns composing a safe alternative outside the Guardrail Engine, and
§14.12(c) speaks of *"a clean degraded response"*. But the phrase "technical
difficulties" appears exactly once in this repository — in §10.9 — and
`core/prompts/09_fallback_responses.md` contains no technical-failure entry and
no selection mechanism. Its content is prose written for a model to follow, not
strings a runtime can pick from.

So §14 emits flags and no wording. **Composing what the customer reads currently
belongs to the channel adapter**, which §14.5 places outside this specification's
scope — and nothing states that explicitly.

**To close it:** either a mechanism that selects a Core fallback response, or an
explicit ruling that the channel adapter owns the wording.

---

### RE-6 — A blocked answer is not recorded as an agent turn

**Class: Documentation / Reporting.**

The Session Manager's contract prescribes appending the agent's turn *"again
afterwards with the response"*. §14 does so only in the delivery stage, which a
guardrail block short-circuits before reaching.

The reasoning: a response the customer never saw must not become an agent turn
that the next turn's prompt shows the model as delivered. The alternative would
feed a blocked answer back into the conversation as though it had been sent.

§14 states no rule either way, and neither does §12. The consequence is that the
durable record contains the user's turn but no agent turn for a blocked turn —
which an auditor should know, since it means the conversation record alone does
not show that a block occurred. That information lives only in the observability
event, which the default sink discards (RE-4).

---

### RE-7 — §14 publishes no `handleRequest` alias, and the convention is unsettled

**Class: Documentation / Reporting.**

The frozen specification writes every public member in camelCase —
`handleRequest`, `getProvider`, `validateCore`, `execute`. Twelve modules render
them snake_case. **The Validation Layer is the only module that also publishes
camelCase aliases** (`validateCore`, `validateProject`, both `# noqa: N815`).

§14 does **not** add one: no ruling sanctioned the convention repository-wide,
and adding an alias here would make §14 the second module of fourteen to differ.
`RuntimeEngine.handle_request` is the only public member.

**To close it:** rule the convention once — either every module publishes the
frozen camelCase name, or the Validation Layer's aliases are the anomaly.

---

## Found during the §14 post-implementation audit, 2026-09-01

Seven findings from the architecture gate run against commit `20bf9c6` after
§14 was committed. **This entry records findings and decisions only. Nothing
below is fixed, and no AUDIT issue is resolved.**

A note that shapes three of them: **AUDIT-1, AUDIT-2 and AUDIT-4 share one
cause.** There is no production composition root, so nothing owns the invariants
such a root would naturally hold — that the budget describes the provider that
will be called, and that a project's state collaborators are its own. Building
the root (AUDIT-4) is what makes the other two structurally impossible rather
than merely documented.

---

### AUDIT-1 — The budget and the provider are never proven to describe the same model

**Severity: High** · **Class: latent architectural hazard / composition
responsibility** · ✅ **RESOLVED 2026-09-01** — globally, not only on the
production path. See the resolution at the end of this entry; the analysis is
retained because it is why the fix took the shape it did.

`RuntimeEngine.__init__` accepts `token_budget` and `providers` as **independent
arguments** and never cross-checks them. An engine can therefore be constructed
whose Token Budget Manager is bound to one model while the Provider Registry
resolves another — reproduced during the audit, with a budget bound to
`other/other-m` while the registry resolved `fixture_provider/fixture-model-1`.

This re-opens, one level up, the invalid state **T-1** exists to make
unconstructible. `runtime/provider/binding.py` names it exactly: *"Module 5 would
count every string precisely, against the wrong vocabulary, and report success…
a wrong answer that looks exact."* `ModelBinding` forbids the mismatch *inside*
an adapter; §14 does not carry that guarantee across its own constructor.

**Not reachable through any committed production path.** No production code
constructs a `RuntimeEngine`; the only assembly is a test helper, which always
derives the budget from the adapter. The hazard is available to a future caller,
which is precisely what the composition root will be.

**Blast radius, measured rather than assumed.** The dangerous direction — a
budget sized against a far larger window than the real provider's — was tested
and produced a **degraded** turn with **zero calls reaching the provider**: the
adapter's own C-1a assertion fired, as the conformance suite requires of every
adapter. What is *not* caught is an over-conservative window (silently drops
Knowledge that would have fit) or a wrong tokenizer against a similar window
(silently miscounts). Those degrade quality with no signal.

**Canonical future resolution (accepted, not implemented):** derive the budget
from the provider selected for the activated project, through its existing
`ModelBinding`. §5.4 already lists the budget's window as coming *"via Provider
Interface's capability query"* and §5.7 grants Module 5 that dependency, so this
is the specified relationship rather than a new one. `ProviderRegistry.register`
already requires `ModelBoundProvider`, so `get_provider(...).model_binding()`
yields a tokenizer and capabilities that provably describe one model.

**Explicitly rejected:** adding provider identity to `TokenBudgetPort` — that
would make Module 4 provider-aware and invert the direction
`runtime/provider/binding.py` was written to protect. Also rejected: a second
`ModelBinding`-like abstraction; the existing one suffices.

**Resolution — `token_budget` was removed from `RuntimeEngine.__init__`.**

The engine now derives the budget itself, after the activation gate:

```python
binding = providers.get_provider(resolved_context).model_binding()
token_budget = TokenBudgetManager(
    tokenizer=binding.tokenizer,
    capabilities=_BoundCapabilities(binding.capabilities),
)
```

**The absence of the parameter is the invariant.** There is no argument through
which any caller — the composition root, a test, or future code — can supply a
budget for a different model. That makes the resolution **globally impossible**
rather than a guarantee of the production path only, which is why it was done in
the constructor instead of in `activate`.

`_BoundCapabilities` is a private six-line adapter inside `engine.py`, present
only because `ModelBinding` holds `capabilities` as an attribute while
`ProviderCapabilityPort` requires a method. **No frozen interface, no Module 4
contract and no Module 5 contract was modified.** Identity was not added to
`TokenBudgetPort`; no second binding type was created; T-1 is extended, not
bypassed.

Two consequences worth recording:

* **Provider misconfiguration now fails at construction**, not on a customer's
  first message — which is what §10.10 asks for. `test_8_a_provider_the_project_
  does_not_declare_fails_at_construction` pins it.
* **The activation gate still runs first**, so an unvalidated project is refused
  as unactivated rather than as a provider problem
  (`test_8_the_activation_gate_still_precedes_provider_resolution`).

Provider resolution during construction is a registry lookup plus the declared-
model assertion — both offline. `test_activation_makes_no_provider_call` proves
no provider call occurs.

Proven by `test_6_no_budget_can_be_injected_through_the_constructor`,
`test_6_the_budget_is_derived_from_the_resolved_providers_binding`,
`test_6_a_mismatched_budget_can_no_longer_be_constructed` and
`test_the_provider_bound_budget_invariant_survives_activation`.

---

### AUDIT-2 — Cross-project session and workflow-state contamination

**Severity: High** · **Class: latent architectural hazard** · ✅ **RESOLVED
2026-09-01 for the production activation path.** **Not globally impossible** —
the distinction is stated in the resolution at the end of this entry and must
not be collapsed.

Two `RuntimeEngine` instances serving different projects, sharing one
`SessionManager` and one `WorkflowStateManager`, and receiving a colliding
`conversation_id`, will interleave their conversations. Reproduced during the
audit:

```
conversation project_id recorded as: fixture_clinic
    user  | A asks
    agent | answer from project A
    user  | B asks          ← project B's turn, in project A's conversation
    agent | answer from project B
```

Project B's next prompt would then contain project A's message and answer, and
`ConversationContext.project_id` continues to name project A.

**Not reachable through an existing production composition path**, because no
production composition root exists to share the collaborators. Requires both a
shared store and an id collision; nothing currently documents that either is
forbidden.

**Not introduced by §14.** §12.6 and §7.6 are frozen and key *every* method on
`conversation_id` alone; the managers have always been project-agnostic. §14 is
simply the first module from which the hazard is reachable.

**Canonical isolation rule (accepted):**

> A `conversation_id` namespace belongs to exactly one project. `SessionManager`
> and `WorkflowStateManager` are scoped to exactly one activated project.

The future composition root constructs them per project, which makes the
collision structurally impossible without touching a signature. `RuntimeEngine`
may additionally enforce project ownership at the `SessionStage` boundary as
defence in depth — it already knows its own `project_id`, and
`ConversationContext.project_id` already exists.

**Frozen Module 7 and Module 12 interfaces must not change** to satisfy this.
Adding `project_id` to their methods would amend §7.6/§12.6; constructor-level
scoping was considered and set aside in favour of the root, which changes no
committed module at all.

**Resolution — `runtime/runtime_engine/activation.py` constructs them per
activation.**

`activate(core, projects_root, project_id, providers)` builds a fresh
`SessionManager` and a fresh `WorkflowStateManager` for every activation, and
**neither is a parameter**. There is no way to hand the same store to two
projects through the production path. Neither frozen signature changed; the
managers remain project-agnostic and the *scoping* carries the guarantee.

**The limit of this resolution, stated precisely.** `RuntimeEngine.__init__`
remains public and still accepts `sessions` and `states`. A caller who bypasses
`activate` can still share stores across two engines and reproduce the original
interleaving. So:

| | |
|---|---|
| **Production activation path** | contamination is **structurally impossible** |
| **Low-level `RuntimeEngine` constructor** | escape hatch **remains open** |

That escape hatch is deliberate — the constructor is the seam tests and future
callers use directly, and closing it would mean either hiding the constructor or
making the managers project-aware, which §12.6/§7.6 forbid. **This entry does
not claim global impossibility.**

The approved defence-in-depth measure — `SessionStage` verifying
`ConversationContext.project_id` against the activated project — was **not
implemented**, because the composition root alone satisfies the canonical rule
and `stages.py` was outside the authorized scope. It remains available if the
escape hatch is later judged unacceptable.

Proven by `test_each_activation_constructs_fresh_collaborators`,
`test_colliding_conversation_ids_stay_isolated_across_activations` and
`test_activation_accepts_no_budget_session_or_workflow_argument`.

**Test-coverage limitation, recorded honestly:** only one project in this
repository is activatable — both production projects fail validation — so the
isolation test exercises **two activations of one project** rather than two
project names. The mechanism under test is per-activation collaborator scoping,
which is what the isolation actually rests on; a second valid fixture would
have required creating files outside the authorized scope.

---

### AUDIT-3 — `transition_history` grows with no-op entries

**Severity: Low** · **Class: Runtime Improvement** · **Owner: Module 6/7** ·
**Deferred.**

Three turns produce `('None->discovery', 'discovery->discovery',
'discovery->discovery')`. The Workflow Router returns "stay" on every turn after
the first, and §14 commits each decision, so per-conversation history grows
linearly with turn count and is mostly noise.

**§14 must not decide whether no-op transitions should be retained.** Filtering
them in the engine would mean §14 deciding what counts as a real transition —
§14.3's *"maintainability red flag"*. Whether `transition_history` is an audit
log (keep every commit) or a state history (keep changes only) is a question §7
does not answer, and it belongs with Modules 6 and 7.

---

### AUDIT-4 — No production composition/activation root

**Severity: Medium** · **Class: architecture decision / implementation
follow-up** · ✅ **RESOLVED 2026-09-01** — `runtime/runtime_engine/activation.py`
exists, is tested, and is the documented production activation path.

Nothing in `runtime/` assembles an activated engine. The chain

```
filesystem → CoreLoader / ProjectLoader → Resolver → Validator
           → ProviderRegistry / adapter → TokenBudgetManager
           → project-scoped SessionManager + WorkflowStateManager
           → RuntimeEngine
```

is performed today only by a test helper. Consequently §14 owns the *session*
half of §14.2's first step ("resolve project + session") and not the *resolve*
half, and every edge a composition root would own is currently the caller's.

**Planned solution:** `runtime/runtime_engine/activation.py`, whose
responsibility is exactly: load → resolve → validate → reject an invalid project
→ resolve the provider → derive the budget from that provider's `ModelBinding`
→ construct a project-scoped `SessionManager` → construct a project-scoped
`WorkflowStateManager` → construct the `RuntimeEngine`.

It must preserve dependency direction, and **must not become a second
orchestrator for request handling** — §14.1 names one module that calls the
others in sequence, and `handle_request` remains that path.

**Resolution — the root is one function, and owns construction only.**

```python
activate(core, projects_root, project_id, providers) -> RuntimeEngine
```

It loads the project, resolves it, validates it with the real Validation Layer,
and constructs the engine with project-scoped collaborators. `core` arrives
already loaded because the frozen `CoreBundle` row says it is *"created once at
process startup"* — loading it per project would re-read `core/` once per
project.

No `ActivationManager`, no factory class, no container, no engine cache, no
module-level state — `test_activation_holds_no_module_level_state` forbids all of
it structurally. It is **not** a second orchestrator:
`test_activation_is_not_a_second_orchestrator` asserts it never calls
`handle_request`, `build_pipeline`, `generate`, a guardrail, the assembler, the
tool executor, a session or workflow write, or the observability sink.

The invalid case is refused by `RuntimeEngine`'s own activation gate rather than
by a second check here — §14.10 has one owner, and two implementations of one
precondition is how they drift apart.

**Dependency direction after the change:** `runtime_engine` now imports twelve
packages (`assembler, budget, guardrail, loader, models, provider_registry,
resolver, session, tool_executor, validation, workflow_router, workflow_state`)
and has **zero inbound** runtime edges — closer to §14.7's *"every other
module"* than before, with the root property intact.
`test_nothing_in_the_runtime_imports_activation` and
`test_the_engine_package_depends_only_downward` pin both halves.

**Known limitation:** `activate` takes exactly its four contracted arguments, so
the engine it returns holds an empty `ToolExecutor` and the null observability
sink. Both are correct today — nothing produces a `ToolRequest` (TE-1) and §15
does not exist (RE-4) — but when either changes, this signature is where the
wiring goes.

---

### AUDIT-5 — Channel semantics after the first turn

**Severity: Low** · **Class: documentation / semantic clarification** ·
**Deferred.**

`RuntimeRequest.channel` reaches `create_session` on the conversation's first
turn and the observability payload on every turn. A later request arriving on a
different channel does **not** replace the conversation's original channel.

That is the frozen model's behaviour, not a §14 defect: §12's data-model row
treats `channel` as conversation-level metadata established at creation, and
§12.6 exposes no method to change it. **No frozen `SessionManager` interface
should be changed merely for this finding.** Recorded so the semantics are
explicit rather than discovered.

---

### AUDIT-6 — A degraded turn always returns `escalate=False`

**Severity: Low** · **Class: deferred policy question** · **Owner: Module 8 /
Guardrail Engine.**

An internal failure contained by §14.9 produces `RuntimeResponse(degraded=True,
escalate=False)`. Whether a technical failure should summon a human is a policy
question §14 does not answer.

`core/guardrails/escalation.md` lists *"Technical issues exceed the AI's
capabilities"* among its Automatic Escalation Conditions — but that condition is
one of the ten the Guardrail Engine publishes in `UNENFORCED_CORE_CONDITIONS` as
having no deterministic evaluator. **The Runtime Engine must not invent
escalation policy for internal failures**: doing so would implement a guardrail
rule Module 8 declined to implement, against §14.3.

**§15 is not the owner either** — §15.3 makes it a pure recorder that *"must
never itself decide to block a request based on an observed pattern; that's
Guardrail Engine's job."* Escalation policy belongs to Module 8.

---

### AUDIT-7 — `RuntimeEngine` inspection surface

**Severity: Very Low** · **Class: API / documentation.**

§14.6 declares one public member; `RuntimeEngine` exposes three:
`handle_request`, plus the read-only properties `project_id` and `stage_names`.

**Decision: keep both, documented as framework-introduced inspection surface.**
They are read-only, mutate nothing, and removing them would push tests into
private attributes — a worse discipline than a documented property. Related to
**RE-7**, which records that §14 publishes no camelCase alias and that the
repository-wide naming convention is still unruled.

**Do not remove or rename them** without a separate ruling.

---

### V-7 — reconciliation after the §14 audit

**V-7 remains open and deferred. Its deadline has not arrived.**

An earlier reading held that the Runtime Engine's *existence* triggered ADR
0003's deadline. That is incorrect. The ADR's wording is specific:

> *"The forcing function is the Runtime Engine (Phase 2, later task), **which
> introduces concurrent request handling**. Until something validates two
> projects in parallel, the hazard is latent. It must be closed before that
> lands, not after."*

**§14 introduces no concurrency** — no async surface, no threads, no executor,
no locks, verified structurally and recorded as RE-3. The forcing function is
concurrent request handling or parallel validation, **not** the module existing.
V-7 must be addressed before either lands; §15 is not the trigger.

---

## Found during Runtime Module 15 (Observability / Audit Logger), 2026-09-01

### §15 implementation status, clause by clause

Recorded because §15 is **partially implemented**, and the parts that are not
must be visible rather than inferred from the fact that tests pass.

| Clause | Requirement | Status |
|---|---|---|
| 15.1 | one consistent interface for auditable events | **PASS** |
| 15.2 | accept structured events from any module | **PASS** — no central enum; any module may emit its own type |
| 15.2 | timestamp them | **PASS** — ISO-8601 UTC, matching `SessionManager`'s convention |
| 15.2 | tag with `project_id`/`conversation_id` | **PASS** |
| 15.2 | persist them | **PARTIAL** — in memory only, see **OB-1** |
| 15.2 | expose a query interface | **PASS** for the three ruled filters |
| 15.3 | pure recorder, never decides | **PASS** — structurally asserted |
| 15.3 | never logs raw credentials or disallowed PII | **PASS** — verified end to end |
| 15.4 | inputs: type, project_id, conversation_id, payload | **PASS** |
| 15.5 | persistence confirmation; queryable records | **PASS** — `log_event` returns the stored event |
| 15.6 | `logEvent` · `queryAuditLog` | **PASS** |
| 15.7 | leaf module | **PASS** — imports `runtime.models` and the standard library only |
| 15.8 | **durable**, ideally append-only store | **PARTIAL** — append-only ✅, durable ❌, see **OB-1** |
| 15.9 | store failure must not block the conversation | **PASS** |
| 15.9 | must raise its own alert/metric | **OPEN** — see **OB-3** |
| 15.10 | events immutable once written | **PASS** |
| 15.11 | structured export for compliance reporting | **DEFERRED** — future extension point |
| 15.12(a) | log and retrieve | **PASS** |
| 15.12(b) | unavailability doesn't block the flow | **PASS** |
| 15.12(c) | no raw credential in a payload | **PASS** |
| 15.12(d) | duplicate event ID rejected or versioned | **STRUCTURALLY UNENFORCEABLE** — see **OB-2** |

---

### OB-1 — Audit persistence is in-memory and therefore not durable

**Class: Architecture Issue** · Ruled for this milestone · **Open.**

§15.8 names the external dependency as *"a durable, ideally append-only log
store."* This milestone implements the seam — an `AuditLogStore` Protocol — and
one implementation, `InMemoryAuditLogStore`, following the pattern three
committed modules already use (`ProjectCache`, `SessionStore`,
`WorkflowStateStore`).

**Append-only is satisfied. Durable is not.** Events live for the process's
lifetime and are lost when it ends. §15.8 is therefore **partially met**, and
this entry exists so that is never read as satisfied.

Introducing SQLite, a database client, a filesystem store or any third-party
package was explicitly out of scope: `dependencies = []` still holds, and
choosing a persistence technology is an architectural decision, not an
implementation detail.

**To close it:** authorize a durable `AuditLogStore` implementation. The seam
requires no other change — `AuditLogger` takes any store satisfying the
Protocol, and `activate` is the single place the in-memory one is constructed.

Pinned by `test_a_durable_store_can_replace_the_in_memory_one` and
`test_the_store_is_a_protocol_with_an_in_memory_implementation`.

---

### OB-2 — §15.12(d)'s duplicate-ID scenario cannot arise, and is not faked

**Class: Documentation / Reporting** · Consequence of the ruled identity model.

§15.12(d) requires that *"a second write to the same event ID is rejected or
versioned, never overwritten."* But **the logger generates every event id**
(`uuid4().hex`, following `SessionManager`'s precedent) and a caller cannot
supply one: whatever `AuditEvent.event_id` holds on the way in is replaced.

So two writes can never share an id, and the scenario the clause describes
**cannot arise from outside this module**. No artificial duplicate detection was
written to make the clause appear satisfied — a check that can never fire is
worse than an honest absence, because it looks like protection.

Note what *is* satisfied: the store never overwrites, later writes never disturb
earlier events, and retrieved events are frozen. The immutability §15.10
actually requires holds; only the duplicate-detection framing of §15.12(d) is
inapplicable.

**This would change** if a future ruling let callers supply ids — at which point
duplicate rejection becomes both meaningful and required.

Pinned by `test_an_id_a_caller_puts_on_an_event_is_replaced`,
`test_logging_the_same_event_twice_produces_two_records` and
`test_no_duplicate_detection_was_written`.

---

### OB-3 — §15.9's audit-gap alert has no seam to be raised through

**Class: Architecture Issue** · **Open.**

§15.9 has two halves. The first — *"must not block the conversation from
proceeding"* — is satisfied: the Runtime Engine guards the logger call, and a
store that raises changes nothing about the `RuntimeResponse`.

The second is not: *"it must raise its own alert/metric, since a silent
audit-logging gap is itself a Compliance risk."*

**The repository has no metrics or alerting seam.** `logging` appears once, in
`validation/pipeline.py`, logging a rule id. Inventing a monitoring abstraction
or an external dependency to satisfy the wording was out of scope, and a
speculative one would be surface with no consumer.

The smallest honest seam identified — and **not** implemented, because it needs
a ruling — is a callback on the Runtime Engine's containment guard, invoked when
`log_event` raises. It changes no frozen contract and adds no dependency, but it
introduces a public abstraction §15 does not name.

**Until then a failing audit store is silent**, which is exactly the Compliance
risk §15.9 names. Pinned by `test_the_logger_raises_no_alert_of_its_own`.

---

### RE-4 — reconciliation

**Was:** *"The default runtime keeps no audit trail"* — the engine defaulted to
`NullObservabilitySink`, which discarded every event.

**Now: partially resolved.** `RuntimeEngine` requires an `AuditLog`; there is no
default and no null sink, so an engine that exists is an engine that records.
`activate` constructs a real `AuditLogger` per activation, so the production path
keeps a queryable trail.

**RE-4 remains open** on its durability half: the trail survives only as long as
the process (**OB-1**), and a failing store is still silent (**OB-3**). The
entry is not closed, because "keeps an audit trail" and "keeps a durable,
monitored audit trail" are different claims.

---

### The §14 placeholder was removed, not extended

`runtime/runtime_engine/ports.py` — which defined `ObservabilitySink` and
`NullObservabilitySink` — was **deleted**. Its own docstring said it would be:
*"§14-local: when §15 is built it owns the contract, and this Protocol is
replaced rather than extended."* The Runtime Engine now depends on
`runtime.observability.AuditLog` and owns no audit semantics: it builds an event
from the turn's outcome, hands it over, and contains any failure. It does not
generate identity, timestamp, store, query, filter, or decide retention.

---

## Notes

Nothing here is deleted once resolved; resolved entries keep their reasoning so
the decision history stays readable.
