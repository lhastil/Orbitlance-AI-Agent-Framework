# ADR 0002 — Framework constants stay transcribed, not Core-derived (V-5)

**Status:** Accepted — implementation postponed
**Date:** 2026-08-06
**Relates to:** Principal Engineer Review finding V-5

---

## Why the issue exists

`runtime/validation/framework_spec.py` hand-transcribes structure that `core/`
already owns:

```
CANONICAL_WORKFLOWS  : discovery recommendation consultation crm_sync follow_up voice_agent
core/workflows/      : consultation crm_sync discovery follow_up recommendation voice_agent
```

Same for `TOOL_CONTRACTS`, `REQUIRED_PROMPTS`, `GUARDRAIL_BUNDLE` and
`REQUIRED_KNOWLEDGE_DOCUMENTS`. These are copies. They agree today only because
a human kept them in step.

The failure mode is specific and asymmetric. Add a seventh workflow to
`core/workflows/` and:

- `CoreWorkflowsRule` still **passes** (it checks required ⊆ present)
- `ConfigWorkflowsRule` actively **rejects** any project enabling the new
  workflow, as `CONF003 workflow unknown`

So the framework moves forward and the validator blocks adoption of the very
thing that moved. This is the same drift class the architecture review already
caught in documentation (a guideline asserting a rename that had not happened),
reintroduced in code.

## Why implementation is postponed

There is a genuine tension that must be resolved deliberately, not by reflex:

**"Required" cannot be derived from "present."** If `REQUIRED_PROMPTS` were
read from `core/prompts/`, then deleting a prompt file would make it stop being
required — the validator would cheerfully approve a Core missing a module it is
supposed to guarantee. A validator that derives its expectations from the thing
it validates cannot detect deletion.

So the correct split is not "derive everything" but:

- **Existence questions** ("is `voice_agent` a real workflow?") → derive from
  `CoreBundle`, which is authoritative about what exists.
- **Requirement questions** ("must `safety.md` exist?") → must stay declared
  independently, or the check is vacuous.

`ConfigWorkflowsRule` asks an *existence* question and should read
`CoreBundle.workflows`. But the CoreBundle is produced by the **Core Loader**,
which does not exist yet. Restructuring this now means guessing at that
module's output shape before it is written.

## What future module will own the decision

**Core Loader (Phase 2, Task 3).**

Once the Core Loader is real, `ConfigWorkflowsRule` should declare
`required_collaborators = {Collaborator.CORE_BUNDLE}` — the mechanism already
exists as of this sprint — and resolve workflow names against
`core.workflows`, deleting `CANONICAL_WORKFLOWS` from the existence path.

`REQUIRED_*` constants stay in `framework_spec.py`, because those encode
*requirements*, which are legitimately the validator's own knowledge.

## Risks if left unchanged

| Risk | Severity |
|---|---|
| Framework gains a module; validator silently blocks projects that adopt it | High |
| Two sources of truth drift without any automated detection | High |
| A deleted Core file that was never in the constant list goes unnoticed | Medium |
| Contributors do not know they must edit a Python file when changing `core/` | Medium |

## Interim mitigation (already in place)

`framework_spec.py` documents the source of every constant in comments, and
`CoreWorkflowsRule` / `CorePromptsRule` / `CoreToolContractsRule` verify that
everything the validator *requires* actually exists in Core. That catches
deletion drift today. It does **not** catch addition drift, which is the gap
this ADR tracks.

## Explicitly not done

No half-migration. Deriving some constants from Core while others stay
transcribed, with no principle distinguishing them, would be worse than either
consistent option.
