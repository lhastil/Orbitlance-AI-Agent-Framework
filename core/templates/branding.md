# Branding Template

## Purpose

Provides a standardized template for documenting a project's client-specific brand voice and visual identity direction — the Branding extension point defined in `docs/project-configuration.md`.

The objective is to capture how this client's Core Personality should be *expressed*, without ever redefining the underlying personality contract itself.

---

## Responsibilities

- Document this client's brand voice
- Document visual identity direction
- Keep brand expression separate from Core Personality's behavioral rules
- Support consistent tone across every AI interaction for this client

---

## Template Goal

Capture everything an AI Agent needs to sound like *this specific client*, while still following the same underlying personality contract every client shares.

---

## Relationship to Core Personality

`core/prompts/01_core_personality.md` defines the underlying behavioral contract (professional, honest, concise, etc.) — this is never overridden. This template only captures the client-specific *expression* of that contract: tone, voice, and visual identity.

---

## Brand Voice

### Brand Personality

---

### Communication Style

---

### Tone of Voice

---

### Writing Style

---

### Languages Supported

---

## Visual Identity

### Color Direction

---

### Logo Concept

---

### Imagery Style

_(Note: final visual asset files belong in `assets/branding/`, shared at the repo root. This section only documents the intended *direction* — the actual logo/image files themselves are not part of this document.)_

---

## Validation Checklist

Before using this template, verify that:

- Brand voice fields don't contradict Core Personality's behavioral contract.
- Visual identity direction is documented, even if final assets don't exist yet.
- Nothing here duplicates factual information that belongs in Knowledge (`knowledge/01_company.md`'s Brand Identity section).

---

## Related Templates

- Company Template

---

## Notes

This template should be completed once per project. It never overrides Core Personality's underlying rules — only how this specific client sounds and looks.
