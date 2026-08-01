# Guardrails (Prompt Injection Point)

## Purpose

Marks where the rules defined in `core/guardrails/` (Safety, Escalation, Compliance) are injected into the assembled system prompt.

This file intentionally contains no guardrail rules of its own. `core/guardrails/` is the single source of truth for safety, escalation, and compliance behavior — duplicating those rules here would create two independently-editable copies of the same policy that could silently drift apart.

---

## Responsibilities

- Reference `core/guardrails/safety.md`, `core/guardrails/escalation.md`, and `core/guardrails/compliance.md` as the content to inject at this point in the prompt
- Preserve the prompt-assembly order (Core Personality → Mission → Conversation Rules → **Guardrails** → Fallback Responses → Tool Instructions)
- Ensure guardrail content is never paraphrased or restated elsewhere in the prompt stack

---

## Must Include

- A reference to all three files in `core/guardrails/`
- Nothing else — no restated rules, no paraphrased safety principles

---

## Must Not Include

- Any safety, escalation, or compliance rule not already defined in `core/guardrails/`
- A second copy of guardrail content "for convenience" — edit `core/guardrails/` instead

---

## Inputs

- `core/guardrails/safety.md`
- `core/guardrails/escalation.md`
- `core/guardrails/compliance.md`

---

## Outputs

The assembled guardrail section of the system prompt, sourced entirely from `core/guardrails/`.

---

## Dependencies

- Core Personality
- Conversation Rules
- Safety Guardrails (`core/guardrails/safety.md`)
- Escalation Guardrails (`core/guardrails/escalation.md`)
- Compliance Guardrails (`core/guardrails/compliance.md`)
- Fallback Responses

---

## Success Criteria

- Guardrail behavior in the assembled prompt matches `core/guardrails/` exactly, with no divergence.
- Updating a rule in `core/guardrails/` is sufficient to update every agent's behavior — no second file needs to be edited.

---

## Notes

If you find yourself wanting to add a new safety, escalation, or compliance rule, add it to the appropriate file in `core/guardrails/`, not here.
