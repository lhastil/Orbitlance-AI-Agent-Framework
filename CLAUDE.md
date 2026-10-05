# CLAUDE.md

## Project isolation

The Orbitlance AI Agent Framework is a standalone project. It is unrelated to
any other repository, product or client the user works on.

- Never mix this project with any other project: do not read, reference, copy
  from, or apply changes to another repository while working here, even if one
  is attached to the same session.
- Never carry context, code, naming, branding, or assumptions from another
  project into this one, or from this one into another.
- If a task seems to involve another project, stop and ask the user first.

## Orientation

- `README.md` covers the Core/Project separation and the current runtime status.
- `docs/` holds the architecture, runtime specification, development
  guidelines, ADRs and known-issue registers.
- Python 3.11+, no runtime dependencies. Dev checks: `pytest` and `ruff check`
  (configured in `pyproject.toml`).
