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

**Fifteen open Architecture Issues: PR-1, TE-2, TE-3, TE-5, TE-6, TE-7, RE-1,
RE-3, RE-5, AUDIT-6, WR-2, OB-4, PR-4, PI-1, PI-2**, recorded during
Modules 10, 11, 14 and 15, the §14 post-implementation audit, the Step 4 roadmap
audit of 2026-09-05, the WR-1 implementation audit of the same day, the RE-5
customer-facing wording audit of 2026-10-08, and the RE-9 provider-outcome audit
of the same day. The RE-5 audit ruled RE-5's design (not implemented) and
registered RE-9 and OB-4; the RE-9 audit ruled RE-9's design and registered
PR-4, PI-1 and PI-2. **RE-8**, registered with the
`RuntimeResponse.escalate` semantics ruling of 2026-10-08, **closed on
2026-10-08**. **WR-3**, registered with the workflow-scope (ROOT-C) ruling of
2026-10-08, **closed on 2026-10-08**. **RE-9**, registered by the RE-5 audit of
2026-10-08, **closed on 2026-10-09**; its two open questions, **RE-9-Q1** and
**RE-9-Q2**, remain unresolved. **PI-2**'s design was ruled on 2026-10-09
(raised-only provider failures; not implemented); that ruling makes RE-9-Q2
moot only for conforming adapters and narrows PR-4, both of which stay open.
**WR-1 and GE-1 are not new defects** — both were disclosed in source and in
README from their own module milestones, and both are pinned by tests; what they
lacked until 2026-09-05 was a register identifier, an owner and a closure
criterion. **OB-1 closed on 2026-09-01** when the
production path was wired to a durable SQLite audit store and proven end to end;
**OB-3 closed on 2026-09-01** when §15.9's audit-gap alert was implemented at the
Runtime Engine's containment guard; **RE-4 closed on 2026-09-01** under the
**activation-invariant ruling** recorded below. None blocks the module it was found in; each needs a
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
| **PI-1** | **The Gemini adapter cannot tell a vendor-side missing or filtered reply from a genuinely empty answer** | **Architecture Issue** |
| **PI-2** | **No rule says when a provider failure is raised and when it is returned as `ProviderResponse.error_type`** | **Architecture Issue** — design ruled, not implemented |
| **PR-1** | **§10.10 and §13.10 disagree about whether the secondary provider must be registered** | **Architecture Issue** |
| **PR-2** | **The declared Model is required at routing time but not at validation** | **Documentation / Reporting** |
| **PR-3** | **`ProviderRequest` deferred; sole ownership reserved to the Provider Registry** | **Additive Extension** |
| **PR-4** | **A returned error-marked or empty `ProviderResponse` never triggers §10.9 failover** | **Architecture Issue** |
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
| **RE-4** | **The default runtime keeps no audit trail** | **Closed** — §15 implemented; durability is an activation invariant |
| **RE-5** | **§14 composes no customer-facing fallback text** | **Architecture Issue** — design ruled, not implemented |
| **RE-6** | **A blocked answer is not recorded as an agent turn** | **Documentation / Reporting** |
| **RE-7** | **§14 publishes no camelCase alias; the convention is unsettled** | **Documentation / Reporting** |
| **RE-8** | **A positive escalation verdict can be lost before the final `RuntimeResponse`** | **Closed** — final escalation normalization in `handle_request` |
| **RE-9** | **An empty or error-classified `ProviderResponse` is delivered as a normal completed turn; no module classifies that provider outcome** | **Closed** — returned failures and exact-empty answers become degraded turns |
| **AUDIT-1** | **Budget and provider are never proven to describe the same model** | **Closed** — resolved globally |
| **AUDIT-2** | **Cross-project session/workflow contamination via shared stores** | **AMENDED** — resolved for the production activation path; **open outside it** (constructor escape hatch remains) |
| **AUDIT-3** | **`transition_history` grows with no-op entries** | **Runtime Improvement** |
| **AUDIT-4** | **No production composition/activation root** | **Closed** — `activation.py` |
| **AUDIT-5** | **Channel semantics after the first turn** | **Documentation / Reporting** |
| **AUDIT-6** | **A degraded turn always returns `escalate=False`** | **Architecture Issue** |
| **AUDIT-7** | **`RuntimeEngine` inspection surface beyond §14.6** | **Documentation / Reporting** |
| **OB-1** | **Durable audit persistence** | **Closed** — production path wired to SQLite |
| **OB-2** | **§15.12(d) duplicate-ID scenario cannot arise; not faked** | **Documentation / Reporting** |
| **OB-3** | **§15.9 audit-gap alert has no seam** | **Closed** — alert raised at §14's containment guard |
| **OB-4** | **The audit record omits a guardrail verdict's `reason` and `triggered_rule`** | **Architecture Issue** |
| **WR-1** | **§6.2's message-driven routing is not implemented; no conversation advances past its first workflow** | **Closed** — two transitions on Core-published vocabulary |
| **WR-2** | **Consultation completion has no runtime contract; "submit" is prose only** | **Architecture Issue** |
| **WR-3** | **Nothing enforces a project's workflow scope; a conversation can be committed to a workflow the project has not enabled** | **Closed** — activation checks plus a commit-time scope gate |
| **GE-1** | **§8.2's pre-flight content scan is not implemented; no inbound message is checked** | **Closed** — two conditions enforced from Core vocabulary |
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

**Class: Architecture Issue** · Ruling D-4(a). ✅ **CLOSED 2026-09-01** — see
*RE-4 — reconciliation* in the §15 section for the closure and its exact limits.

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
**Design ruled — not implemented** (2026-10-08). The ruling is recorded under
*"Registered with the RE-5 customer-facing wording ruling, 2026-10-08"* below;
RE-5 is not closed by it. The original entry is retained unchanged.

When a turn is blocked, or degraded by a contained failure,
`RuntimeResponse.text` is empty and the flags carry the outcome; an escalating
turn may still carry an answer (GE-1). `RuntimeResponse.__post_init__` refuses a
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

**Cross-reference:** this entry is the **precedent** for the activation-invariant
ruling of 2026-09-01 (recorded in the §15 section), which generalises the same
production-path-versus-constructor distinction to durable audit persistence.
**AUDIT-2's own status, classification and amendment are unchanged by that
ruling**, and the distinction above must still not be collapsed.

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

#### Amendment, 2026-09-01 — the audit trail moved to logical isolation

OB-1's production wiring changed **what isolates the audit trail**, and the
change is a genuine weakening of the mechanism. It is recorded here rather than
absorbed silently.

| | Before | After |
|---|---|---|
| **Audit trail** | one `InMemoryAuditLogStore` per activation → **structural** isolation: no shared object existed through which two activations could meet | one shared SQLite database (`ORBITLANCE_AUDIT_DB`) → **logical** isolation, enforced by `project_id` filtering |
| **Sessions** | per-activation `SessionManager` → structural | **unchanged — still structural** |
| **Workflow state** | per-activation `WorkflowStateManager` → structural | **unchanged — still structural** |

**What still holds for the audit trail:** `project_id` is on every `AuditEvent`
and is one of the three query filters; `AuditFilters.matches` ANDs the supplied
filters, so a `project_id` query never returns another project's rows.
`test_activations_share_one_backing_store_with_logical_isolation` proves the
four properties directly — separate logger and store objects per activation, one
shared database beneath them, no cross-project rows from a filtered query, and
`project_id` as the boundary.

**What no longer holds:** the audit records of two projects now coexist in one
file. A caller that queries **without** a `project_id` filter sees every
project's events. That is a filter discipline, not a structural guarantee, and
this entry does not claim otherwise.

**AUDIT-2's core finding is unaffected.** It concerns conversation
contamination through shared session and workflow stores, and those remain
per-activation. Nothing about the audit change makes one project's *conversation*
reachable from another.

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
one of the eight the Guardrail Engine publishes in `UNENFORCED_CORE_CONDITIONS` as
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
| 15.2 | persist them | **PASS** — durable SQLite store on the production activation path, **OB-1** closed 2026-09-01 |
| 15.2 | expose a query interface | **PASS** for the three ruled filters |
| 15.3 | pure recorder, never decides | **PASS** — structurally asserted |
| 15.3 | never logs raw credentials or disallowed PII | **PASS** — verified end to end |
| 15.4 | inputs: type, project_id, conversation_id, payload | **PASS** |
| 15.5 | persistence confirmation; queryable records | **PASS** — `log_event` returns the stored event |
| 15.6 | `logEvent` · `queryAuditLog` | **PASS** |
| 15.7 | leaf module | **PASS** — imports `runtime.models` and the standard library only |
| 15.8 | **durable**, ideally append-only store | **PASS** — durable SQLite store on the production activation path (**OB-1** closed 2026-09-01); append-only structurally. Durable per the ratified OB-1 ruling: an event survives the store object and is readable by a new store over the same path. Claims nothing about constructions off that path, and no multi-process, thread-safety, retention or access-control guarantee |
| 15.9 | store failure must not block the conversation | **PASS** |
| 15.9 | must raise its own alert/metric | **PASS** — raised at §14's containment guard, **OB-3** closed 2026-09-01 |
| 15.10 | events immutable once written | **PASS** |
| 15.11 | structured export for compliance reporting | **DEFERRED** — future extension point |
| 15.12(a) | log and retrieve | **PASS** |
| 15.12(b) | unavailability doesn't block the flow | **PASS** |
| 15.12(c) | no raw credential in a payload | **PASS** |
| 15.12(d) | duplicate event ID rejected or versioned | **STRUCTURALLY UNENFORCEABLE** — see **OB-2** |

---

### OB-1 — Audit persistence is in-memory and therefore not durable

**Class: Architecture Issue** · Ruled for this milestone. ✅ **CLOSED 2026-09-01**
— see *✅ RESOLVED 2026-09-01* below. The dated layers between are how it got
there, not the current state.

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

#### Status update, 2026-09-01 — a durable adapter exists; **OB-1 remains open**

`runtime/observability/adapters/sqlite_store.py` implements
`SqliteAuditLogStore`, a durable `AuditLogStore` over the standard library's
`sqlite3`. **No third-party dependency was added; `dependencies = []` still
holds.** It is an optional adapter subtree structurally analogous to
`runtime/provider/adapters/`: `adapters/__init__.py` imports no implementation,
nothing in `runtime/` imports the module, and there is no default.

Two claims that must not be collapsed:

> **durable adapter implemented**  ≠  **production audit persistence durable**

**`activate()` is unchanged and still constructs `InMemoryAuditLogStore`.**
Production wiring — and the storage-path configuration it would require — is a
separate decision that has not been taken. `test_the_production_path_still_uses_
the_in_memory_store` asserts both the runtime object and the absence of
`SqliteAuditLogStore` from `activation.py`.

**§15.8 is therefore still only partially met**, and OB-1 stays open: the
repository now *provides* a durable store, but the runtime does not *use* one.

