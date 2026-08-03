# Runtime Specification

## Purpose

This is the engineering blueprint for the Orbitlance AI Agent Framework's runtime — the software that actually reads `core/` and `projects/<client>/` and runs a live conversation. It follows the Runtime Architecture design and exists so an engineer can implement the runtime without making any architectural decisions of their own.

**Status:** Specification phase. No implementation has started. No framework file (`core/`) has been or will be modified as part of this document. Framework-level issues discovered while writing this spec are recorded in `docs/known-issues.md`, not fixed here.

**Scope note:** This document specifies runtime *modules* — software components — not the markdown framework itself. It is new, additive documentation; it does not change how `core/` or `projects/` work.

---

## How to read this document

Each module is specified with the same 12 headings, in order, so any two modules can be compared directly:

1. Purpose · 2. Responsibilities · 3. Non-responsibilities · 4. Inputs · 5. Outputs · 6. Public Interface · 7. Internal Dependencies · 8. External Dependencies · 9. Failure Modes · 10. Validation Rules · 11. Future Extension Points · 12. Unit Test Scenarios

After the modules: the Data Model catalogue, then a single consolidated Dependency Graph covering every module (so the whole system's shape is visible in one place, not just pairwise).

---

# Modules

## 1. Core Loader

| | |
|---|---|
| **1. Purpose** | Load and cache the immutable `core/` bundle once per runtime process. |
| **2. Responsibilities** | Read `core/prompts/`, `core/guardrails/`, `core/workflows/`, `core/tools/` contracts from disk/package; parse into a `CoreBundle`; validate structural completeness at load time; cache for the process lifetime. |
| **3. Non-responsibilities** | Never load `core/industry playbooks/` into any runtime-accessible structure (reference-only, per the QA-03 rule). Never load `core/templates/` (meta-documents, not runtime content). Never mutate Core after loading. Never load anything project-specific. |
| **4. Inputs** | A path/package reference to `core/`. |
| **5. Outputs** | `CoreBundle` (see Data Models). |
| **6. Public Interface** | `load() -> CoreBundle`  ·  `getCoreBundle() -> CoreBundle` (cached accessor) |
| **7. Internal Dependencies** | None. Core Loader is a root module — nothing else must run before it, and it depends on no other runtime module. |
| **8. External Dependencies** | Filesystem/package access to `core/`. |
| **9. Failure Modes** | Missing required core file → hard fail, runtime does not start (fail closed). Unparseable structure → hard fail naming the specific file/section. |
| **10. Validation Rules** | Every required file under `core/prompts/`, `core/guardrails/`, `core/workflows/`, `core/tools/` must exist and parse into its required sections. Presence of any Industry Playbook content inside the resulting `CoreBundle` is itself a validation failure — a Core Loader defect, not a data problem. |
| **11. Future Extension Points** | Load Core from a versioned package/registry instead of raw filesystem, supporting an eventual framework/runtime repo split. |
| **12. Unit Test Scenarios** | (a) loads successfully from a complete, valid `core/`; (b) fails when a required prompt file is missing; (c) fails when a guardrail file is malformed; (d) confirms Industry Playbook content is never present in the resulting `CoreBundle` even if the source directory contains it; (e) repeated `getCoreBundle()` calls return the identical cached instance. |

---

## 2. Project Loader

| | |
|---|---|
| **1. Purpose** | Load a single project's four extension points (Knowledge, Branding, Integrations, Config) into a raw `ProjectContext`. |
| **2. Responsibilities** | Read `projects/<client>/`; parse `config.md` and the three extension-point folders; cache per project; invalidate on detected change. |
| **3. Non-responsibilities** | Never read another project's directory (this module is where Rule 6's isolation guarantee is structurally enforced). Never fall back to another project's data. Never decide what a "missing" extension point should mean — that's the Resolver's job, not the Loader's, so this module can stay a pure reader/parser. |
| **4. Inputs** | `project_id`. |
| **5. Outputs** | `ProjectContext` (raw — may have partially-missing extension points; not yet resolved against Core defaults). |
| **6. Public Interface** | `load(project_id) -> ProjectContext`  ·  `invalidate(project_id)` |
| **7. Internal Dependencies** | None required. Project Loader can run in parallel with Core Loader at startup — it doesn't need `CoreBundle` to read a project's own files. |
| **8. External Dependencies** | Filesystem/package access to `projects/<client>/`. |
| **9. Failure Modes** | Unknown `project_id` → error surfaced to Runtime Engine, never swallowed. Malformed `config.md` → error. What counts as acceptable-partial vs. fatal-missing for Knowledge specifically is an open framework question (`known-issues.md` #3) — Project Loader reports raw completeness state and leaves the consequence to the Resolver. |
| **10. Validation Rules** | `project_id` must resolve to exactly one directory, no ambiguity. Deep per-Template structural validation is delegated to the Validation Layer — Project Loader only confirms each present extension point is parseable at all. |
| **11. Future Extension Points** | Load from a database/API instead of raw filesystem once project count grows into the hundreds. |
| **12. Unit Test Scenarios** | (a) loads a fully-populated project; (b) loads a project missing Branding/Integrations without erroring; (c) errors clearly on unknown `project_id`; (d) errors on malformed `config.md`; (e) confirms two different `project_id`s never share any loaded data. |

---

## 3. Resolver

| | |
|---|---|
| **1. Purpose** | Combine `CoreBundle` + raw `ProjectContext` per the Resolution Order (`docs/project-configuration.md`), producing a `ResolvedContext` ready for everything downstream. |
| **2. Responsibilities** | Decide, per extension point, whether to use the project's version or a Core default — **not uniformly** (see note below). Record which choice was made, for observability. |
| **3. Non-responsibilities** | Never mutate `CoreBundle` or the raw `ProjectContext` (pure function). Never call an LLM provider. Never perform deep content validation (Validation Layer's job) — only enough checking to decide fallback. |
| **4. Inputs** | `CoreBundle`, `ProjectContext`. |
| **5. Outputs** | `ResolvedContext`. |
| **6. Public Interface** | `resolve(coreBundle, projectContext) -> ResolvedContext` |
| **7. Internal Dependencies** | Core Loader (for `CoreBundle`), Project Loader (for `ProjectContext`). One-directional — neither Loader depends on Resolver. |
| **8. External Dependencies** | None (pure in-memory transformation). |
| **9. Failure Modes** | Missing/incomplete Knowledge → `ResolvedContext.knowledge_incomplete = true`, never silently proceeds and never invents placeholder content. Runtime Engine checks this flag and refuses activation — Resolver itself stays a pure function with no process-control side effects. |
| **10. Validation Rules** | Every fallback decision must be recorded in the output's `fallback_log`. |
| **11. Future Extension Points** | Partial-Knowledge resolution (e.g., Services + FAQ present, Portfolio not yet) as a deliberately-allowed degraded state for non-critical files, once `known-issues.md` #3 is formally resolved and "critical vs. optional" Knowledge is defined. |
| **12. Unit Test Scenarios** | (a) fully-populated project resolves with no fallback flags; (b) missing Branding resolves to the Core default voice; (c) missing Integrations resolves to a per-tool capability-disabled state, not an error; (d) missing Knowledge sets `knowledge_incomplete = true` without inventing content; (e) resolving identical inputs twice produces identical output (purity/determinism). |

> **Note on Rule 4:** this module's spec deliberately implements the differentiated behavior identified during design (Branding/Config → safe Core defaults; Integrations → capability degradation, not a fallback; Knowledge → fail loudly, no fallback) rather than the single uniform rule as currently worded in `docs/project-configuration.md`. This is a precision gap in the framework doc, not a redesign — tracked as `known-issues.md` #3, to be reconciled when framework issues are fixed together.

---

## 4. Prompt Assembler

| | |
|---|---|
| **1. Purpose** | Build the static `PromptBundle` from a `ResolvedContext`, per the assembly order in the Runtime Architecture. |
| **2. Responsibilities** | Assemble, in order: Core Personality → Mission → Conversation Rules → Guardrails bundle → Fallback Responses → Tool Instructions → Branding overlay → Knowledge (per Token Budget Manager's selection) → active Workflow's instructions (others present only as an index). |
| **3. Non-responsibilities** | Never call an LLM provider. Never decide which workflow is active (renders whatever it's told is active). Never perform token counting itself. |
| **4. Inputs** | `ResolvedContext`, current `WorkflowState`, `ConversationContext`. |
| **5. Outputs** | `PromptBundle`. |
| **6. Public Interface** | `assemble(resolvedContext, workflowState, conversationContext) -> PromptBundle` |
| **7. Internal Dependencies** | Resolver, Token Budget Manager, Workflow State Manager (read-only — never mutates workflow state). |
| **8. External Dependencies** | None. |
| **9. Failure Modes** | `resolvedContext.knowledge_incomplete == true` → assembles a minimal, honest degraded-mode bundle (the agent explains it isn't fully configured) rather than a normal one — as defense-in-depth even though Runtime Engine should already have refused activation upstream. |
| **10. Validation Rules** | Assembled output must never contain any string sourced from `core/industry playbooks/` — enforced as a hard runtime assertion, not just a design intention. |
| **11. Future Extension Points** | Provider-specific prompt shaping (role-separated vs. flat string) delegated to each Provider adapter, with this module producing a provider-agnostic intermediate structure. |
| **12. Unit Test Scenarios** | (a) assembles correctly for a fully-resolved context; (b) output never contains a known playbook string (snapshot/fixture test); (c) a degraded (`knowledge_incomplete`) context produces the honest degraded bundle, not a hallucination risk; (d) only the active workflow's instructions appear expanded. |

---

## 5. Token Budget Manager

| | |
|---|---|
| **1. Purpose** | Decide which Knowledge (and conversation history) fits the target provider's context window, given Core's fixed overhead. |
| **2. Responsibilities** | Estimate Core + Branding + active Workflow overhead; compute remaining budget; select which Knowledge sections to include (Phase 1: all of them; later: retrieval-based). |
| **3. Non-responsibilities** | Never edit, paraphrase, or summarize Knowledge content — only selects/omits whole sections (paraphrasing customer-facing facts is a business-risk decision, not a token-management one). Never calls an LLM provider. |
| **4. Inputs** | `ResolvedContext`, target provider's context window size (via Provider Interface's capability query), `ConversationContext`. |
| **5. Outputs** | A Knowledge selection and a history window, both consumed directly by Prompt Assembler — not exposed as a standalone top-level data model, since nothing else needs to reason about them independently. |
| **6. Public Interface** | `selectKnowledge(resolvedContext, budget) -> KnowledgeSelection`  ·  `estimateOverhead(coreBundle, brandingContext, workflowState) -> tokenCount` |
| **7. Internal Dependencies** | Resolver, Provider Interface (capability query only, not a live call). |
| **8. External Dependencies** | A tokenizer appropriate to the target provider — the one place a genuine third-party/algorithmic dependency enters the runtime besides the LLM call itself. |
| **9. Failure Modes** | Core's fixed overhead alone exceeds the smallest supported provider's window → hard configuration error at Validation Layer time, never discovered mid-request. |
| **10. Validation Rules** | Selected content must never exceed the computed budget (hard assertion). Full-knowledge inclusion is always attempted first; selective inclusion only when it doesn't fit — never the reverse. |
| **11. Future Extension Points** | Retrieval-based (RAG-lite) Knowledge selection once full-inclusion stops scaling. |
| **12. Unit Test Scenarios** | (a) small knowledge base needs no truncation; (b) large knowledge base triggers selective inclusion while Core's overhead is never sacrificed; (c) history truncates from the oldest turn first, never mid-turn; (d) a larger context-window provider yields less/no truncation than a smaller one for identical input. |

---

## 6. Workflow Router

| | |
|---|---|
| **1. Purpose** | Decide, each turn, which of the 6 workflows is active — re-derived, not mechanically advanced. |
| **2. Responsibilities** | Consult each workflow's documented Trigger/Decision Point rules from `CoreBundle` against the current state and latest message to propose a transition. |
| **3. Non-responsibilities** | Never stores state itself (pure decision function — Workflow State Manager owns persistence). Never calls an LLM provider as the primary mechanism — routing should be a fast, deterministic/heuristic classification first, with an LLM-based classification only as a secondary signal for genuinely ambiguous cases (an explicit cost/latency trade-off: an LLM call on every routing decision taxes every turn of every conversation). |
| **4. Inputs** | Current `WorkflowState`, latest message (and optionally latest response), `CoreBundle`'s workflow definitions. |
| **5. Outputs** | A `WorkflowTransitionDecision` (candidate — not yet committed). |
| **6. Public Interface** | `route(currentState, latestMessage, coreBundle) -> WorkflowTransitionDecision` |
| **7. Internal Dependencies** | Core Loader (workflow definitions). Receives current state as a parameter rather than reading Workflow State Manager directly — deliberate, to keep this a pure function and avoid a Router↔StateManager cycle. Optionally Provider Interface, for ambiguous-case classification (one-directional; Provider Interface never depends back). |
| **8. External Dependencies** | None required; optionally an LLM provider for the ambiguous-case path. |
| **9. Failure Modes** | Ambiguous input with no clear signal → default to remaining in the current workflow (conservative — avoids workflow-thrashing). |
| **10. Validation Rules** | A `WorkflowTransitionDecision` must always name a workflow that exists in `CoreBundle` — routing to an undefined workflow is a hard bug, caught by assertion. |
| **11. Future Extension Points** | Pluggable routing strategies (rules-based now, ML-classifier later) behind the same interface. |
| **12. Unit Test Scenarios** | (a) a clear Discovery→Recommendation trigger routes correctly; (b) ambiguous input stays in the current workflow; (c) calling `route()` twice with identical inputs has no side effects (purity); (d) routing decisions never reference Industry Playbook content. |

---

## 7. Workflow State Manager

| | |
|---|---|
| **1. Purpose** | Own persistence and lifecycle of `WorkflowState` per conversation. |
| **2. Responsibilities** | Store current workflow, collected data-so-far, and transition history; commit `WorkflowTransitionDecision`s from Workflow Router; expose current state to Prompt Assembler and Tool Executor. |
| **3. Non-responsibilities** | Never decides what the next state should be (only persists/commits what Router hands it). Never calls an LLM provider. Never reads/writes another conversation's state. |
| **4. Inputs** | `WorkflowTransitionDecision`, `conversation_id`. |
| **5. Outputs** | `WorkflowState` (current, persisted). |
| **6. Public Interface** | `getState(conversation_id) -> WorkflowState`  ·  `commitTransition(conversation_id, decision) -> WorkflowState` |
| **7. Internal Dependencies** | Called by Workflow Router (one-directional — Router doesn't depend on State Manager reading its own output). |
| **8. External Dependencies** | A persistence store (in-memory for a single-process MVP; a real store for multi-instance scaling). |
| **9. Failure Modes** | Persistence store unavailable → the conversation cannot continue; surfaces a clear "please try again," never silently resets to a default state (a silent reset would look like the agent forgot the entire conversation — worse than an honest error). |
| **10. Validation Rules** | `commitTransition` must be atomic per `conversation_id` — no lost updates under concurrent requests for the same conversation. |
| **11. Future Extension Points** | Redis/DB-backed store for horizontal scaling; state versioning/migration across framework versions. |
| **12. Unit Test Scenarios** | (a) commits and retrieves correctly; (b) two conversations never see each other's state; (c) concurrent commits for the same conversation don't corrupt state; (d) persistence failure surfaces a clear error, never silent state loss. |

---

## 8. Guardrail Engine

| | |
|---|---|
| **1. Purpose** | Enforce the **universal** Core guardrails bundle (Safety + Escalation + Compliance) at pre-flight and post-response checkpoints. |
| **2. Responsibilities** | Pre-flight: cheap heuristic scan of the incoming message for conditions requiring immediate block/escalation, before any LLM call is made. Post-response: scan the generated response for violations (e.g., a price not present in Knowledge, an attempted diagnosis) before it ever reaches the user. |
| **3. Non-responsibilities** | Never composes the actual safe alternative response itself (detects/blocks only — a stricter re-generation or canned fallback is invoked separately). Never skips the post-response check to save latency/cost, under any circumstance. **Does not currently enforce industry-specific Escalation Considerations from Industry Playbooks** — see `known-issues.md` #5; there is presently no framework-defined runtime home for that content. |
| **4. Inputs** | Pre-flight: latest message, `ResolvedContext`. Post-response: `ProviderResponse`, `ResolvedContext` (for fact-checking against actual Knowledge). |
| **5. Outputs** | `GuardrailResult`. |
| **6. Public Interface** | `checkPreFlight(message, resolvedContext) -> GuardrailResult`  ·  `checkPostResponse(response, resolvedContext) -> GuardrailResult` |
| **7. Internal Dependencies** | Core Loader (the guardrails bundle, loaded atomically per `known-issues.md` #2's resolution approach), Resolver (`ResolvedContext`, for fact-checking). |
| **8. External Dependencies** | Optionally a secondary LLM call as a "guardrail judge" for the post-response check — recommended as a sampled/async audit pass, not a blocking check on every turn, given the cost/latency of doubling LLM calls per turn. |
| **9. Failure Modes** | Guardrail Engine's own internal failure → fail closed (block/escalate by default). A broken Guardrail Engine must never silently become a no-op. |
| **10. Validation Rules** | Every block must include a specific reason (for observability and for constructing an honest, specific fallback rather than a generic one). |
| **11. Future Extension Points** | Per-project custom guardrail additions layered on top of (never replacing) universal Core guardrails — this is the likely eventual home for the gap recorded in `known-issues.md` #5, once a framework-level decision resolves it. |
| **12. Unit Test Scenarios** | (a) pre-flight blocks an automatic-escalation-condition message without any Provider call being made (assert the Provider was never invoked); (b) post-response blocks a response containing a price absent from Knowledge; (c) post-response blocks an attempted diagnosis for a Healthcare project's conversation, to the extent the universal guardrails alone can catch it; (d) Guardrail Engine's own internal failure results in a blocked/escalated outcome, never pass-through. |

---

## 9. Provider Interface

| | |
|---|---|
| **1. Purpose** | The abstract contract every concrete LLM provider adapter must implement. |
| **2. Responsibilities** | Declare `generate(promptBundle, history) -> ProviderResponse`; declare capability metadata (context window size, streaming support, tool-calling support) queryable without a live call. |
| **3. Non-responsibilities** | Never contains provider-specific logic itself — that belongs to each concrete adapter (e.g. an Anthropic adapter, an OpenAI adapter). Never decides retry/fallback-to-secondary-provider (Provider Registry's job). |
| **4. Inputs** | `PromptBundle`, conversation history. |
| **5. Outputs** | `ProviderResponse`. |
| **6. Public Interface** | `generate(promptBundle, history) -> ProviderResponse`  ·  `getCapabilities() -> ProviderCapabilities` |
| **7. Internal Dependencies** | None — a pure interface/contract. Concrete implementations depend on external provider SDKs, not on other runtime modules. |
| **8. External Dependencies** | N/A at the interface level; each concrete implementation depends on its provider's actual SDK/API. |
| **9. Failure Modes** | Each concrete implementation must translate provider-specific errors (rate limits, auth failures, timeouts) into a small, normalized error set so the rest of the runtime never needs provider-specific error handling. |
| **10. Validation Rules** | Every concrete implementation must pass a shared conformance test suite, including a check that `getCapabilities()` reports truthfully (a provider claiming a context window size that doesn't match reality is a conformance failure, not a production surprise). |
| **11. Future Extension Points** | Streaming responses; native tool-calling capability declaration, once Tool Executor integrates with providers offering it. |
| **12. Unit Test Scenarios** | (a) the conformance suite any new adapter must pass before registration; (b) normalized error types returned for common failure classes (auth, rate-limit, timeout) regardless of underlying provider. |

---

## 10. Provider Registry

| | |
|---|---|
| **1. Purpose** | Look up and route to the correct `Provider Interface` implementation for a given project, with secondary-provider fallback. |
| **2. Responsibilities** | Maintain the registry of available providers; resolve which provider a project uses (currently unspecified in Config — `known-issues.md` #4); attempt a configured secondary provider on primary failure. |
| **3. Non-responsibilities** | Never implements LLM-calling logic itself (delegates entirely to the resolved Provider Interface implementation). Never decides prompt content. |
| **4. Inputs** | `ResolvedContext` (for provider selection, pending `known-issues.md` #4), `PromptBundle`, history. |
| **5. Outputs** | `ProviderResponse`. |
| **6. Public Interface** | `getProvider(resolvedContext) -> ProviderInterface`  ·  `generateWithFallback(resolvedContext, promptBundle, history) -> ProviderResponse` |
| **7. Internal Dependencies** | Provider Interface, Resolver. |
| **8. External Dependencies** | None directly — delegates to Provider Interface implementations, which have their own. |
| **9. Failure Modes** | Primary fails → attempt configured secondary → if none configured or it also fails, surface a clear "technical difficulties" outcome to Runtime Engine. |
| **10. Validation Rules** | A project must never route to an unregistered provider — caught as a configuration error at Validation Layer time, not mid-conversation. |
| **11. Future Extension Points** | Cost- or load-based routing across multiple providers, beyond simple primary/secondary failover. |
| **12. Unit Test Scenarios** | (a) routes to the correct provider for a given project; (b) falls back to secondary on primary failure; (c) surfaces a clear error when no provider succeeds; (d) a project configured for an unregistered provider fails at validation time, not at first request. |

---

## 11. Tool Executor

| | |
|---|---|
| **1. Purpose** | Execute the concrete action behind a workflow's tool call, using the project's configured provider for that `core/tools/*.md` contract. |
| **2. Responsibilities** | Given a `ToolRequest`, resolve the project's configured concrete provider from `ResolvedContext.integrations`; execute it; normalize the result into a `ToolResponse`; implement the error-handling behavior already documented in each tool contract (preserve data, retry per policy, never fabricate success). |
| **3. Non-responsibilities** | Never decides *when* to call a tool (only executes what it's told). Never exposes raw credentials to any other module — credential handling stays fully internal to each concrete implementation, never passed through `ToolRequest`/`ToolResponse`. |
| **4. Inputs** | `ToolRequest`, `ResolvedContext`. |
| **5. Outputs** | `ToolResponse`. |
| **6. Public Interface** | `execute(toolRequest, resolvedContext) -> ToolResponse` |
| **7. Internal Dependencies** | Resolver. Does not depend on Workflow State Manager/Router — they call this module, not the reverse. |
| **8. External Dependencies** | The actual third-party CRM/Calendar/Email/etc. APIs. |
| **9. Failure Modes** | Per each tool contract's documented policy — e.g. a timeout retries per policy then surfaces failure honestly (never optimistic success). An unconfigured Integration for a requested tool returns a "capability unavailable" `ToolResponse` rather than crashing, consistent with the Resolver's differentiated Integrations handling. |
| **10. Validation Rules** | A `ToolResponse` claiming success must correspond to an actually-confirmed external call. |
| **11. Future Extension Points** | New tool contract types beyond CRM/Calendar/Email/Integrations, following the same contract-plus-template pattern. |
| **12. Unit Test Scenarios** | (a) successfully executes a configured call and returns a normalized response; (b) returns "capability unavailable" for an unconfigured Integration rather than erroring; (c) retries per documented policy on transient failure, then surfaces failure honestly; (d) confirms no credentials ever appear in a `ToolRequest`/`ToolResponse` (structural/security test). |

---

## 12. Session Manager

| | |
|---|---|
| **1. Purpose** | Own the technical lifecycle of a session and the raw conversational record (`ConversationContext`) — distinct from Workflow State Manager, which owns business-process state. |
| **2. Responsibilities** | Create/retrieve `ConversationContext` per `conversation_id`; append each turn; track session metadata (channel, timestamps); expire/archive per retention policy. |
| **3. Non-responsibilities** | Never decides workflow logic (delegated entirely to Workflow Router/State Manager). Never persists across projects. |
| **4. Inputs** | `conversation_id`, new message/response to append. |
| **5. Outputs** | `ConversationContext`. |
| **6. Public Interface** | `getContext(conversation_id) -> ConversationContext`  ·  `appendTurn(conversation_id, message, response)`  ·  `expire(conversation_id)` |
| **7. Internal Dependencies** | None required to function — a leaf module alongside Core/Project Loader. Prompt Assembler and Guardrail Engine read from it, but it depends on nothing else in the runtime. |
| **8. External Dependencies** | A persistence store (same scaling consideration as Workflow State Manager). |
| **9. Failure Modes** | Persistence unavailable → same policy as Workflow State Manager: fail clearly, never silently lose history. |
| **10. Validation Rules** | Turns append in strict chronological order; past turns are never reordered or mutated (audit integrity, ties to Compliance). |
| **11. Future Extension Points** | Cross-channel session continuity (a web chat continuing over the phone) — explicitly not supported initially. |
| **12. Unit Test Scenarios** | (a) creates and retrieves a session correctly; (b) appends turns in order; (c) two conversations never share data; (d) expired sessions are no longer retrievable but remain in an audit archive per Compliance retention needs, never simply deleted. |

**Why this is a separate module from Workflow State Manager:** they have genuinely different responsibilities and different consumers. Session Manager holds raw conversational data needed by almost every module (Prompt Assembler's history, Guardrail Engine's context, Observability's logging). Workflow State Manager holds business-process state needed specifically by Workflow Router, Prompt Assembler's "which workflow is active" query, and Tool Executor triggering. A change to how chat history is stored shouldn't require touching workflow-transition logic, and vice versa — splitting them follows the same single-responsibility principle the framework already enforces at the documentation level.

---

## 13. Validation Layer

| | |
|---|---|
| **1. Purpose** | Verify structural and content-level correctness of Core and Project data before it's used, both at authoring time (CI) and at activation time (runtime). |
| **2. Responsibilities** | Validate a project's four extension points against their Templates' required fields (the established superset-of-contract rule); validate Core's structural completeness; produce a `ValidationResult`. |
| **3. Non-responsibilities** | Never silently "fixes" or auto-corrects invalid data — a validator that mutates what it validates is a design smell; it only reports. Never makes the activation go/no-go decision itself (Runtime Engine's job, informed by this module's output). |
| **4. Inputs** | `CoreBundle` and/or `ProjectContext`. |
| **5. Outputs** | `ValidationResult`. |
| **6. Public Interface** | `validateCore(coreBundle) -> ValidationResult`  ·  `validateProject(projectContext) -> ValidationResult` |
| **7. Internal Dependencies** | Core Loader, Project Loader (reads their outputs; never calls back into them). |
| **8. External Dependencies** | None — pure checking logic against in-memory structures. |
| **9. Failure Modes** | A `ValidationResult` reporting problems *is* this module's normal, successful output. The only true failure is the validator itself crashing on malformed input it should have handled gracefully — this must never happen; validators must be defensive against exactly the malformed data they exist to catch. |
| **10. Validation Rules** (what it checks) | Every Knowledge field the Template requires is present; no client-specific content pattern appears in what should be Core-shared files (defense-in-depth against a repeat of the earlier hardcoded-SLA class of bug); Config's declared industry playbook(s) actually exist in Core; once `known-issues.md` #4 is resolved, Config's declared LLM provider is actually registered. |
| **11. Future Extension Points** | Automated CI integration — this module formalizes the "even a script checking that every project's files match their templates" recommendation from the earlier framework review into a concrete, specified component. |
| **12. Unit Test Scenarios** | (a) a fully-valid project passes with an empty issues list; (b) a missing required field is flagged with which field/file; (c) a Config referencing a non-existent playbook is flagged; (d) the validator doesn't crash on a completely empty/garbage project directory — it reports "invalid," not an exception. |

---

## 14. Runtime Engine

| | |
|---|---|
| **1. Purpose** | The top-level orchestrator implementing the end-to-end request lifecycle — the only module that calls the others in sequence. |
| **2. Responsibilities** | Own the full per-request flow: resolve project + session → pre-flight guardrail check → prompt assembly → provider call → post-response guardrail check → workflow routing/state commit → tool execution → response delivery → observability logging. Make the activation go/no-go decision from `ValidationResult`, checked at project-activation/deploy time — not re-validated on every single message, for performance. |
| **3. Non-responsibilities** | Never implements any other module's internal logic itself. If Runtime Engine starts containing prompt-building or guardrail logic directly, that's a maintainability red flag and a violation of every other module's single responsibility. |
| **4. Inputs** | Incoming request (`project_id`, `conversation_id`, message, channel). |
| **5. Outputs** | Final response to the calling channel adapter (out of this spec's scope). |
| **6. Public Interface** | `handleRequest(request) -> RuntimeResponse` |
| **7. Internal Dependencies** | Every other module. This is intentional — Runtime Engine is the designated single "top of the graph" module, precisely so no other module needs to depend on more than one or two peers. Nothing depends back on it (true root, no cycle). |
| **8. External Dependencies** | Whatever channel adapter delivers the incoming request (out of scope here). |
| **9. Failure Modes** | Any single module's failure must be caught and translated into the appropriate degraded response — Runtime Engine is the layer responsible for ensuring a lower-level exception never becomes a raw, unhandled crash reaching the user. |
| **10. Validation Rules** | A project must have passed Validation Layer's checks before Runtime Engine accepts any request for it — a hard precondition. |
| **11. Future Extension Points** | Request prioritization/rate-limiting per project, once multi-tenant load characteristics are understood at scale. |
| **12. Unit Test Scenarios** | (a) a full successful request through every module with test doubles; (b) a pre-flight guardrail block short-circuits before any Provider call (assert Provider Registry's `generate` was never invoked); (c) a Provider failure with no working fallback surfaces a clean degraded response, not a crash; (d) a project that hasn't passed validation is rejected before any module runs. |

---

## 15. Observability / Audit Logger (additional module)

**Why this module is being introduced, unprompted by the given list:** Compliance Guardrails explicitly require auditability — "traceable actions, clear decision history, verified business records, consistent operational logging." Nearly every module above produces an event worth recording (guardrail blocks, tool calls, provider failures, workflow transitions). Bolting logging into each module individually would violate single-responsibility and guarantee inconsistent log formats across modules — the same class of problem the framework already found and fixed once (the guardrails-duplication issue). One dedicated module gives every other module a single consistent way to emit an auditable event.

| | |
|---|---|
| **1. Purpose** | Provide one consistent interface for recording auditable runtime events, satisfying Compliance's auditability requirement. |
| **2. Responsibilities** | Accept structured events from any module; timestamp and tag with `project_id`/`conversation_id`; persist them; expose a query interface for audit review. |
| **3. Non-responsibilities** | Never makes decisions based on what it logs — a pure recorder, not a decision-maker (it must never itself decide to block a request based on an observed pattern; that's Guardrail Engine's job). Never logs raw credentials or PII beyond what Compliance's data-handling rules allow. |
| **4. Inputs** | Structured event objects (type, `project_id`, `conversation_id`, payload) from any module. |
| **5. Outputs** | Persistence confirmation; queryable audit records. |
| **6. Public Interface** | `logEvent(event)`  ·  `queryAuditLog(filters) -> [AuditEvent]` |
| **7. Internal Dependencies** | None required to function — every other module depends on it, one-directionally; it depends on nothing else in the runtime (a leaf module, like Core/Project Loader). |
| **8. External Dependencies** | A durable, ideally append-only log store. |
| **9. Failure Modes** | Log store unavailable → must **not** block the conversation from proceeding (a logging failure is not a conversation failure) — but it must raise its own alert/metric, since a silent audit-logging gap is itself a Compliance risk. |
| **10. Validation Rules** | Logged events are immutable once written. |
| **11. Future Extension Points** | Structured export for compliance reporting/regulatory audits, per client industry. |
| **12. Unit Test Scenarios** | (a) logs an event and it's retrievable via query; (b) log-store unavailability doesn't block the conversation flow (Runtime Engine's response still succeeds even when this module's persistence call fails); (c) no raw credential ever appears in a logged event payload; (d) events are immutable — a second write to the same event ID is rejected or versioned, never overwritten. |

---

# Data Models

| Model | Purpose | Key Fields | Lifecycle | Ownership |
|---|---|---|---|---|
| **CoreBundle** *(added — represents Core Loader's output; needed for precision since nothing else formally typed it)* | Immutable in-memory representation of everything loaded from `core/` (excluding playbooks) | personality, mission, conversationRules, guardrailsBundle (atomic Safety+Escalation+Compliance), fallbackResponses, toolInstructions, workflowDefinitions, toolContracts | Created once at process startup; lives for the process lifetime; never mutated | Core Loader (sole writer); read by nearly every other module |
| **ProjectContext** | Raw, unresolved representation of one project's four extension points | project_id, knowledge (map, entries may be absent), branding, integrations, config, completeness flags | Created by Project Loader on load; cached per project; invalidated on file change | Project Loader (sole writer); read only by Resolver |
| **ResolvedContext** | Fully-resolved Core+Project combination, ready for everything downstream | project_id, resolvedKnowledge, resolvedBranding, resolvedIntegrations, resolvedConfig, knowledge_incomplete, fallback_log | Created per project by Resolver, typically once per activation/deploy, cached; recomputed on underlying change | Resolver (sole writer); read by Prompt Assembler, Token Budget Manager, Guardrail Engine, Tool Executor, Provider Registry |
| **ConversationContext** | Raw conversational history and session metadata | conversation_id, project_id, channel, turns (ordered), started_at, last_active_at | Created by Session Manager on first message; appended each turn; expired/archived per retention policy | Session Manager (sole writer); read by Prompt Assembler, Guardrail Engine, Observability |
| **SessionState** | Technical/infrastructural session metadata, distinct from conversational content | session_id, conversation_id, status (active/idle/expired), channel_connection_metadata, created_at, expires_at | Created alongside ConversationContext; expires independently — a session can expire while ConversationContext's history is retained for audit | Session Manager (sole writer) |
| **WorkflowState** | Which workflow is active for a conversation, plus data collected so far | conversation_id, active_workflow, collected_data, transition_history | Created by Workflow State Manager on first message (defaults to Discovery); updated via commitTransition; persists for the conversation's life | Workflow State Manager (sole writer); Workflow Router reads/proposes but never writes directly |
| **PromptBundle** | Assembled, provider-agnostic representation of what to send the LLM this turn | staticSections, conversationHistoryWindow, latestMessage | Created fresh by Prompt Assembler each turn (static portion may be cached across turns); discarded after the Provider call — ephemeral, not the durable record | Prompt Assembler (sole writer); consumed immediately by Provider Registry |
| **ProviderRequest** | Normalized request sent into a Provider Interface implementation | promptBundle, conversationHistoryWindow, providerCapabilitiesUsed | Created by Provider Registry per call; ephemeral | Provider Registry (sole writer) |
| **ProviderResponse** | Normalized response from an LLM call, regardless of provider | text, providerMetadata (tokens/latency/model), errorType (nullable), rawProviderPayload (debug only) | Created by the concrete Provider Interface implementation; passed to Guardrail Engine, then delivered or replaced | Provider Interface implementation (sole writer); read by Guardrail Engine, Runtime Engine, Observability |
| **ToolRequest** | Normalized request to execute one tool-contract action | toolContract, parameters, project_id, conversation_id | Created by Workflow State Manager/Router when a workflow calls for an action; discarded after Tool Executor processes it | Workflow State Manager (sole writer); never contains credentials |
| **ToolResponse** | Normalized result of a tool execution | success, data, errorType (nullable), capability_unavailable | Created by Tool Executor per call | Tool Executor (sole writer); read by Workflow State Manager, Observability |
| **ValidationResult** | Output of a Core or Project validation check | valid, issues [{field, file, severity, message}], validated_at, target | Created fresh per `validateCore`/`validateProject` call; not persisted long-term by this module itself | Validation Layer (sole writer); read by Runtime Engine (activation gate), Observability |
| **GuardrailResult** | Outcome of a pre-flight or post-response guardrail check | blocked, reason, escalate, checkpoint ("pre-flight"/"post-response"), triggeredRule | Created fresh per check call; consumed immediately by Runtime Engine | Guardrail Engine (sole writer) |

---

# Dependency Graph

**Rule:** every dependency is one-directional. No module depends on anything that depends back on it.

```
Runtime Engine
  ├─► Core Loader                (leaf)
  ├─► Project Loader             (leaf)
  ├─► Resolver          ─────────► Core Loader, Project Loader
  ├─► Session Manager             (leaf)
  ├─► Guardrail Engine  ─────────► Core Loader, Resolver
  ├─► Token Budget Manager ──────► Resolver, Provider Interface (capability query only)
  ├─► Prompt Assembler  ─────────► Resolver, Token Budget Manager, Workflow State Manager (read-only)
  ├─► Provider Registry ─────────► Provider Interface, Resolver
  │     └─► Provider Interface    (leaf — concrete adapters own their own external SDK deps)
  ├─► Workflow Router   ─────────► Core Loader, (optionally) Provider Interface
  ├─► Workflow State Manager      (leaf w.r.t. other runtime modules — called by Router, calls nothing back)
  ├─► Tool Executor     ─────────► Resolver
  ├─► Validation Layer  ─────────► Core Loader, Project Loader
  └─► Observability / Audit Logger (leaf — everything writes to it, it depends on nothing)
```

**Confirmed: no new circular dependency exists among these 15 runtime modules** — the graph above is a clean DAG with Runtime Engine as the single root. This is a separate claim from the framework-content-level cycles already recorded in `docs/known-issues.md` (#1 and #2), which exist in the *markdown* dependency declarations inside `core/workflows/` and `core/guardrails/`, not in this runtime module graph. Those are tracked, not fixed, per current direction.

---

## Notes

This specification assumes `docs/known-issues.md`'s five recorded issues are resolved together in a future pass, not during implementation. Where this document had to make a precision call that goes slightly beyond what a framework doc currently states verbatim (Resolver's differentiated Rule 4 behavior; Guardrail Engine's scoping around Issue #5), that's flagged inline rather than silently assumed, so the eventual framework fix and this specification can be reconciled deliberately rather than discovered as a mismatch later.
