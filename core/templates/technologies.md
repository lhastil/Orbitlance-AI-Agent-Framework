# Technologies Template

## Purpose

Provides a standardized template for documenting the technologies, platforms, and technical capabilities a business uses — from the customer's perspective, not an internal engineering reference.

The objective is to ensure every AI Agent can accurately answer technology-related questions without exposing implementation details that don't belong in a customer-facing knowledge base.

---

## Responsibilities

- Document each technology or platform in use
- Describe what each one enables, not how it's implemented
- Keep technology information current as the stack changes
- Support accurate, non-technical explanations of technical capabilities

---

## Template Goal

Capture all technology information required for an AI Agent to explain, in plain language, what a business's technology stack enables — without exposing credentials, architecture, or proprietary implementation details.

---

## Technology Entry

### Technology Name

---

### Category

Examples (covering every category the Technologies Knowledge contract requires):

- Programming Language
- AI Model / Provider
- Framework
- Automation Platform
- CRM Integration
- API
- Cloud Platform
- Communication Channel
- Other Supported Integration

---

### Purpose

---

### Use Cases

---

### Compatibility

---

### Limitations (if applicable)

---

### Notes

---

## Validation Checklist

Before using this template, verify that:

- Every technology is described in terms of what it enables, not how it's built.
- No API keys, credentials, internal architecture, or infrastructure details appear anywhere in this document.
- Every category required by `core/knowledge/05_technologies.md`'s "Must Include" list (programming languages, AI models/providers, frameworks, automation platforms, CRM integrations, APIs, cloud platforms, communication channels, supported integrations) is represented by at least one entry, where applicable to this business.

---

## Related Templates

- Company Template
- Services Template
- FAQ Template
- Integrations Template

---

## Notes

Each technology should have its own completed entry. This template is a strict superset of `core/knowledge/05_technologies.md`'s contract — it must never omit a required category, though it may include additional entries the contract doesn't strictly require.

The information collected here becomes the primary source for the Technologies Knowledge file and should be reviewed whenever the business's technology stack changes.
