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

**No open Architecture Issue.** PA-3 was recorded as one on 2026-08-09 and
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
| **PA-4** | **§4 cites an assembly order in a section that does not exist** | **Documentation / Reporting** |

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

## Notes

Nothing here is deleted once resolved; resolved entries keep their reasoning so
the decision history stays readable.