**What the adapter does claim.** "Durable" is defined minimally, by ruling: an
appended event survives destruction of the store object and is readable by a
newly constructed store over the same database path. Proven by
`test_events_survive_destruction_of_the_store_object` and
`test_two_stores_on_one_path_share_the_database`.

**What it explicitly does not claim**, each recorded rather than implied:

| Out of scope | State |
|---|---|
| Multi-process durability | **Not claimed.** No locking or coordination exists; two processes appending to one file is unaddressed |
| Thread safety | **Not claimed.** RE-3 unchanged; ADR 0003's V-7 deadline **not triggered** |
| Retention | **None.** Records are kept indefinitely until something outside the framework removes the database |
| Access control | Whatever the host filesystem provides. No application-level authorization was invented |
| Corrupt-record recovery | **None.** A malformed record raises `SqliteAuditLogStoreError`; it is never silently skipped, and no repair semantics exist |

**Isolation, stated precisely.** Two stores constructed with the same path share
one database file. `project_id` remains a field on every event and a query
filter, and a `project_id` filter never returns another project's rows — but
**shared physical storage does not provide the structural isolation that
separate in-memory stores do**, and this entry does not claim it does. **AUDIT-2
is unaffected**, because nothing wires shared storage into the production path.

**Related entries:** **RE-4** stays open — the production path still keeps no
durable trail. **OB-3** stays open — a failing store is still silent, adapter or
not. **OB-2** is unaffected: the adapter carries **no `UNIQUE` constraint and no
duplicate detection**, deliberately, because a check that can never fire is
worse than an honest absence.

**Update, 2026-09-01.** Both cross-references above have since moved: the
production path was wired to this adapter (closing **OB-1**), and a failing
store is no longer silent (closing **OB-3**). **RE-4 has since closed too**
(2026-09-01), under the activation-invariant ruling recorded in this section.

**To close OB-1:** authorize production wiring, including how the database path
reaches `activate()` — the adapter takes it explicitly at construction and there
is no configuration mechanism in this repository to supply it.

---

#### ✅ **RESOLVED 2026-09-01 — the production path is wired to the durable store**

`activate()` now reads **`ORBITLANCE_AUDIT_DB`** and constructs
`AuditLogger(SqliteAuditLogStore(path))`. `InMemoryAuditLogStore` is no longer
on the production path; it remains `AuditLogger`'s default and the test store.

**§15.2's "persist them" and §15.8's "durable" are now met on the production
path**, and OB-1 closes — but only on what was actually proven:

* `test_a_request_through_activate_is_durably_recorded` runs a real request
  through `activate()`, destroys the engine, and reads the event back through a
  **newly constructed** store over the same path. That is the ruled definition
  of durable, demonstrated end to end rather than asserted;
* `test_the_production_path_uses_the_durable_store` pins the wiring;
* `test_activation_wires_the_adapter_and_no_longer_the_in_memory_store` pins it
  structurally.

**Configuration.** `activate()`'s signature is unchanged at four arguments; the
environment variable **is** the deployment-level configuration, because this
repository has no settings object, config file or CLI. **There is no default
path**: an absent or empty variable raises `AuditStoreNotConfiguredError`, so a
deployment is told its audit configuration is missing rather than having
customer-linked records written somewhere nobody chose.

**New activation-time failure mode**, deliberate and recorded:

| Cause | Raised |
|---|---|
| `ORBITLANCE_AUDIT_DB` absent or empty | `AuditStoreNotConfiguredError` (a `ValueError`, checked first, before anything is loaded) |
| Variable set, path unusable | `SqliteAuditLogStoreError`, propagating unchanged from the adapter, which already names the path and the reason |

A runtime that cannot keep a durable audit trail no longer starts. That is a
behaviour change for any caller of `activate()`, and it is intentional.

**Post-activation containment is unchanged.** `RuntimeEngine._observe` still
wraps the write in `try/except Exception: return`; a failing store cannot alter
`RuntimeResponse`, trigger escalation or degrade a turn —
`test_a_write_failure_after_activation_leaves_the_response_identical` corrupts
the database *after* activation and asserts a byte-identical response.

**Still out of scope, and still not claimed:** retention (records kept
indefinitely), access control (host filesystem only), corrupt-record recovery,
thread safety, and multi-process safety. **RE-3 preserved; V-7 not triggered** —
no lock, thread, async surface or pool was introduced.

**What this does *not* close:** **OB-3 remains open** — a store that fails after
activation is still silent, because §15.9's alert/metric has no seam. **RE-4
therefore also remains open**; only its durability half is resolved.

**Update, 2026-09-01 — OB-3 has since closed**, in a separate change that added
the alert to §14's containment guard. It did not touch this adapter, the store
Protocol, the logger, or the wiring described above. **RE-4 has since closed
too** (2026-09-01), under the activation-invariant ruling.

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

**Class: Architecture Issue** · **Closed 2026-09-01.**

**Was:** §15.9 has two halves. The first — *"must not block the conversation from
proceeding"* — was satisfied: the Runtime Engine guards the logger call, and a
store that raises changes nothing about the `RuntimeResponse`. The second was
not: *"it must raise its own alert/metric, since a silent audit-logging gap is
itself a Compliance risk."* A failing audit store was silent, which is exactly
the Compliance risk the clause names.

The entry recorded that the repository had no metrics or alerting seam, and that
inventing a monitoring abstraction to satisfy the wording was out of scope.

**Now: closed, without inventing one.** The alert is a standard-library
`logging` call, and nothing more — no Alert or Metric Protocol, no injected
callback, no new constructor parameter, no counter, no metrics backend, no third
-party dependency, no queue, no worker, no async delivery, no retry. `logging`
was already in the repository (`validation/pipeline.py`), and where its output
goes is a deployment decision, which is the posture every other external
dependency here takes. `pyproject.toml` was not touched.

**Where it lives: `RuntimeEngine._observe`, not `AuditLogger`.** The ruled
reason is structural. `AuditLogger.log_event` *raises* on store failure,
deliberately and by contract; §14's guard is the frame that holds the exception,
and §15.3 keeps the logger a pure recorder. The Audit Logger gained no alerting
responsibility, and its failure contract is unchanged.

**What the alert carries: four fields.** The audit event type that was lost, the
`project_id`, the `conversation_id`, and `type(failure).__name__`. Nothing else.
The exception's *message* is deliberately excluded because
`SqliteAuditLogStoreError` embeds the database path and a future store could
embed a connection string; nothing from `AuditEvent.payload` is forwarded, and
the event is never serialized wholesale. An alert about a disclosure failure
must not become a second disclosure channel.

**Ordering: §15.9's first half outranks its second.** A logging handler that
itself raises — a full disk, a broken formatter, a misconfigured stream — is
swallowed. Reporting the gap may never cost the turn that exposed it.

**Proven by** nine tests in `tests/runtime_engine/test_runtime_engine.py`
(`test_ob3_*`): exactly one ERROR on a failing store, none on a healthy turn,
the four permitted fields present, no credential / path / message / answer /
payload key reaching the alert, a byte-identical `RuntimeResponse` when the
store fails, and a byte-identical one when the *alert* fails too. Each was
confirmed load-bearing by mutating the engine and watching them fail.
`test_the_logger_raises_no_alert_of_its_own` was not deleted: it now pins the
**division of responsibility** — the observability package must stay silent.

---

### Ruling, 2026-09-01 — where the durability invariant lives

**Accepted architectural ruling:**

> **Durable audit persistence is a production activation invariant, not a
> universal `RuntimeEngine` constructor invariant.**

| | |
|---|---|
| **`activate(...)`** | **is** the production activation path, and owns durable audit persistence. It constructs the durable store, and **must not** silently fall back to `InMemoryAuditLogStore` |
| **`RuntimeEngine(...)` directly** | a **lower-level / test / embedded seam**. It remains public and unchanged — and is **not** the production activation path, and must not be documented as one |
| **`AuditLogger()` in-memory default** | remains **acceptable outside production activation** |

**What the frozen specification actually requires.** §15.8 names *"a durable,
ideally append-only log store"* under **External Dependencies** — a statement
about what the deployed module depends on. §15 defines no constructor, no
default and no instantiation contract anywhere; §15.6 is `logEvent` ·
`queryAuditLog` and nothing more. No frozen clause requires every possible
construction to be durable.

**The specification supports this positively, not merely by silence.** §14.12(a)
requires a unit-test scenario of *"a full successful request through every module
with **test doubles**"* — so the spec itself mandates a construction path in
which every collaborator is a double. A universal constructor-level durability
invariant would put §14's own required scenario in tension with §15.8. And
§14.2 already places the go/no-go decision *"at project-activation/deploy time —
not re-validated on every single message"*, so **activation** is the spec's own
vocabulary for the locus where invariants are established once.

**Precision worth keeping.** `activate()` is framework-introduced: §14.6's frozen
Public Interface is `handleRequest(request) -> RuntimeResponse` and names no
activation function (this is why **AUDIT-4** existed). The ruling therefore
attaches a frozen requirement to a non-frozen seam. That is permissible because
the spec is silent on *where* the store is configured, leaving it a free
implementation decision — and **AUDIT-2 already made the identical decision** for
sessions and workflow state. This ruling generalises that precedent to the audit
log; it does not open new ground.

**No code change was required to adopt it.** `activate()` already constructs
`AuditLogger(SqliteAuditLogStore(...))`, already fails fast with
`AuditStoreNotConfiguredError` rather than falling back, and the constructor is
untouched. Pinned by `test_the_production_path_uses_the_durable_store`,
`test_activation_wires_the_adapter_and_no_longer_the_in_memory_store` (which
asserts `InMemoryAuditLogStore` does not appear in the composition root),
`test_the_in_memory_store_remains_the_loggers_default`, and the three
activation-failure tests.

**What this ruling does not do:** it does not touch **AUDIT-2**, whose subject is
cross-project *conversation* contamination through shared session and workflow
stores — a different invariant, and one where the constructor hazard is real
because it can reach a third party's conversation. AUDIT-2's status,
classification and amendment stand exactly as recorded.

---

### RE-4 — reconciliation

**Closed 2026-09-01.**

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

**Update, 2026-09-01 — the durability half is resolved; RE-4 stays open.**
OB-1's production wiring means `activate()` now builds a `SqliteAuditLogStore`
over `ORBITLANCE_AUDIT_DB`, so the trail survives the process and is readable
afterwards.

**Update, 2026-09-01 — the monitoring half is resolved too; RE-4 still stays
open, on a narrower ground.** OB-3 closed: a store that fails after activation
now raises an ERROR naming the lost event type, the project, the conversation
and the failure class. **"Durable" is true; "monitored" is now true as well**,
and both of the blockers this entry previously named are closed.

**Update, 2026-09-01 — RE-4 is CLOSED** under the **activation-invariant
ruling** recorded above.

