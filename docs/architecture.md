# Framework Architecture

## Purpose

This document explains how the Orbitlance AI Agent Framework is structured and how each module works together.

The goal is to keep the framework modular, maintainable, and reusable across different client projects.

---

# High-Level Architecture

The framework is divided into independent modules.

Each module has a single responsibility.

```
Prompts
        │
        ▼
Knowledge Base
        │
        ▼
Reasoning
        │
        ▼
Workflows
        │
        ▼
Tools
        │
        ▼
Response

```


---

# Module Overview

## Prompts

Defines the AI's behavior.

Examples:

- Personality
- Mission
- Conversation Rules
- Discovery
- Recommendation
- Lead Qualification

Prompts define *how* the AI behaves.

They never contain business knowledge.

---

## Knowledge Base

Stores factual information.

Examples:

- Company
- Services
- FAQ
- Process
- Pricing
- Portfolio

Knowledge defines *what* the AI knows.

It never defines conversation logic.

---

## Templates

Fill-in documents used to onboard a new client's knowledge base.

Every `core/knowledge/` file defines the **contract**: what a company's knowledge must (and must not) contain. Every `core/templates/` file is the **literal document a new client fills in** to satisfy that contract, and is copied into `projects/<client>/knowledge/` once completed.

A Template is always a **strict superset** of its matching Knowledge contract:

- Every field the Knowledge contract requires must appear in the matching Template.
- A Template may include additional optional fields (e.g. brand tone, competitive positioning) that help a client articulate their business, even when the Knowledge contract doesn't strictly require them.
- A Template must never omit, contradict, or replace a Knowledge requirement — it only ever adds detail on top of it.

Knowledge and Templates are not two independent descriptions of the same thing — Knowledge is the rulebook, Templates are the worksheet built from it.

---

## Workflows

Defines repeatable business processes.

Examples:

- Consultation Request
- Lead Qualification
- CRM Sync
- Voice Call Flow

Workflows describe how tasks are completed.

---

## Tools

External integrations used by the AI.

Examples:

- CRM
- Email
- Forms
- APIs

Tools allow the AI to perform actions.

---

## Projects

Contains client-specific implementations.

Each project reuses the same Core framework and may only extend it through four documented extension points: Knowledge, Branding, Integrations, and Config. Everything else in Core is shared, read-only, and identical across every client.

See [docs/project-configuration.md](project-configuration.md) for the full override contract, including the resolution order used when a project doesn't provide one of its extension points, and the isolation guarantee between projects.

---

# Design Principles

Every module has one responsibility.

Modules should remain independent whenever possible.

Business knowledge should never be duplicated across multiple files.

Conversation logic should remain separated from factual knowledge.

The framework should always be easy to expand without major restructuring.

---

# Future Growth

The framework is designed to support:

- Website AI Agents
- Voice AI Agents
- Internal Company Assistants
- Customer Support Agents
- Sales Consultants
- Industry-specific AI Solutions

Additional modules can be added without changing the existing architecture.
