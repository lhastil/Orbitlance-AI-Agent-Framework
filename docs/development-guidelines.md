# Development Guidelines

This document defines the standards used when developing AI Agents with the Orbitlance AI Agent Framework.

---

# General Principles

Build reusable components.

Avoid duplicated logic.

Prefer modular design.

Keep every file focused on a single responsibility.

---

# Prompt Guidelines

Prompts define behavior.

Do not store company information inside prompts.

Keep prompts modular.

Avoid long monolithic prompts.

---

# Knowledge Guidelines

Knowledge stores facts.

Knowledge should be easy to update without modifying prompts.

Keep information concise and accurate.

Avoid duplicated information across multiple files.

---

# Workflow Guidelines

Every workflow should represent one business process.

Workflows should be reusable across different projects whenever possible.

---

# Naming Convention

Use lowercase filenames.

Separate words with underscores.

Examples:

core_personality.md

lead_qualification.md

consultation_request.md

---

# Version Control

Commit frequently.

Keep commits small and focused.

Use meaningful commit messages.

Example:

Add consultation request module

Improve discovery prompt

Update pricing knowledge

---

# Documentation

Every module should explain:

Purpose

Responsibilities

Dependencies (if any)

Notes

---

# Future Compatibility

Design every module with future expansion in mind.

New modules should be added without modifying existing ones whenever possible.