**It closes on the condition the entry set for itself.** RE-4's own text reads
*"To close it: implement §15."* §15 is implemented; the production path is
durable (**OB-1**) and no longer silent on a gap (**OB-3**). Every element of
the recorded defect is gone: there is no `NullObservabilitySink`, `ports.py` was
deleted, and `audit` is a **required** constructor parameter, so the *"default"*
the title names does not exist to keep no trail.

**A correction to the previous update, stated rather than quietly dropped.** The
paragraph this replaces kept RE-4 open on the ground that `RuntimeEngine(...)`
built directly with `AuditLogger()` still loses its trail silently. That ground
was an extension of RE-4 beyond what RE-4 records, and it misplaced the seam:
`RuntimeEngine` has **no audit default at all**, so nothing about it is silent —
a caller must pass a logger explicitly. The in-memory behaviour comes from
`AuditLogger()`'s own default, one layer down. Under the ruling above that
default is acceptable outside production activation, so the observation is not a
defect and is no longer carried as one.

**What is *not* claimed by this closure:** that every possible construction keeps
a durable trail. It does not, deliberately. The claim is narrower and exact —
**the production activation path keeps a durable, monitored, queryable audit
trail**, and that path is `activate()`.

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

## Registered during the Step 4 roadmap audit, 2026-09-05

Two frozen-specification gaps that had **no register identifier**. Neither is a
newly discovered defect: both were disclosed in their module's source docstring
and in README's module table from their own milestone, and both are pinned by
tests written to fail the day the gap closes. What each lacked was an
identifier, an owner and a stated closure criterion — which is what this section
supplies, and nothing more. **No ruling is made here.**

They share one root — the framework's Core content is prose written for a human
or a model, not conditions a program can evaluate — but they are separate
issues in separate modules with separate closure routes.

---

### WR-1 — §6.2's message-driven routing is not implemented; no conversation advances past its first workflow

**Class: Architecture Issue** · Ruling D-4 deferred the provider path; this entry
registers the consequence, which had no identifier until 2026-09-05.
✅ **CLOSED 2026-09-05** — see the resolution note after the ruling below. The
description that follows is the state as registered, retained for history.

§6.2 requires the Router to consult each workflow's Trigger/Decision Point rules
*"against the current state **and latest message**"*. `route()` accepts
`latest_message` — it is in the frozen §6.6 signature — and immediately discards
it: `del latest_message`.

