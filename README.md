# Orbitlance AI Agent Framework

## Purpose

A modular AI Agent Framework built to be reused across multiple client projects. The framework separates reusable core logic from client-specific configuration, so a new client agent is assembled by composing prompts, knowledge, tools and workflows rather than rewriting them.

## The Core/Project separation

This is the idea the whole framework rests on.

**`core/`** holds everything that is true for every client: the agent's personality and mission, the conversation rules, the safety/escalation/compliance guardrails, the tool contracts, the workflow definitions, and the knowledge *contracts* that say which facts a client must supply.

**`projects/`** holds everything true for exactly one client: their knowledge, branding, integrations and configuration.

Nothing in `core/` mentions a client, and nothing in `projects/` re-implements framework logic. Onboarding a client means filling in templates, not writing code — and a change to shared behaviour reaches every client at once, because it lives in one place.

`core/industry_playbooks/` is the deliberate exception: it is reference material for the human authoring a project's Knowledge and Operating Constraints, and is never loaded at runtime.

## Status — active implementation

The framework is **under active implementation**. The architecture is frozen (`v1.0-architecture-freeze`) and the runtime is being built module by module against it.

**The Runtime Engine is implemented**, and the end-to-end request → response lifecycle runs: a project is loaded, resolved and validated at activation, and a request then passes through session handling, both guardrail checkpoints, budgeted prompt assembly, the provider call, workflow routing and state commit, the tool seam, and audit logging. This is verified offline against a test-fixture project with a conforming provider double; it has not been exercised against a live provider end to end, and several modules carry the deliberate limitations the table above records. This repository is not ready to serve live traffic.

### Runtime module status

The frozen specification defines fifteen runtime modules. All fifteen are implemented, plus one concrete provider adapter. Where a module is implemented with a deliberate limitation, the table says so.

| # | Module | Status |
|---|---|---|
| 1 | Core Loader | ✅ Implemented |
| 2 | Project Loader | ✅ Implemented |
| 3 | Resolver | ✅ Implemented |
| 4 | Prompt Assembler | ✅ Implemented |
| 5 | Token Budget Manager | ✅ Implemented |
| 6 | Workflow Router | ✅ Implemented — structural routing only; no semantic classification |
| 7 | Workflow State Manager | ✅ Implemented |
| 8 | Guardrail Engine | ✅ Implemented — post-response checks; pre-flight applies no content rule |
| 9 | Provider Interface | ✅ Implemented |
| 10 | Provider Registry | ✅ Implemented |
| 11 | Tool Executor | ✅ Implemented — no tool implementation is registered by default |
| 12 | Session Manager | ✅ Implemented |
| 13 | Validation Layer | ✅ Implemented |
| 14 | **Runtime Engine** | ✅ **Implemented** |
| 15 | Observability / Audit Logger | ✅ Implemented — in-memory audit store; not durable |

Where a row is qualified, the limitation is deliberate and recorded in
[docs/known-issues-runtime.md](docs/known-issues-runtime.md) rather than left to be discovered.

Alongside module 9, one concrete provider adapter is implemented: **Google Gemini 3.6 Flash**, verified against the real Gemini API.

### Verification

- **993 passed, 16 skipped** in the offline suite — no credential or network required. The 16 skipped are the live Gemini tests below, which the offline suite excludes. Figures as verified at the §15 milestone.
- **16 / 16 live Gemini tests passing** against the real API. These are opt-in and are excluded from the offline suite.

## Repository structure

```
Orbitlance-AI-Agent-Framework/
│
├── README.md
├── pyproject.toml
│
├── docs/                     architecture, configuration contract,
│   ├── architecture.md       runtime specification, guidelines,
│   ├── project-configuration.md   ADRs and known issues
│   ├── runtime-specification.md
│   ├── development-guidelines.md
│   ├── known-issues.md
│   ├── adr/
│   └── releases/
│
├── core/                     reusable framework content
│   ├── prompts/
│   ├── knowledge/
│   ├── guardrails/
│   ├── tools/
│   ├── workflows/
│   ├── templates/
│   └── industry_playbooks/   reference-only, never loaded at runtime
│
├── projects/                 per-client configuration and data
│   ├── orbitlance/
│   └── sunrise_dental_clinic/
│
├── runtime/                  the Python implementation
│   ├── models/               shared data models
│   ├── core_loader/          module 1
│   ├── loader/               module 2
│   ├── resolver/             module 3
│   ├── assembler/            module 4
│   ├── budget/               module 5
│   ├── workflow_router/      module 6
│   ├── workflow_state/       module 7
│   ├── guardrail/            module 8
│   ├── provider/             module 9 + provider adapters
│   ├── provider_registry/    module 10
│   ├── tool_executor/        module 11
│   ├── session/              module 12
│   ├── validation/           module 13
│   ├── runtime_engine/       module 14 + the activation composition root
│   └── observability/        module 15
│
├── tests/
└── assets/                   branding assets and diagrams
```

## Content overview

- **`core/prompts/`** — the agent's reusable base personality, mission and conversational behavior.
- **`core/knowledge/`** — the knowledge contracts defining what every client must supply.
- **`core/guardrails/`** — safety, escalation and compliance boundaries, loaded together as one atomic bundle.
- **`core/tools/`** — the five vendor-agnostic tool contracts the agent can act through.
- **`core/workflows/`** — step-by-step process definitions for key agent workflows.
- **`core/templates/`** — blank templates used to onboard a new client across all four extension points.
- **`core/industry_playbooks/`** — per-industry reference material for the human author. Never loaded at runtime.
- **`projects/`** — per-client configuration and data that consumes the `core/` framework.

## Getting started

```bash
pip install -e ".[dev]"     # framework + test tooling
pytest -q                   # the offline suite
```

The framework has **no runtime dependencies**. Provider SDKs are optional extras, installed only when a given adapter is used:

```bash
pip install -e ".[gemini]"  # only if using the Gemini adapter
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — how the pieces relate to one another
- [docs/project-configuration.md](docs/project-configuration.md) — the Core/Project override contract
- [docs/runtime-specification.md](docs/runtime-specification.md) — the fifteen-module runtime blueprint
- [docs/development-guidelines.md](docs/development-guidelines.md) — how to work in this repository
- [docs/adr/](docs/adr/) — architecture decision records
- [docs/known-issues.md](docs/known-issues.md) — tracked architectural issues
- [docs/known-issues-runtime.md](docs/known-issues-runtime.md) — tracked runtime implementation issues
