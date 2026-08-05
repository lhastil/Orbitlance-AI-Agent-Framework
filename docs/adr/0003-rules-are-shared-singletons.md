# ADR 0003 — Rules remain shared singleton instances (V-7)

**Status:** Accepted — implementation postponed
**Date:** 2026-08-06
**Relates to:** Principal Engineer Review finding V-7

---

## Why the issue exists

`runtime/validation/rules/__init__.py` assembles module-level tuples of rule
*instances*:

```python
STRUCTURE_RULES = (ProjectRootExistsRule(), ProjectIdNamingRule(), ...)
```

`default_project_rules()` returns those same objects every call, so every
`Validator()` shares one set of rule instances. Verified:

```
two Validators share the SAME rule instances: True
across separate Validator instances:         True
```

This is correct **today** because every rule is stateless: `evaluate` reads the
context and yields issues, touching no `self` attribute. But nothing enforces
that. `ValidationRule` does not prevent a subclass writing `self._cache = {}`.

The hazard is concrete at scale. Thousands of agents validated concurrently
share these instances. The first rule that memoises anything — a compiled
per-project pattern, a "already reported this" set, a counter — becomes
cross-project state leakage inside the component that decides what goes live.
Project A's data would influence Project B's verdict, intermittently and
non-deterministically.

## Why implementation is postponed

The candidate fixes each have real costs that deserve a deliberate decision
rather than a reflex during a stabilization sprint:

1. **Instantiate rules per `Validator`** — cheap, but does not prevent state
   leakage *within* one Validator reused across projects, which is the likely
   deployment shape.
2. **Instantiate rules per validation call** — safest, but allocates ~23 objects
   per validation and abandons the current module-level composition.
3. **Enforce statelessness structurally** — e.g. `__slots__ = ()` on
   `ValidationRule` so instance attributes cannot be assigned at all. Cheapest
   and strongest, but interacts with dataclass/ABC mechanics and needs its own
   verification pass.

Option 3 is the likely answer. Choosing it correctly requires testing that it
does not break subclassing patterns the rules already rely on, which is a
change to the rule base class — the single most depended-upon type in the
module — during a sprint whose purpose is stabilising that very foundation.

Doing it hastily risks the exact rewrite this ADR exists to avoid.

## What future module will own the decision

**The Validation Layer itself**, in a dedicated follow-up before the runtime
becomes concurrent.

The forcing function is the **Runtime Engine (Phase 2, later task)**, which
introduces concurrent request handling. Until something validates two projects
in parallel, the hazard is latent. It must be closed *before* that lands, not
after.

## Risks if left unchanged

| Risk | Severity |
|---|---|
| A future stateful rule silently leaks data between projects | High |
| Failure is intermittent and load-dependent — the hardest class to reproduce | High |
| It occurs in the component gating activation, so the blast radius is "wrong thing went live" | High |
| Nothing in code review flags adding `self.x` to a rule as dangerous | Medium |

## Interim mitigation (already in place)

`ValidationRule`'s docstring states rules are pure and must not mutate context
or hold state. That is documentation, not enforcement — which is precisely the
weakness recorded here.

## Explicitly not done

No speculative partial fix. Adding `__slots__ = ()` without verifying it against
every existing rule and the ABC machinery would be a change to the foundation
made on assumption rather than evidence.