**What is implemented is genuinely deterministic, and it is two rules.** R-1: a
new conversation routes to the first-turn workflow, which `discovery.md`'s own
Trigger names (*"A new conversation begins"*). R-2: otherwise stay put, which is
§6.9 verbatim (*"Ambiguous input with no clear signal → default to remaining in
the current workflow"*). With no evaluable transition rule available, **every**
input is ambiguous by that definition.

**Why no third rule exists.** Five of the six workflows define a Decision Point
and every one turns on a judgement rather than a checkable condition — *"If
sufficient information has been collected"*, *"If the customer accepts the
recommendation"*, *"If the customer confirms the information"*, *"If the customer
responds"*, *"If synchronization succeeds"*. Inventing keyword heuristics would
make `router.py` the framework's routing semantics, resting on nothing in the
specification.

**The consequence, stated plainly: this router never advances a conversation
past its first workflow**, and **§6.12(a)** — *"a clear Discovery→Recommendation
trigger routes correctly"* — is a frozen test scenario that cannot be written
against the committed Core content. It is not faked.

**§6.3 pre-authorises one of the two closure routes**, and that is why this is a
ruling and not an implementation task: *"an LLM-based classification only as a
secondary signal for genuinely ambiguous cases"*, with an explicit cost/latency
warning that *"an LLM call on every routing decision taxes every turn"*.

**Partially dependent on TE-5 / TE-1.** Two of the five judgement conditions are
tool-shaped — `crm_sync`'s *"If synchronization succeeds"* needs a tool result
`route()` is not given, and Triggers such as *"A consultation request is
submitted"* name events it cannot observe. The other three are purely
conversational and closable without any tool work.

**To close it:** a ruling between (a) machine-readable Trigger/Decision Point
rules authored in `core/workflows/` — which amends frozen content — and (b) the
provider-backed ambiguous-case classification §6.3/§6.7 permit; then at least one
real transition satisfying §6.12(a), with §6.9's conservative default preserved.

**Related:** **TE-5** — a related partial dependency, not the same issue: two of
the five conditions need a tool result. **TE-3** — a thematic relationship only,
sharing the prose-is-not-machine-readable root with no dependency between them.
**GE-1** — same root, different module, independent ruling.

Pinned by `test_no_machine_checkable_transition_rule_exists_in_core`,
`test_the_router_documents_that_it_cannot_advance_a_conversation`,
`test_no_message_content_changes_the_outcome` and
`test_an_active_workflow_is_retained`.

---

### Ruling, 2026-09-05 — WR-1's routing strategy and where its authority lives

**Accepted architectural ruling:**

> **§6.2's message-driven routing is satisfied by Core-authored deterministic
> rules consulted against the latest message — not by runtime heuristics, and
> not by a provider call.**

**Ratified, not yet implemented.** This section records the decision; the
behaviour it authorizes does not exist yet. **WR-1 stays open until the closure
criteria below are met.**

| | |
|---|---|
| **Strategy** | Core-authored deterministic/heuristic routing as the **primary** mechanism. The runtime consults machine-readable rules Core publishes and **must not become the authoritative source of routing policy** |
| **In scope** | **Two workflow transitions** — **discovery → recommendation** and **recommendation → consultation** — plus **one terminal completion action**, Consultation's *"Submit the consultation request"*, which is **not** a transition. See the amendment below |
| **Out of scope** | `crm_sync` transitions, `voice_agent` channel-driven transitions, tool-result-driven routing, project-specific rules, `collected_data` extraction, provider/LLM semantic routing |

**Why deterministic and not semantic.** §6.3 makes deterministic/heuristic
classification the primary mechanism and permits an LLM *"only as a secondary
signal for genuinely ambiguous cases"*, warning that *"an LLM call on every
routing decision taxes every turn of every conversation."* §6.11 names the
sequence directly — *"rules-based now, ML-classifier later."* **No Provider or
LLM call is authorized for the WR-1 routing decision**; provider-backed semantic
routing remains a future decision and is not part of this closure.

**Where the authority lives.** The rules belong in the relevant files under
`core/workflows/`, **each workflow owning its own machine-consultable
Trigger/Decision Point vocabulary**. The runtime may read, transcribe or use
them; it may not independently define workflow semantics. No separate runtime
routing vocabulary, and no new repository convention for expressing rules.
Routing authority does **not** move into `projects/*/config.md`: project config
stays selection and configuration, never workflow semantics.

**Conservative fallback, unchanged.** When no deterministic rule matches the
current state and latest message, the current workflow is preserved and no
transition is guessed — §6.9 exactly as it stands. **No confidence thresholds**
and no semantic classification outside the Core-authored rules.

**One-way progression, and the reason it matters.** The two authorized
transitions advance along `discovery → recommendation → consultation` and
**no automatic regression is implemented**. A wrong transition changes which
playbook the Prompt Assembler expands into the prompt, so routing must not
oscillate or look reversible without an explicit contract. No confirmation
requirement is added unless existing Core workflow content already requires one;
**no new confirmation policy is created**. Consultation is the **last workflow
this ruling routes to**; what follows its completion is the terminal action
described in the amendment below, not a further transition.

**Nothing else moves.** `WorkflowState` and `WorkflowTransitionDecision` are
unchanged, with no new fields; `collected_data` stays `{}` unless an existing
contract independently requires otherwise; transitions persist through the
existing `WorkflowStateManager` and transition-history behaviour is preserved.
Routing keeps its **post-response position** in the §14 pipeline — it is not
moved before the Provider, no second Provider call is added, and no other stage
ordering changes.

**Explicitly excluded, with their reasons:**

* **`crm_sync`** — its Decision Point is *"If synchronization succeeds"*, which
  needs a tool result `route()` is not given. Coupled to **TE-5 / TE-1**, both
  of which stay open and unamended.
* **`voice_agent`** — it triggers on the conversation's channel, which §6.6 does
  not pass to `route()`. **AUDIT-5** stays open and unamended.

**No other issue is resolved by this work.** TE-1, TE-2, TE-3, TE-5, TE-6, TE-7,
RE-1, RE-3, RE-5, AUDIT-3, AUDIT-5, AUDIT-6 and V-7 are untouched — only WR-1
may be closed by it.

**WR-1 may close only when all of these hold:** Core workflow files carry
authoritative machine-consultable rules for the **two** authorized transitions;
`WorkflowRouter.route()` evaluates the latest message against them; **both**
transitions are demonstrated end to end; ambiguous or non-matching input
preserves the current workflow; no automatic regression exists; **every
`WorkflowTransitionDecision` names a workflow that exists in `CoreBundle`, and
no decision ever targets `submit`**; no Provider dependency exists in the
routing implementation; workflow state stays compatible with the existing model
and gains no new field; §6.9 and §6.10 remain intact; §6.12(c) purity and
§6.12(d) playbook isolation remain intact; `crm_sync` and `voice_agent` remain
explicitly out of scope; the full regression suite passes; and no unrelated
Architecture Issue is closed or amended.

**On the tests that pin the gap:** `test_no_machine_checkable_transition_rule_
exists_in_core` and `test_the_router_documents_that_it_cannot_advance_a_
conversation` were written to fail the day rules were authored. They may be
retired or inverted **only** so far as the authorized implementation requires.
No unrelated test may be weakened.

---

#### Amendment, 2026-09-05 — `submit` is not a workflow, and the third transition is withdrawn

**Cause: a §6.10 target verification performed before implementation
authorization.** The ruling above, as first ratified, named a third transition
**consultation → submit**. That target does not exist.

**Evidence.** `core/workflows/` holds six files and `CoreBundle.workflows` six
keys — `consultation`, `crm_sync`, `discovery`, `follow_up`, `recommendation`,
`voice_agent`. `framework_spec.py`'s `CANONICAL_WORKFLOWS` lists the same six,
sourced from `core/templates/config.md`'s *"The six available workflows are…"*.
Asking the committed router to target `submit` raises `UndefinedWorkflowError`:
*"Cannot route to workflow 'submit': it is not defined in Core."* A
`consultation → submit` decision would therefore violate **§6.10 on every
attempt** — the clause the same ruling requires to stay intact.

**What "Submit" actually is.** Every occurrence of the word in `core/workflows/`
is an action or an event, never a destination: `consultation.md`'s Decision
Point *"➡ Submit the consultation request"*, beside *"Update the information and
confirm again"* and *"end the workflow professionally"* — neither of which is a
workflow either; and the Triggers of `crm_sync` (*"A consultation request is
submitted"*) and `follow_up` (*"A consultation request has been submitted."*).
`consultation.md`'s Outputs confirm the shape: *"Complete consultation request ·
Qualified lead · Ready for CRM or business follow-up."* **Submitting is how
Consultation completes.**

**Amended scope.** The immediate WR-1 implementation scope is exactly:

1. **discovery → recommendation** — a workflow transition;
2. **recommendation → consultation** — a workflow transition;
3. **Consultation's completion action, *"Submit the consultation request"*** —
   **a terminal action, not a workflow target**, and outside
   `WorkflowTransitionDecision` semantics for WR-1.

**For item 3, none of the following is authorized:** creating a `submit`
workflow; adding `submit` to `CoreBundle.workflows`; creating a new
`WorkflowTransitionDecision` target; routing Consultation to `crm_sync`;
routing Consultation to `follow_up`; implementing `crm_sync` or `follow_up`
routing; or inventing a terminal workflow or completion state. Re-targeting the
transition at `crm_sync` or `follow_up` was considered and **rejected**: both
are valid §6.10 targets, but both are driven by the submission *event* rather
than by a customer message, and both collide with **TE-5 / TE-1**, which this
ruling excludes and does not amend.

**This amendment introduces no new contract.** `WorkflowState` and
`WorkflowTransitionDecision` are not redefined, no completion-state contract is
created, and no new field is added. **What can be proven about Consultation
completion using only the existing contracts is an open question for the
implementation audit to answer** — and if the honest answer is "nothing beyond
what already exists", item 3 is recorded as such rather than built.

**Unaffected.** Everything else in the ruling above stands: the Core-authored
deterministic strategy, the prohibition on a Provider call, the authority
location, §6.9's conservative fallback, one-way progression with no automatic
regression, the untouched state models, the post-response §14 position, and the
`crm_sync` / `voice_agent` exclusions.

**Test requirements, amended accordingly.** Coverage must prove: both authorized
transitions occur from Core-authored message rules; non-matching or ambiguous
messages preserve the current workflow; no automatic regression occurs;
`route()` actually consults the latest message; the runtime holds no independent
authoritative routing vocabulary; no Provider call occurs for routing; **no
decision ever names `submit` or any workflow absent from `CoreBundle`**; §6.10,
§6.12(c) and §6.12(d) remain intact; `crm_sync` and `voice_agent` stay out of
scope; and an end-to-end run through `activate()` demonstrates a real multi-turn
transition.

**WR-1 remains OPEN.** No implementation is authorized by this amendment.

---

#### Amendment, 2026-09-05 (second) — AMB-1 and AMB-2 ruled; final WR-1 scope

**Cause: the WR-1 implementation audit**, which found two contract ambiguities
the ruling above did not anticipate. Both are now ruled.

**AMB-1 — Discovery → Recommendation: AUTHORIZED, narrowly.**

The existing Decision Point, *"If sufficient information has been collected"*, is
**state-oriented**, and the `WorkflowState` contract provides no collected-data
semantics able to evaluate it — `collected_data` is permanently `()` because the
Router returns `{}` on every decision (D-3), which this ruling does not reopen.

Core is therefore authorized to publish an **explicit, message-shaped readiness
vocabulary** in `core/workflows/discovery.md`, as an *additional* Core-authored
routing signal for the existing Decision Point. **This must be documented for
what it is**: the deterministic routing representation available under the
current runtime contract — **not** a machine-readable evaluation of accumulated
`collected_data`, and it must not be presented as one. The existing prose
Decision Point remains authoritative as the conceptual workflow rule.

Constraints, all of them: authority stays in `core/workflows/discovery.md`; the
runtime reads and evaluates but **never defines its own readiness phrases or
routing policy**; authority does not move into `runtime/` or
`projects/*/config.md`; **no `collected_data` extraction**; **no change to
`WorkflowState` or `WorkflowTransitionDecision`**; **no Provider/LLM semantic
classification**; **no confidence threshold**; case-insensitive deterministic
matching is permitted, following the **GE-1 Core-vocabulary precedent**; and a
non-matching or ambiguous message preserves the current workflow (§6.9).

**AMB-2 — Consultation completion: DO NOT IMPLEMENT UNDER WR-1.**

The audit established that the repository has **no runtime contract** for
Consultation completion. It is registered separately as **WR-2** below and is
**out of scope for WR-1**. None of the following is authorized here: a `submit`
workflow, a terminal state, a `WorkflowState` or `WorkflowTransitionDecision`
change, a completion event, a `ToolRequest` producer, a `consultation_form`
change, or `crm_sync`/`follow_up` routing.

**Final WR-1 scope:**

1. **discovery → recommendation**, using the newly authorized Core-owned
   message-shaped readiness vocabulary;
2. **recommendation → consultation**, using Core-owned deterministic acceptance
   vocabulary;
3. **Consultation completion — not implemented**, explicitly deferred to
   **WR-2**. **WR-1 must not claim Consultation completion is implemented.**

**Final WR-1 closure criteria.** WR-1 may close once: both transitions work end
to end; both use Core-authored deterministic vocabulary; `latest_message` is
actually evaluated; non-matching or ambiguous messages preserve the current
workflow; no automatic regression is introduced; no Provider/LLM dependency
exists; §6.9, §6.10, §6.12(c) and §6.12(d) remain intact; §14's post-response
routing position is unchanged; **no new `WorkflowState` or
`WorkflowTransitionDecision` fields** are introduced; **no `submit` workflow
exists or is required**; Consultation completion is explicitly recorded as out
of scope and separately tracked as **WR-2**; the full regression suite passes;
and no unrelated Architecture Issue is closed or amended.

**WR-1 remains OPEN.** No implementation is authorized by this amendment.

---

#### ✅ **RESOLVED 2026-09-05 — WR-1 implemented as ruled**

`discovery.md` and `recommendation.md` each carry a **`## Routing Phrases`**
section declaring itself the authoritative source, with one `###` subsection per
target workflow holding a bullet phrase list. `WorkflowRouter.route()` reads the
**active** workflow's section and matches the latest message
case-insensitively; `del latest_message` is gone.

**The vocabulary is derived, not transcribed.** The router reads Core per call,
so editing a document changes routing with no Python to keep in step —
`test_wr1_the_router_follows_core_when_core_changes` proves it by substituting a
document with a different phrase, and
`test_wr1_no_routing_phrase_is_authoritative_in_python` proves no phrase is
written in `router.py`. Module 6 gained **no new import**: `core_bundle` was
already a `route()` parameter and the Core Loader already provides
section-addressable access, so §6.7's dependency set is unchanged.

**No ordering policy in Python (H-2 as ruled).** The runtime holds exactly one
routing constant, `_ROUTING_SECTION` — an *address*. A subsection's heading names
its own target, so the permitted progression is entirely Core-declared.
`test_wr1_the_router_holds_no_workflow_ordering_policy` asserts, over executable
string values only, that `router.py` names no workflow but `discovery` (R-1's
first-turn choice), and `test_wr1_no_published_target_is_regressive` asserts that
no Core document publishes a backward target. `recommendation.md` deliberately
publishes no `### discovery` subsection; its *"If new business needs emerge"*
branch stays prose.

**What `discovery.md`'s vocabulary is, per AMB-1.** The section states in its own
words that the Decision Point *"If sufficient information has been collected"*
remains the authoritative conceptual rule, that the runtime cannot evaluate it
because nothing extracts collected data, and that the phrases are a
**message-shaped readiness signal — not a machine-readable evaluation of
accumulated `collected_data`, and not to be presented as one**. `collected_data`
remains `{}` on every decision, including a transition (D-3 untouched).

**H-1, recorded honestly — and it is worse than the ruling anticipated.**

* **Router → Module 7 is proven for both transitions.**
  `test_wr1_the_seam_carries_a_real_transition_through_module_seven` walks a
  conversation `discovery → recommendation → consultation` through the real
  `WorkflowStateManager`, with `transition_history` recording both.
* **No activatable fixture can execute *either* transition end to end.**
  `fixture_clinic` is the only project that passes validation, and it enables
  `discovery` and `consultation` only. Discovery's published target is
  `recommendation`, which the fixture does not enable, so an advanced
  conversation degrades at the Prompt Assembler's project-scope check on the
  next turn — verified, and pinned by
  `test_wr1_no_activatable_fixture_can_execute_a_transition_end_to_end`, which
  fails the day a fixture enables Recommendation. `sunrise_dental_clinic` enables
  all six but fails validation; `orbitlance` fails with eleven issues.
* **This is fixture coverage, not an implementation failure**, and per the H-1
  ruling no project configuration or fixture was altered to manufacture a path.
* **What `activate()` does prove:** the router runs on every turn and receives
  the real message; §6.9's conservative default holds through the whole
  pipeline; and another workflow's vocabulary does not move this one.

**Unchanged and still open:** **WR-2** (Consultation completion has no runtime
contract), **TE-1 / TE-5**, **AUDIT-5**, **AUDIT-3**, **RE-5**, **AUDIT-6**, and
every other issue. `crm_sync` and `voice_agent` publish no routing section and
remain out of scope. No `submit` workflow exists, and
`test_wr1_no_decision_ever_targets_submit` asserts no decision ever names one.

Proven by seventeen tests across `tests/workflow_router/` and
`tests/runtime_engine/`. Four existing tests were **transformed, not deleted** —
the two written to fail the day rules were authored, the message-content case
(which kept every message whose premise still holds and now pins that a
workflow routes only on what *it* publishes), and the extraction-rules scan
(narrowed to pattern/scoring/threshold machinery, with the stronger
no-vocabulary-in-Python guarantee asserted separately).

---

### WR-2 — Consultation completion has no runtime contract; "submit the consultation request" is prose only

**Class: Architecture Issue** · Registered 2026-09-05, carved out of WR-1 by the
AMB-2 ruling. **Explicitly out of scope for WR-1**, which must not claim to
implement it.

`core/workflows/consultation.md`'s Decision Points read:

> *"If the customer confirms the information: ➡ **Submit the consultation
> request.**"*

alongside *"Update the information and confirm again"* and *"end the workflow
professionally"* — none of which is a workflow. Its Outputs describe the same
completion: *"Complete consultation request · Qualified lead · Structured
customer information · Ready for CRM or business follow-up."*

**Submitting is how the Consultation workflow completes. Nothing in the runtime
represents that completion.** Established by the WR-1 implementation audit:

| Contract | State at HEAD |
|---|---|
| **`WorkflowState`** | Four fields — `conversation_id`, `active_workflow`, `collected_data`, `transition_history`. **No terminal, completed or status field.** `SessionStatus` (active/idle/expired) is §12 session lifecycle, not §7 workflow completion, and is not reusable |
| **`WorkflowTransitionDecision`** | Two fields; `target_workflow: str` is **required and non-optional**, and §6.10 requires it to name a workflow that exists in `CoreBundle`. There is no null, terminal or "no transition" value, so a completion cannot be expressed as a decision |
| **`core/tools/consultation_form.md`** | Declares *"Submit consultation requests"* and *"Return submission status"* — the one contract that would represent submission. It has **no implementation**: `ToolExecutor().registered_contracts()` is empty |
| **`ToolRequest` producer** | **None.** Nothing in `runtime/` constructs one — this is **TE-1**, and `ToolStage` is *"a typed no-op until a producer exists"* |

**There is no `submit` workflow, and none may be invented.** `core/workflows/`
holds exactly six files and `CoreBundle.workflows` six keys — `consultation`,
`crm_sync`, `discovery`, `follow_up`, `recommendation`, `voice_agent` —
matching `framework_spec.py`'s `CANONICAL_WORKFLOWS`. Targeting `submit` raises
`UndefinedWorkflowError`, so a `consultation → submit` decision would violate
§6.10 on every attempt. That is why WR-1's third transition was withdrawn.

**Why this is not simply TE-1.** TE-1 records that `ToolRequest` has no writer.
WR-2 is the prior question: *what does it mean, in this runtime, for a workflow
to finish?* Even with a `ToolRequest` producer, nothing would mark the
Consultation workflow complete — `active_workflow` would still name
`consultation` forever. The two are **coupled and distinct**, and neither closes
the other.

**Related:** **TE-1 / TE-5** — a tool producer and a result path are necessary
but not sufficient. **WR-1** — carved out of it; WR-1 closes without this.
**AUDIT-3** — `transition_history` no-op growth is a symptom of the same absent
notion of a workflow ending. **`crm_sync` / `follow_up`** — both trigger on *"a
consultation request is/has been submitted"*, so both are downstream consumers
of the event this issue records as unrepresented.

**To close it:** a ruling on how a completed workflow is represented — a
terminal value or status on `WorkflowState`, a decision shape that can express
"no further workflow", or an explicit statement that completion is the channel
adapter's concern and the runtime models none — followed by whichever of those
the ruling selects, and a demonstration that a Consultation conversation reaching
confirmation is distinguishable at runtime from one still in progress.

---

### GE-1 — §8.2's pre-flight content scan is not implemented; no inbound message is checked

**Severity: High** · **Class: Architecture Issue** · **Owner: Module 8 /
Guardrail Engine.** Registered 2026-09-05; the behaviour was disclosed in source
and in README from the Module 8 milestone but carried no identifier.
✅ **CLOSED 2026-09-05** — see the closure note after the ruling below. The
description that follows is the state as registered, retained for history.

§8.2 requires a *"cheap heuristic scan of the incoming message for conditions
requiring immediate block/escalation, before any LLM call is made."*
`check_pre_flight` discards both of its §8.4 inputs: `del message,
resolved_context`. It verifies that the Core guardrails bundle is intact and
fails closed on internal error, and that is all.

**The post-response half of §8.2 is real and is not affected by this entry.**
`core.safety.unsupported_price` blocks a price absent from the project's
resolved Knowledge — the clause's own verbatim example, tested by §8.12(b).

**Why no content rule exists.** All ten of `escalation.md`'s Automatic
Escalation Conditions are semantic, and are published as
`UNENFORCED_CORE_CONDITIONS` precisely so coverage is never inferred from the
fact that the Engine returned a result. A keyword list *"would become this
framework's safety semantics on no authority, and would fail in both directions:
missing real escalations while blocking innocent messages."* Every project
Operating Constraint is likewise semantic; §8.11 records structured constraints
as the intended remedy and that mechanism does not exist.

**§8.2 does not require all ten.** It says *"conditions requiring immediate
block/escalation"*, qualified as a *cheap heuristic* — so a narrower, justified
selection satisfies the clause. *"The customer explicitly requests a human
representative"* and *"requests a manager or supervisor"* are materially more
tractable than *"Security concerns are detected"*. This is closable
incrementally.

**§8.12(a)** — *"pre-flight blocks an automatic-escalation-condition message
without any Provider call being made"* — is a frozen test scenario that cannot
currently be written, and is deliberately not faked. §8.12(c) is unmet for the
same reason.

**Relationship to AUDIT-6.** AUDIT-6 concerns *"Technical issues exceed the AI's
capabilities"* — item ten of the same tuple — and already names Module 8 as its
owner. It is a **single-condition instance** of this entry and is kept separate:
it asks a narrower question that can be answered independently.

**To close it:** a ruling naming which Automatic Escalation Conditions receive
deterministic evaluators and on what authority, and what false-positive rate is
acceptable when the outcome is blocking a customer; then at least one real
pre-flight block satisfying §8.12(a) with the Provider proven un-invoked,
`UNENFORCED_CORE_CONDITIONS` shrunk to the genuine remainder, and §8.9's
fail-closed and §8.10's reason/attribution behaviour preserved. Project
Operating Constraints (§8.12(c), §8.11) remain separate future work.

**Related:** **AUDIT-6** — a narrower single-condition issue covering item ten;
do not merge. **RE-5** — detection versus the wording a blocked customer reads,
which §8.3 makes explicitly not this module's job: separate and sequenced, since
more blocking makes RE-5's absent wording more visible. **WR-1** — same root,
different module, independent ruling.

Pinned by `UNENFORCED_CORE_CONDITIONS` and the §8.12(a)/(c)
non-implementability tests in `tests/guardrail/test_guardrail_engine.py`.

---

### Ruling, 2026-09-05 — GE-1's pre-flight scope and where its authority lives

**Accepted architectural ruling:**

> **§8.2's pre-flight scan is satisfied by a narrow deterministic subset whose
> trigger vocabulary is Core content, not by broad heuristics invented in
> `runtime/`.**

**Ratified, not yet implemented.** This section records the decision; the
behaviour it authorizes does not exist yet. **GE-1 stays open until the closure
criteria below are met**, and `UNENFORCED_CORE_CONDITIONS` remains at **ten**
entries until implementation is separately authorized.

| | |
|---|---|
| **Strategy** | Narrow deterministic subset. A cheap deterministic evaluation runs at pre-flight, before any Provider call — satisfying §8.2 and making §8.12(a) writable — **without** attempting all ten Automatic Escalation Conditions |
| **In scope** | **Exactly two** conditions: *"The customer explicitly requests a human representative"* and *"The customer requests a manager or supervisor."* The set is not to be silently expanded |
| **Out of scope** | Conditions 3–10 remain **explicitly unenforced** for pre-flight purposes |

**Where the authority lives — the substance of this ruling.** The trigger
vocabulary for the two conditions is **Core content**, authored in
`core/guardrails/escalation.md`. `runtime/guardrail/engine.py` may transcribe
that committed definition under the repository's existing transcription
discipline — the same discipline `PRICE_PATTERN` follows — but **must never
become the authoritative source of the safety policy**. Any new trigger
vocabulary is therefore a frozen Core-content change, and Core/Project
separation is preserved: safety semantics stay in `core/`, never in Python.

**No Provider at pre-flight.** Provider-backed semantic classification is
**refused** at this checkpoint and Module 8 remains provider-independent. §6.3's
secondary-classification permission is **Module 6-specific and does not
transfer**. §8.8's post-response sampled/async guardrail judge remains the
authorized location for any future semantic or provider-backed evaluation. **No
Provider call may occur as part of GE-1 pre-flight.**

**Escalate, do not block.** A match on either condition produces
**`escalate=True`, `blocked=False`**. The customer is requesting human
assistance; that is a handoff request, not a reason to refuse service. The
false-positive posture is deliberately conservative in this direction: a wrong
match costs an unnecessary escalation signal, never a refused customer. **These
conditions must not be converted into automatic blocking.**

**One companion §14 change is authorized, and only one.** The chosen semantics
are not currently representable: `PreFlightGuardrailStage` reads
`result.escalate` only when `result.blocked` is true, and the delivery stage
reads only `state.post_response.escalate` — so a pre-flight escalation on a
passing turn is silently dropped. **`pre_flight.escalate` must survive to the
final `RuntimeResponse`.** No other §14 behaviour is to be added.

**What this ruling does not decide:**

* **AUDIT-6 remains open.** Condition 10, *"Technical issues exceed the AI's
  capabilities"*, is a post-failure runtime condition, not a property of an
  inbound message, and is outside the evaluator set. It needs its own §14
  degradation/escalation ruling.
* **Project Operating Constraints remain out of scope.** No `project.*`
  evaluators, `UNENFORCED_PROJECT_CONSTRAINTS` unchanged, and **no claim on
  §8.11 or §8.12(c)**. A separate issue for that gap is not registered by this
  ruling.
* **RE-5 remains open.** Composing what a customer reads is §8.3's excluded
  responsibility and Module 14's concern. The order relationship stands: more
  active escalation makes RE-5's absent wording more visible.

**Boundaries preserved:** Core/Project separation · Module 8 provider
independence · §8.2's cheap pre-flight semantics · §8.9 fail-closed · §8.10
reason and `core.*` attribution · §8.3's responsibility boundary · §6.3 as a
Module 6 permission · §8.8 as the authorized venue for future post-response
semantic judging.

**GE-1 may close only when all of these hold:** authoritative Core vocabulary
exists for the two conditions; pre-flight evaluates them before any Provider
call; a real matching message yields `escalate=True` with `blocked=False`; that
flag survives to `RuntimeResponse`; no Provider call precedes the decision;
reason and `core.*` attribution are preserved; `UNENFORCED_CORE_CONDITIONS`
contains exactly the remaining **eight**; §8.9's fail-closed behaviour is
intact; project constraints remain explicitly unenforced; AUDIT-6 and RE-5
remain open; and the full regression suite passes.

---

#### ✅ **RESOLVED 2026-09-05 — GE-1 implemented exactly as ruled**

`escalation.md` now carries an **"Escalation Trigger Phrases"** section stating
that it is the authoritative source, with one subsection per condition, worded
identically to the condition it serves. `check_pre_flight` looks the phrases up
through `ESCALATION_VOCABULARY_SECTIONS` and matches them case-insensitively.

**The vocabulary is derived, not transcribed** — a stronger reading of the
ruling than transcription, and the one that makes Core authoritative in fact
rather than by convention. The Engine reads the section per call, so editing
`escalation.md` changes behaviour with no Python to keep in step.
`test_ge1_the_engine_follows_core_when_core_changes` proves it by substituting a
document with a different phrase and observing the Engine follow it;
`test_ge1_the_vocabulary_is_core_content_not_python` proves no phrase is written
in `engine.py`. Module 8 imports nothing new — the `CoreBundle` was already
injected, and the Core Loader already provides section-addressable access, so
§8.7's dependency set is unchanged and no markdown helper was imported.

**Semantics as ruled:** `escalate=True`, `blocked=False`, a reason naming the
matched phrase and the Core condition, and `core.escalation.*` attribution
resolving to `GuardrailOrigin.CORE`. Every phrase Core publishes is exercised,
not a sample.

**§14 plumbing, the one authorized change:** `DeliveryStage` now takes the union
of both checkpoints' `escalate` flags. Nothing else about §14 changed; a
structural test pins that the stage consults the two verdicts and acquires no
other escalation policy.

**Fail-closed extension, recorded because it is a judgment call.** A missing
phrase list raises, which §8.9's guard turns into a blocked, escalating
`engine.internal_failure`. `escalation.md` could otherwise exist, be non-empty,
pass the bundle-integrity check, and leave the Engine silently enforcing
nothing — the no-op §8.9 forbids. The blast radius is deliberate and matches the
existing posture for an incomplete bundle.

**`UNENFORCED_CORE_CONDITIONS` moved 10 → 8.** The two enforced conditions left
it; the eight remaining are still asserted verbatim against `escalation.md`.
`UNENFORCED_PROJECT_CONSTRAINTS` is untouched and **no `project.*` rule exists**.

**Unchanged and still open:** **AUDIT-6** (condition ten is a post-failure
question for §14), **RE-5** (§8.3 keeps composing the customer's wording outside
this module), **WR-1**, and every other issue. §8.12(c) remains unimplementable.

Proven by fifteen tests across `tests/guardrail/` and `tests/runtime_engine/`.
Two existing tests were **transformed, not deleted**: the 10-condition count
narrowed to 8, and the "does not guess" test kept every case whose premise still
holds while the two now-enforced messages moved to positive coverage.

---

## Registered with the `RuntimeResponse.escalate` semantics ruling, 2026-10-08

**Ruling, approved:** `RuntimeResponse.escalate` is `True` if and only if at
least one Guardrail Engine checkpoint returned `GuardrailResult.escalate=True`
during the current `handle_request` turn; otherwise it is `False`. It is a
turn-level runtime fact sourced from Guardrail Engine verdicts, fail-closed
verdicts included, and the audit's `escalate` value records it. It is not a
channel instruction or handoff state. A non-guardrail source of escalation
requires amending the definition. Recorded on the field in
`runtime/models/runtime.py`.

---

### RE-8 — A positive escalation verdict can be lost before the final `RuntimeResponse`

**Class: Architecture Issue** · Registered 2026-10-08.
✅ **CLOSED 2026-10-08** — see the resolution note after the ruling below. The
description that follows is the state as registered, retained for history.

The current runtime does not yet conform to the ruling above on every
turn-ending path. A Guardrail Engine checkpoint can return `escalate=True` during
the turn, and the final `RuntimeResponse` (and so the audit outcome) can still
report `escalate=False`.

**Reachable today:**

* a prompt-assembly, provider, router, state-commit or delivery exception —
  `handle_request` replaces the outcome with `RuntimeResponse(degraded=True)`;
* a post-response block — `PostResponseGuardrailStage` builds the blocked
  response from the post-response verdict alone.

**Not reachable today, but covered by the same invariant:**

* a post-response stage exception — the Guardrail Engine contains its own
  failures and returns a blocking, escalating verdict instead of raising;
* a tool-stage exception — nothing produces a `ToolRequest` (TE-1);
* a turn that ends with no outcome — `build_pipeline` always ends with
  `DeliveryStage`, which sets one or raises; reachable only by substituting the
  pipeline in a test.

The frozen definition applies to every `handle_request` turn, so these paths are
covered without being made reachable.

Until this closes, `escalate=False` on such a turn does not prove that no
checkpoint escalated.

**Scope is propagation only.** Whether technical failures should themselves
escalate is AUDIT-6. Customer wording is RE-5. Handoff state and channel
instructions are not part of this issue.

#### Ruling, 2026-10-08 — RE-8's design and its §14 authorization

**Accepted architectural ruling. Ratified, not yet implemented. RE-8 stays open
until implementation and verification are complete.**

> **Owner: `RuntimeEngine.handle_request`.** After the final `RuntimeResponse`
> outcome is settled — including exception containment and the no-outcome
> fallback — and immediately before `_observe_outcome` and `return`: if any
> Guardrail Engine verdict recorded on the current turn's `TurnState` has
> `escalate=True`, the final `RuntimeResponse.escalate` must be `True`.

| | |
|---|---|
| **Behaviour** | Only `escalate=False → True`. Never `True → False`. No other `RuntimeResponse` field changes |
| **Source** | The Guardrail Engine verdicts already recorded on the turn's `TurnState` (`pre_flight`, `post_response`), read directly. No new `TurnState` field; no helper unless implementation proves one strictly necessary |
| **Nature** | A final outcome-normalization guarantee — not a pipeline stage, and not Guardrail Engine logic |
| **§14 authorization** | **Exactly one additional §14 behavioural change**, for RE-8 only. GE-1's "one companion §14 change" limit is superseded for this authorization alone; no general reopening of §14 |
| **Specification** | `docs/runtime-specification.md` is **not** changed. Like GE-1's change, this is authorized by register ruling |
| **`DeliveryStage`** | Its existing escalation merge is **kept unchanged**. The engine step is the final guarantee across every termination path; the duplicate calculation on the Delivery path is not a problem RE-8 solves |
| **No-outcome path** | Covered for escalation preservation only. Its test asserts the escalation invariant and creates no contract for `text`, `blocked` or `degraded` |

**RE-8 does not create escalation.** It propagates a verdict that already
exists. Whether a failure should create a new verdict is AUDIT-6, which this
ruling does not touch.

**Tests required with the implementation:**

1. a positive pre-flight verdict survives every applicable termination path;
2. a positive post-response verdict survives the relevant paths;
3. no escalating verdict means `RuntimeResponse.escalate=False` on the same paths;
4. the audit's `escalate` equals the final `RuntimeResponse.escalate`;
5. `blocked`, `degraded` and text semantics are unchanged on real, reachable paths;
6. no stage gains its own ownership of escalation propagation;
7. the synthetic no-outcome path preserves `escalate=True` and asserts nothing more.

Existing GE-1 and `DeliveryStage` tests stay unchanged. No per-stage
propagation is added.

**Out of scope:** new escalation verdicts; technical-failure escalation policy
(AUDIT-6); Guardrail Engine policy and §8; the §8.12(a) / GE-1 tension; RE-5;
who decides when a tool is called (TE-1), who owns customer-data collection,
and who enforces project workflow scope; WR-2; handoff or channel semantics; escalation
source or reason fields; `RuntimeResponse` fields; pipeline order;
`DeliveryStage`; exception-containment semantics; audit payload keys.

**Untouched frozen decisions:** the `RuntimeResponse.escalate` definition, GE-1
policy, WR-1, `RuntimeResponse`'s four-field model, §14 pipeline order, §15's
pure-recorder principle, Guardrail Engine semantics, and every earlier freeze.

#### ✅ **RESOLVED 2026-10-08 — RE-8 implemented as ruled**

`RuntimeEngine.handle_request` now performs the final escalation normalization
after the outcome is settled — exception containment and the no-outcome fallback
included — and before `_observe_outcome` and `return`. It reads the two existing
Guardrail Engine verdicts, `state.pre_flight` and `state.post_response`; if
either has `escalate=True`, the final response is normalized to `escalate=True`.
Only `False → True`: `text`, `blocked` and `degraded` are carried over unchanged,
and a failure never creates escalation.

No `TurnState` field, stage or Guardrail Engine logic was introduced, and
`DeliveryStage` is unchanged. The audit observes the normalized response, so its
`escalate` value now matches the final `RuntimeResponse` on every path.

Proven by thirteen tests in `tests/runtime_engine/`, covering the required
matrix; eleven fail against the unfixed engine. Full offline suite: **1104
passed, 16 skipped**.

**Unchanged and still open:** AUDIT-6, RE-5, the §8.12(a) / GE-1 tension, and
every other issue.

---

## Registered with the workflow-scope (ROOT-C) ruling, 2026-10-08

One gap, found during the post-RE-8 architecture triage, registered together with
its approved design.

---

### WR-3 — Nothing enforces a project's workflow scope; a conversation can be committed to a workflow the project has not enabled

**Class: Architecture Issue** · Registered 2026-10-08 (audit reference ROOT-C).
✅ **CLOSED 2026-10-08** — see the resolution note after the ruling below. The
description that follows is the state as registered, retained for history.

The frozen specification assigns project workflow scope to no module, and
`WorkflowNotEnabledError` says so. The Router cannot see what a project enabled
(§6.6 gives `route()` no `ResolvedContext`), the State Manager persists whatever
it is given (§7.3, §7.4), and `WorkflowStage` commits the Router's decision
without a scope check. The only check is the Prompt Assembler's, on the *next*
turn — after the out-of-scope state is already committed, and before routing can
run again. With no backward routing, the conversation then degrades on every
later turn.

Two reproduced consequences:

* **A routed transition to a workflow the project has not enabled.**
  `fixture_clinic` enables Discovery and Consultation; Discovery publishes a route
  to Recommendation. A matching message commits Recommendation, and every later
  turn degrades. WR-1's H-1 note records the first degraded turn; the degradation
  is in fact permanent.
* **A project without Discovery.** Validation does not require it, so the project
  activates; `FIRST_TURN_WORKFLOW = "discovery"` is committed after the first
  answer, and every conversation degrades from its second turn.

`config.workflows_known` checks only that enabled names are canonical.

**Related:** WR-1 (whose rulings are not changed by this entry), WR-2, and the
Prompt Assembler's `WorkflowNotEnabledError`, which recorded the intent that
*"the Runtime Engine is the primary gate"*.

#### Ruling, 2026-10-08 — WR-3's workflow-scope invariant and its enforcement

**Accepted architectural ruling. Ratified, not yet implemented. WR-3 stays open
until implementation and verification are complete.**

> **The Runtime Engine never commits a `WorkflowTransitionDecision` whose target
> is not in the active project's `ResolvedContext.config.enabled_workflows`; and
> no project activates unless its first-turn workflow, `discovery`, is enabled.**

**Decisions, approved:**

| | |
|---|---|
| **Scope source** | `ResolvedContext.config.enabled_workflows`, fixed for an activation, with the existing default of all six when `config.md` selects none |
| **"Enabled"** | The workflows a project lists. Discovery is the one required workflow; this does **not** make any other workflow mandatory |
| **First turn** | `FIRST_TURN_WORKFLOW = "discovery"` is unchanged. A project **must not activate** without Discovery. Selection stays channel-independent |
| **Core `Dependencies`** | Describe runtime data and input consumption. They are **not** enablement dependencies, create **no** implicit enablement, and introduce **no** dependency closure. The dependency model is unchanged |
| **Violation** | An out-of-scope transition is **refused**: no commit, no history entry, the current workflow is preserved, and the generated answer is delivered unchanged. The turn is not degraded, `RuntimeResponse` is unchanged, and scope enforcement never sets `RuntimeResponse.escalate` — escalation stays governed solely by the frozen Guardrail Engine semantics |

**Enforcement approved for implementation:**

* **At activation (Validation Layer):** an **ERROR** when Discovery is not
  enabled; a **WARNING** for each routing target a project's enabled workflows
  publish under `Routing Phrases` that the project has not enabled. Both are
  derived from Core content, never from a hard-coded workflow list. The project
  still activates with the WARNING.
* **At commit (Runtime Engine, §14):** before any workflow transition is
  committed, its target must belong to `enabled_workflows`; an invalid target is
  refused as above.

**Placement for the implementation:** inside `WorkflowStage`, after `route()` and
before `commit_transition()`. No additional module call, no new `TurnState`
field, and no change to the Router's or the State Manager's responsibility. The
Prompt Assembler's `WorkflowNotEnabledError` remains a downstream backstop.

**Authorization:** one §14 behavioural change (the commit-time check), by
register ruling as for GE-1 and RE-8; the activation checks are additive
Validation Layer rules. `docs/runtime-specification.md` is not changed.
`WorkflowTransitionDecision`, `WorkflowState`, the Resolver's output, the §14
stage order and WR-1's rulings are unchanged.

**Observability.** The activation WARNING is configuration-time observability,
not a runtime audit event; the audit payload and event shape are unchanged. It
announces every out-of-scope target that today's Core-published routing can
produce. **It is not a substitute for runtime observability of transitions that
cannot be known at activation** — provider-backed, tool-driven or other dynamic
producers would need a separate architectural decision.

**Recovery:** none is required. Workflow and session stores are constructed per
activation and config and Core are fixed within one, so no out-of-scope state
can persist once the check exists.

**Out of scope:** workflow completion (WR-2); provider-backed routing; tool-driven
routing and who decides when a tool is called (TE-1); customer-data ownership;
channel-specific first-workflow selection; audit payload changes; dependency-model
changes; customer wording (RE-5); concurrency (RE-3); escalation policy
(AUDIT-6); provider validation (PR-1); the §8.12(a) / GE-1 tension.

#### ✅ **RESOLVED 2026-10-08 — WR-3 implemented as ruled**

Implemented in commit `f620a7f`.

**At activation**, two Validation Layer rules: `CONF008` (ERROR) rejects a
project whose effective enabled set does not include the first-turn workflow,
`discovery`, so such a project cannot activate; `CONF009` (WARNING) reports each
routing target an enabled workflow publishes under `Routing Phrases` that the
project has not enabled, and the project still activates. The enabled set is
derived exactly as the Resolver derives it — nothing declared enables every
workflow; otherwise only the declared labels that name a Core workflow — and
targets are read from Core documents as the Router reads them, never from a
list in Python. Core `Dependencies` enable nothing.

**At runtime**, `WorkflowStage` checks the Router's `target_workflow` against
`ResolvedContext.config.enabled_workflows` between `route()` and
`commit_transition()`. An out-of-scope target is refused: nothing is committed,
no history entry is written, the current workflow is preserved, and the
generated answer is delivered. The turn is not degraded, and the refusal never
alters `RuntimeResponse.escalate`. No module call, `TurnState` field or stage was
added; the Router and the State Manager are unchanged, and the Prompt
Assembler's `WorkflowNotEnabledError` remains the backstop.

Because the Validation Layer may not depend on the Router or the Resolver
(§13.7), the first-turn workflow and the `Routing Phrases` section name are
transcribed in `framework_spec.py`; alignment tests keep them, the enabled-set
derivation and the routing-target reading equal to the runtime's.

Proven by twenty-nine new tests across `tests/runtime_engine/`,
`tests/validation/` and `tests/test_vocabulary_alignment.py`; twenty-six fail
against the unfixed implementation. `test_1_the_fixture_project_passes_activation`
now expects the fixture's one `CONF009` WARNING. Full offline suite: **1133
passed, 16 skipped**.

**Unchanged and still open:** WR-2, the remaining tool and customer-data
ownership questions, AUDIT-6, RE-5, PR-1, the §8.12(a) / GE-1 tension, and every
other issue.

---

## Registered with the RE-5 customer-facing wording ruling, 2026-10-08

One ruling on an existing issue, and two new gaps found by the same read-only
audit (run against commit `a2535d1`). The three are independent: neither new
issue is part of RE-5, and neither may be fixed under it.

---

### Ruling, 2026-10-08 — RE-5: who owns customer-facing wording

**Accepted architectural ruling. RE-5 is design ruled — not implemented. It is
not closed.**

**This is a documentation and ruling decision only.** No implementation is
required inside the current framework for the ownership rule itself: the runtime
already emits no customer-facing wording, and the owner of non-answer wording is
outside this specification.

1. **Answer turns.** When `RuntimeResponse.text` is non-empty, the model owns the
   customer-facing wording. The framework delivers the model's text unchanged.
2. **Non-answer turns.** When `RuntimeResponse.text == ""`, the framework does
   not generate customer-facing wording.
3. **Owner of non-answer wording.** The channel adapter — which consumes
   `RuntimeResponse` and is outside this framework specification (§14.5, §14.8)
   — owns customer-facing wording for non-answer turns.
4. **What the channel adapter may rely on.** It may use the response flags
   (`blocked`, `escalate`, `degraded`) to determine appropriate wording, but must
   not claim a success, handoff, or cause that is not represented by those flags.
5. **Providers** own model output, not customer-facing fallback wording.
6. **Guardrail Engine** owns detection, attribution and blocking/escalation
   decisions, not customer-facing wording (§8.3).
7. **Runtime Engine** owns runtime outcome classification, not customer-facing
   wording.
8. **Guardrail reasons, exception messages and internal diagnostics are never
   customer-facing text.**
9. **Nothing is introduced.** The ruling adds no fallback catalogue, no second
   provider generation pass, and no new `RuntimeResponse` fields.
10. **Out of scope.** Tool-result wording, customer-data collection wording, and
    handoff/channel behaviour after escalation are not covered and remain outside
    RE-5's scope.

**Unchanged:** `RuntimeResponse`, the Runtime Engine, the provider contract, the
Guardrail Engine, `docs/runtime-specification.md`, and every other issue's
ruling, including WR-3 and RE-8.

---

### RE-9 — An empty or error-classified `ProviderResponse` is delivered as a normal completed turn

**Class: Architecture Issue** · Registered 2026-10-08 (RE-5 audit, finding F1).
✅ **CLOSED 2026-10-09** — see the resolution note after the ruling below. The
description that follows is the state as registered, retained for history.
**Open.** A §14 / runtime outcome-semantics question. **This is not a wording
problem**, and it is independent of RE-5.

A `ProviderResponse` may currently carry empty text, an `error_type`, or both:

* the Gemini adapter normalises a blocked or empty candidate to `text=""` and
  returns it, with the comment that *"the Guardrail Engine and Runtime Engine
  decide what to do with it"* — neither currently does;
* the shared conformance suite accepts a returned `ProviderResponse` whose
  `error_type` is set.

`DeliveryStage` reads only `text`. Either response therefore produces a
normal-looking `RuntimeResponse` with empty `text`, `blocked=False`,
`escalate=False` and `degraded=False`. The turn is logged as
`runtime.turn_completed`, and an empty agent turn is appended to the
conversation. Reproduced on a scratch copy of `a2535d1` for both shapes.

**What is undefined.** The architecture does not say who classifies this
provider outcome, or whether it should become degraded, failed, blocked or
something else.

**This issue must be ruled before any behaviour change is implemented.** It
must not be fixed as part of RE-5. No solution is proposed here.

---

### OB-4 — The audit record omits a guardrail verdict's `reason` and `triggered_rule`

**Class: Architecture Issue** · Registered 2026-10-08 (RE-5 audit, finding F5).
**Open.** An observability/audit issue — **not a customer-facing wording issue**,
and separate from RE-5 and RE-9.

`GuardrailResult.reason` exists, and §8.10 requires every block to carry one
*"for observability and for constructing an honest, specific fallback"*, together
with whether a Core guardrail or a project Operating Constraint triggered it
(carried by `triggered_rule`). Both are useful for attribution and for fallback
reasoning.

The Runtime Engine's audit payload records `blocked`, `escalate`, `degraded`,
`channel` and, on a contained failure, `failed_stage` — but **neither `reason`
nor `triggered_rule`**. No other module records them. The observability purpose
§8.10 describes for guardrail reasons is therefore not fully represented in the
audit data.

One fact any future decision must account for: an `engine.internal_failure`
reason embeds the caught exception's text.

**Not changed now:** audit structures, the audit payload and the Guardrail
Engine. No fix is implemented and none is proposed here.

---

## Registered with the RE-9 provider-outcome ruling, 2026-10-08

One ruling on an existing issue, and three new gaps found by the same read-only
audit (run against commit `abbd7b9`). The three new issues are independent of
RE-9's outcome classification and of one another; none may be fixed under RE-9.

**Identifiers.** Issues are prefixed by the module they concern. `PR-4` continues
the Provider Registry (Module 10) series. Module 9 — the Provider Interface and
its concrete adapters — had no register entry before, so `PI-1` and `PI-2` open a
Provider Interface series. (The provider code's own labels, such as P-1, C-1a and
E-1, are design notes in source, not register identifiers.)

---

### Ruling, 2026-10-08 — RE-9: when a provider outcome is a completed turn

**Accepted architectural ruling. RE-9 is design ruled — not implemented. It is
not closed.**

> **A turn completes normally only when the provider stage yields a usable
> answer.**

1. A `ProviderResponse` with `error_type` set is a **provider failure**,
   equivalent to a raised `ProviderError`, regardless of its `text`.
2. A `ProviderResponse` with `error_type` unset and `text == ""` is **no usable
   answer**. "Empty" means exactly `text == ""`. Whitespace-only text is
   intentionally not ruled here.
3. In both cases the **Runtime Engine** classifies the turn as **degraded** under
   §14.9 and §14.12(c): `RuntimeResponse.text == ""` and `degraded=True`.
   Provider text from a failed response is not delivered.
4. `blocked` and `escalate` retain their frozen meanings. RE-9 never sets
   `blocked` and never sets `escalate`. Any guardrail verdict that is actually
   reached remains governed by the existing guardrail semantics and RE-8. Whether
   technical failures should escalate remains AUDIT-6.
5. Such a turn uses the existing degraded runtime outcome and event semantics. No
   new event type, payload field, or `RuntimeResponse` field is introduced.
6. No agent turn is recorded for such a turn, consistent with the existing
   no-answer and degraded paths.
7. Customer-facing wording remains governed by RE-5. The channel adapter owns
   wording for the non-answer turn, using the existing outcome flags. Provider
   error text, exception messages, and internal diagnostics never become
   customer-facing wording.
8. The ruling does not alter the provider contract, the Provider Registry's
   failover policy, Guardrail Engine ownership, `RuntimeResponse`, `TurnState`,
   §14.2's stage ordering, or any existing architecture boundary.

**Unresolved under RE-9 — deliberately not decided by this ruling:**

* **RE-9-Q1 — whitespace-only text.** Whether a `ProviderResponse` whose `text`
  is non-empty but whitespace-only counts as empty. Under clause 2 it does not
  meet the definition of empty; whether it should is an open question.
* **RE-9-Q2 — the post-response checkpoint on a failed response.** Whether the
  post-response guardrail checkpoint must run on a response already classified
  as a provider failure. A raised `ProviderError` never reaches that checkpoint;
  §8.3 forbids skipping it *"to save latency or cost"*. Clause 4 covers only a
  verdict that is actually reached.

Neither question may be settled implicitly by an implementation of RE-9.

#### Audit of RE-9-Q1 and RE-9-Q2, 2026-10-08 — both remain unresolved

A read-only audit against commit `58f6417` found that the architecture does not
answer either question. **Both remain unresolved RE-9 questions; no new issue is
registered for either.** The eight-clause ruling above is unchanged, and RE-9
remains **design ruled — not implemented**. Neither question blocks implementing
RE-9, provided the constraints below hold.

**RE-9-Q1 — unresolved.** The frozen specification defines no content rule for
`ProviderResponse.text`, and no rule defines a "deliverable" or "usable" answer
beyond non-emptiness. Elsewhere the runtime treats whitespace both ways —
document and configuration models treat whitespace-only content as empty, while
`RuntimeResponse`'s blocked-text invariant and RE-5 clause 1 treat any non-empty
string as text — and no rule ties either convention to provider output.

> **Implementation constraint (Q1).** An RE-9 implementation must treat empty
> provider text exactly as `text == ""`. It must not use `.strip()`, truthiness,
> or any newly invented "blank" or "meaningful text" rule. This preserves Q1 as
> an unresolved architecture decision.

**RE-9-Q2 — unresolved.** §8.3 forbids skipping the post-response check *"to save
latency or cost"*, and §14 makes the stage non-removable from composition, but no
clause says whether the checkpoint must run on every `ProviderResponse` or only on
one that could be delivered. Today a raised `ProviderError` never reaches the
checkpoint, while a returned failed `ProviderResponse` does. Whether that
distinction is intended is part of **PI-2**, which could make Q2 moot (if
failures must always be raised) but does not answer it. **PR-4** changes which
response reaches the checkpoint, not whether it must run.

> **Implementation constraint (Q2).** An RE-9 implementation must not introduce a
> new early exit between `ProviderStage` and `PostResponseGuardrailStage` that
> would implicitly decide Q2. The existing checkpoint path must remain intact
> unless a future architecture ruling explicitly decides otherwise.
>
> **Semantic constraint (Q2).** If a guardrail verdict is actually reached on a
> failed provider response, RE-9 must preserve the existing guardrail semantics
> (clause 4, RE-8) while still applying the RE-9 degraded classification
> (clause 3). The implementation must not silently convert Q2 into a new
> stage-ordering decision.

#### ✅ **RESOLVED 2026-10-09 — RE-9 implemented as ruled**

Implemented in commit `a348675`, in `runtime/runtime_engine/stages.py`.

A private predicate classifies a provider response as having no usable answer
exactly when `error_type is not None` or `text == ""`. It uses neither stripping
nor truthiness.

* **`DeliveryStage`:** such a response becomes a degraded turn. `text` is `""`,
  no agent turn is recorded, `blocked` is not set, and `escalate` retains the
  existing union of guardrail verdicts. The event is the existing
  `runtime.turn_degraded`, with no `failed_stage`.
* **`PostResponseGuardrailStage`:** if the existing checkpoint blocks such a
  response, the block and the guardrail's own `escalate` value are preserved,
  and the turn is also degraded. The event remains `runtime.turn_blocked`.
* **Unchanged:** ordinary answers; the provider contract and `ProviderResponse`;
  Provider Registry failover; `RuntimeResponse` shape; `TurnState`; `engine.py`,
  including the RE-8 repair and outcome observer; event names and payload keys;
  and §14.2 stage order. No early exit was added before the post-response
  checkpoint.

**Still unresolved:**

* **RE-9-Q1:** whitespace-only text semantics.
* **RE-9-Q2:** post-response checkpoint policy for failed provider responses.

The implementation follows both recorded constraints and settles neither
question. Closing RE-9 does not close RE-9-Q1, RE-9-Q2, RE-5, PR-4, PI-1, PI-2,
OB-4, AUDIT-6, RE-6, or any other issue.

**Verification:** seven new tests were added; the four behavioural tests fail
against the unfixed implementation, and the three checkpoint cases pin existing
behaviour. The full offline suite passed with **1140 passed, 16 skipped**;
`ruff check` passed.

**Related, not blocking:** AUDIT-6 (escalation of technical failures), RE-6 (the
agent-history reasoning clause 6 follows), RE-5 (wording, unchanged), PR-4, PI-1
and PI-2 (below). `docs/runtime-specification.md` is not changed; an
implementation would be one §14 behavioural change authorized by register
ruling, as for GE-1, RE-8 and WR-3.

---

### PR-4 — A returned error-marked or empty `ProviderResponse` never triggers §10.9 failover

**Class: Architecture Issue** · Registered 2026-10-08 (RE-9 audit). **Open.**
A Provider Registry / failover issue — **not** an RE-9 outcome-classification
issue.

§10.9: *"Primary fails → attempt configured secondary → if none configured or it
also fails, surface a clear 'technical difficulties' outcome to Runtime Engine."*

`ProviderRegistry.generate_with_fallback` fails over only when the primary
**raises** a `ProviderError` whose class is in `FAILOVER_ERROR_TYPES` (rate
limit, timeout, service unavailable). A primary that **returns** a
`ProviderResponse` — whether its `error_type` is set or its `text` is empty — is
passed through unexamined, and the secondary is never attempted.

The architecture does not say whether a returned failure, or a returned empty
answer, is a "primary failure" for §10.9's purposes. RE-9's classification is
unaffected either way: the Runtime Engine sees only the response the Registry
finally returns. No fix is implemented and none is proposed here.

**Narrowed by the PI-2 ruling, 2026-10-09 — still open.** A conforming adapter
reports every operational failure by raising, so for conforming adapters PR-4
reduces to the returned **empty** answer (`error_type` unset, `text == ""`). How
the Registry should treat a returned `error_type` from a non-conforming adapter
is not decided, and no failover policy is decided for either case.

---

### PI-1 — The Gemini adapter cannot tell a vendor-side missing or filtered reply from a genuinely empty answer

**Class: Architecture Issue** · Registered 2026-10-08 (RE-9 audit). **Open.**
A Provider Interface (Module 9) adapter-normalization question under §9.9 and the
conformance suite — **not** to be solved as part of RE-9.

`GeminiAdapter._normalise_response` maps `response.text is None` to `text=""`
and returns it as a success. It does not inspect why the reply is missing — for
example, no candidate, or a candidate withheld by the vendor's own filtering — so
a vendor-side missing or filtered response is indistinguishable from a genuinely
empty model answer. Pinned by
`test_an_empty_candidate_is_an_empty_string_not_a_crash`.

The architecture does not say whether such a case should be normalised to a
`ProviderError`, a returned `error_type`, or an empty successful response, nor
whether the conformance suite should require a particular answer. Under RE-9 the
runtime outcome is degraded in every one of those representations. No fix is
implemented and none is proposed here.

---

### PI-2 — No rule says when a provider failure is raised and when it is returned as `ProviderResponse.error_type`

**Class: Architecture Issue** · Registered 2026-10-08 (RE-9 audit).
**Design ruled — not implemented** (2026-10-09). The ruling follows the original
entry below; PI-2 is not closed by it. The original entry is retained unchanged.
**Open.** A provider-contract clarification.

Two representations of a provider failure are both permitted today:

* **Raised.** The Provider Interface's `generate` contract requires a normalised
  `ProviderError` to be raised rather than a vendor exception escaping, and the
  Gemini adapter and the Provider Registry express every failure this way.
* **Returned.** The frozen `ProviderResponse` data-model row carries a nullable
  `errorType`, `ProviderResponse.failed` treats a set `error_type` as failure,
  and `check_generate_returns_normalised_response` accepts a returned
  `ProviderResponse` whose `error_type` is set.

The architecture does not standardize when each representation should be used.
RE-9 rules how the runtime classifies both; it does not choose between them, and
neither does this entry. No fix is implemented and none is proposed here.

#### Ruling, 2026-10-09 — PI-2: provider failures are raised

**Accepted architectural ruling (Option 1, raised-only). PI-2 is design ruled —
not implemented. It is not closed.**

1. **Raised only.** A conforming Provider adapter must report operational
   provider failures by raising the standard `ProviderError`. It must not return
   `ProviderResponse(error_type=...)` as its failure-reporting mechanism.
2. **The frozen field stays.** `ProviderResponse.error_type` and the frozen
   `ProviderResponse` data-model row are unchanged.
3. **RE-9 clause 1 stays as a safety net.** The Runtime Engine keeps classifying
   a returned `ProviderResponse` with `error_type` set as a provider failure (a
   degraded turn). That defensive classification does not make such a response
   conforming adapter behaviour.
4. **RE-9-Q2 is moot only for conforming adapters.** A conforming adapter cannot
   produce a returned provider failure, so for conforming adapters the question
   does not arise. RE-9-Q2 itself stays unresolved: it still applies to a
   returned failure that reaches the RE-9 safety net from non-conforming code,
   and no wider question of post-response guardrail behaviour for unsuccessful
   responses — including an exact-empty answer — is decided here.
5. **PR-4 is narrowed, not decided.** For conforming adapters PR-4 reduces to the
   returned empty answer; see the note in PR-4's entry. No failover policy is
   decided.
6. **Workflow transitions on no-usable-answer turns stay separate and
   unresolved.** Today a returned failure or an empty answer still reaches
   `WorkflowStage`, which may commit a transition; a raised failure does not.
   This ruling does not decide empty-success behaviour, turn atomicity or
   workflow rollback.

**Unchanged:** the Provider Interface signature, `ProviderResponse`, the Provider
Registry and its failover set, the Gemini adapter (which already raises every
failure), RE-9's ruling and implementation, the Runtime Engine and §14.2's stage
order, and `docs/runtime-specification.md`. PI-1's open choice no longer includes
a returned `error_type` for a conforming adapter; PI-1 is otherwise not decided.

**Future implementation task — separately authorized, not part of this ruling.**
Make `check_generate_returns_normalised_response` in `runtime/provider/conformance.py`
fail an adapter whose `generate` returns a `ProviderResponse` with `error_type`
set, and add the minimal test in `tests/provider/` proving that such an adapter
fails conformance while a raising adapter still passes. Conformance runs one
sample call per adapter, so it enforces the rule at registration time; RE-9 clause
1 remains the runtime safety net. **PI-2 may close when that task is implemented
and verified.**

---

## Notes

Nothing here is deleted once resolved; resolved entries keep their reasoning so
the decision history stays readable.
