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

**The Runtime Engine is not implemented.** There is no end-to-end request lifecycle yet: the modules below work and are tested individually, but nothing yet orchestrates them into a complete request → response flow. This repository is not ready to serve live traffic.

### Runtime module status

The frozen specification defines fifteen runtime modules. Eight are implemented, plus one concrete provider adapter.

| # | Module | Status |
|---|---|---|
| 1 | Core Loader | ✅ Implemented |
| 2 | Project Loader | ✅ Implemented |
| 3 | Resolver | ✅ Implemented |
| 4 | Prompt Assembler | ✅ Implemented |
| 5 | Token Budget Manager | ✅ Implemented |
| 6 | Workflow Router | ⬜ Not implemented |
| 7 | Workflow State Manager | ⬜ Not implemented |
| 8 | Guardrail Engine | ⬜ Not implemented |
| 9 | Provider Interface | ✅ Implemented |
| 10 | Provider Registry | ⬜ Not implemented |
| 11 | Tool Executor | ⬜ Not implemented |
| 12 | Session Manager | ✅ Implemented |
| 13 | Validation Layer | ✅ Implemented |
| 14 | **Runtime Engine** | ⬜ **Not implemented** |
| 15 | Observability / Audit Logger | ⬜ Not implemented |

Alongside module 9, one concrete provider adapter is implemented: **Google Gemini 3.6 Flash**, verified against the real Gemini API.

### Verification

- **565 offline tests passing** — no credential or network required.
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
│   ├── provider/             module 9 + provider adapters
│   ├── session/              module 12
│   └── validation/           module 13
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
