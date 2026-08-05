# ADR 0001 — Config remains prose-parsed for now (V-3)

**Status:** Accepted — implementation postponed
**Date:** 2026-08-06
**Relates to:** Principal Engineer Review finding V-3

---

## Why the issue exists

`projects/<client>/config.md` carries machine-meaningful settings — the active
industry playbook, enabled workflows, the LLM provider — inside human-authored
markdown prose. The Validation Layer recovers that meaning with regular
expressions in `runtime/validation/rules/config.py`:

- `_LIST_ITEM_RE` / `_BOLD_LABEL_RE` require the exact shape `- **Primary:** value`
- `_declared_workflows` splits on em-dashes and bold labels
- `_named_playbooks` looks for backticked tokens, else the first word of a list item

This is coupling between a *document's visual formatting* and the *runtime's
behaviour*. Demonstrated, not theorised: writing the provider as
`Primary provider: anthropic` instead of `- **Primary:** anthropic` currently
produces `CONF004 provider not declared` — a false blocking error on a
correctly-configured project.

The framework never specified config.md as structured data. It was designed as
a human-readable index, and the runtime is retrofitting a parser onto it.

## Why implementation is postponed

Fixing this properly is a **framework change, not a runtime change**. It means
altering `core/templates/config.md` to carry a machine-readable block (YAML
frontmatter or a fenced data section), updating `docs/project-configuration.md`
to define that block as the contract, and migrating both existing projects.

That touches frozen architecture. Doing it inside a stabilization sprint whose
stated scope is "eliminate architectural weaknesses in the Validation Layer"
would mean unfreezing the framework to solve a runtime problem — exactly the
architectural drift this sprint exists to prevent.

Additionally, deciding it now would be premature: the Project Loader (Task 2)
is the module that will actually *own* config parsing. Designing the data
format before its primary consumer exists risks specifying the wrong shape.

## What future module will own the decision

**Project Loader (Phase 2, Task 2).**

The Loader parses `config.md` and produces `ProjectContext`. It is the natural
owner of the config format contract. The Validation Layer should consume
already-parsed, typed values from `ProjectContext` rather than re-deriving them
from raw markdown — at which point the regex helpers in `config.py` are deleted
rather than duplicated.

**Decision point:** before the Project Loader implements config parsing, decide
whether config.md gains a structured block. If it does, both the Loader and the
Validation Layer read typed fields and this ADR closes.

## Risks if left unchanged

| Risk | Severity |
|---|---|
| False blocking errors on validly-configured projects when an author uses reasonable but unanticipated markdown | High |
| Each false positive is fixed by adding another regex special case, compounding fragility | High |
| The Project Loader duplicates the same heuristics, so the fragility then lives in two modules and must be unwound from both | High |
| At hundreds of authors, formatting conventions diverge faster than regexes can absorb | High |

The last risk is the one that forces the rewrite: this approach does not fail
gradually, it fails per-author.

## Explicitly not done

No partial implementation. No speculative parser, no tolerant "try several
shapes" fallback — that would deepen the coupling while appearing to fix it.
