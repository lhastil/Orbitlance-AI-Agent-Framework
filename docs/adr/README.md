# Architecture Decision Records

Decisions affecting the Orbitlance runtime. Records are **never deleted** — a
superseded decision is retained with a banner so the reasoning behind a reversal
stays readable.

**Read the status column before acting on any ADR.**

| ADR | Decision | Status | Owner of next step |
|---|---|---|---|
| [0001](0001-config-remains-prose-parsed.md) | Config remains prose-parsed; possible future machine-readable block | ⚠️ **SUPERSEDED by 0004** | — |
| [0002](0002-framework-constants-are-transcribed.md) | Framework constants stay transcribed rather than Core-derived | Accepted — postponed | Core Loader (Task 3) |
| [0003](0003-rules-are-shared-singletons.md) | Validation rules remain shared singleton instances | Accepted — postponed | Validation Layer, before Runtime Engine adds concurrency |
| [0004](0004-config-stays-markdown-loader-owns-parsing.md) | **config.md stays Markdown; Project Loader is its sole parser** | **Accepted — final** | Project Loader (Task 2) |

---

## Closed questions — do not re-open without new evidence

### Should `config.md` adopt YAML front matter or another machine-readable format?

**No. Decided in [ADR 0004](0004-config-stays-markdown-loader-owns-parsing.md).**

This was reviewed twice. The first review (ADR 0001) leaned toward amending the
framework; the second found its premises were factually wrong and reversed the
conclusion. Both records are retained.

If you arrived here from ADR 0001, from the v1.1 release notes, or from a
`# TODO` referencing V-3, the answer is: **config.md remains Markdown**, and the
concern is resolved inside `runtime/` by making the Project Loader the sole
parser — which the frozen runtime specification already required.

ADR 0004 states the one measurable threshold that would justify revisiting it.
That threshold is not currently met.

---

## Conventions

- **Accepted — final**: decided; implement as written.
- **Accepted — postponed**: the decision is to *defer*; the ADR names which
  future module owns the eventual call and the risk of leaving it.
- **Superseded**: retained for history. The banner names its replacement. Do not
  act on it.

An ADR that changes the **frozen architecture** (`core/`,
`docs/architecture.md`, `docs/project-configuration.md`) requires an explicit
architecture amendment and a version bump. An ADR that changes only `runtime/`
is a runtime refactor and does not touch the freeze. ADR 0004 is the latter.
