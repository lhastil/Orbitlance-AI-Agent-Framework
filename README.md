# Orbitlance AI Agent Framework

## Purpose

A modular, production-ready AI Agent Framework built to be reused across multiple client projects. The framework separates reusable core logic from client-specific configuration, so new client agents can be assembled by composing prompts, knowledge, tools and workflows rather than rewriting them.

## Responsibilities

- Provide a single, consistent foundation for building AI business agents.
- Keep reusable framework logic (`core/`) separate from client-specific data (`projects/`).
- Make every module independently understandable, testable and replaceable.
- Avoid duplicating the same information across multiple files.

## Sections

### Repository Structure

```
Orbitlance-AI-Agent-Framework/
│
├── README.md
│
├── docs/
│   ├── architecture.md
│   ├── development-guidelines.md
│   ├── project-configuration.md
│   ├── runtime-specification.md
│   └── known-issues.md
│
├── core/
│   ├── prompts/
│   ├── knowledge/
│   ├── industry_playbooks/
│   ├── guardrails/
│   ├── tools/
│   ├── templates/
│   └── workflows/
│
├── projects/
│   ├── orbitlance/
│   │   ├── knowledge/
│   │   ├── branding/
│   │   ├── integrations/
│   │   └── config.md
│   └── sunrise_dental_clinic/
│       ├── knowledge/
│       ├── branding/
│       ├── integrations/
│       └── config.md
│
└── assets/
    ├── branding/
    └── diagrams/
```

See [docs/architecture.md](docs/architecture.md) for how these pieces relate to one another, [docs/project-configuration.md](docs/project-configuration.md) for the Core/Project override contract, [docs/runtime-specification.md](docs/runtime-specification.md) for the runtime implementation blueprint, [docs/development-guidelines.md](docs/development-guidelines.md) for how to work in this repository, and [docs/known-issues.md](docs/known-issues.md) for tracked architectural issues.

### Module Overview

- **`core/prompts/`** — the agent's reusable base personality, mission and conversational behavior.
- **`core/knowledge/`** — reusable knowledge-base structure (company, services, FAQ, pricing, etc.).
- **`core/industry_playbooks/`** — per-industry reference material. Reference-only: guides the human authoring a project's Knowledge and Operating Constraints, never loaded at runtime.
- **`core/guardrails/`** — safety, escalation and compliance boundaries, loaded together as one atomic bundle.
- **`core/tools/`** — the five vendor-agnostic tool contracts the agent can act through.
- **`core/templates/`** — blank templates used to onboard a new client across all four extension points.
- **`core/workflows/`** — step-by-step process definitions for key agent workflows.
- **`projects/`** — per-client configuration and data that consumes the `core/` framework.
- **`assets/`** — branding assets and diagrams supporting the documentation.

### Status

_(placeholder — this repository is currently a structural scaffold only; content has not yet been written)_

## Notes

This repository is a **scaffold only**. Files exist to define the shape of the framework; no final prompt or business content has been written yet.
