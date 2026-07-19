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
│
├── core/
│   ├── prompts/
│   ├── knowledge/
│   ├── industry playbooks/
│   ├── guardrails/
│   ├── tools/
│   ├── templates/
│   └── workflows/
│
├── projects/
│   └── orbitlance/
│       ├── knowledge/
│       ├── branding/
│       ├── integrations/
│       └── config.md
│
└── assets/
    ├── branding/
    └── diagrams/
```

See [docs/architecture.md](docs/architecture.md) for how these pieces relate to one another, and [docs/development-guidelines.md](docs/development-guidelines.md) for how to work in this repository.

### Module Overview

- **`core/prompts/`** — the agent's reusable base personality, mission and conversational behavior.
- **`core/knowledge/`** — reusable knowledge-base structure (company, services, FAQ, pricing, etc.).
- **`core/industry playbooks/`** — industry-specific guidance layered on top of the base agent.
- **`core/guardrails/`** — safety, escalation and compliance boundaries.
- **`core/tools/`** — definitions of external tools/integrations the agent can call.
- **`core/templates/`** — blank templates used to onboard a new client's knowledge base.
- **`core/workflows/`** — step-by-step process definitions for key agent workflows.
- **`projects/`** — per-client configuration and data that consumes the `core/` framework.
- **`assets/`** — branding assets and diagrams supporting the documentation.

### Status

_(placeholder — this repository is currently a structural scaffold only; content has not yet been written)_

## Notes

This repository is a **scaffold only**. Files exist to define the shape of the framework; no final prompt or business content has been written yet.
