# Quick Start

This gets one agent answering from the command line, using the example in
`examples/minimal_agent/`. It assumes a source checkout; the package is not
published to an index.

## Install

Python 3.11 or newer.

```bash
git clone https://github.com/lhastil/Orbitlance-AI-Agent-Framework.git
cd Orbitlance-AI-Agent-Framework
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gemini]"        # add ",dev" for pytest and ruff
```

The base install has no runtime dependencies. The `gemini` extra installs
`google-genai`, which only the Gemini adapter imports.

## What you configure, and what ships with the framework

| | Owned by | Located by |
|---|---|---|
| **Core** — personality, guardrails, workflows, tool contracts | the framework | `bundled_core_root()` |
| **Project** — your knowledge, branding, integrations, `config.md` | you | the `projects_root` you pass to `activate` |
| **Provider** — the adapter that calls the model | you register it | `ProviderRegistry` |

Never edit Core for one project: a project changes behaviour only through its
four extension points below. The example keeps its project next to the script, in
`examples/minimal_agent/projects/lantern_kitchen/`:

```
lantern_kitchen/
  config.md              required sections, provider, enabled workflows
  knowledge/             01_company.md … 08_contact.md — all eight are required
  branding/brand.md
  integrations/integrations.md
```

Templates for every file are in `core/templates/`; the override rules are in
[`project-configuration.md`](project-configuration.md). The project ID must
match `^[a-z0-9]+(_[a-z0-9]+)*$`.

The provider is selected in `config.md`:

```markdown
## LLM Provider

- **Primary:** google
- **Model:** gemini-3.6-flash
- **Secondary (optional):** none
```

`google` / `gemini-3.6-flash` is the only identity the bundled Gemini adapter
binds to. Any other value fails validation (`CONF005`) or activation
(`ProviderModelMismatchError`).

## Run the example

```bash
export GOOGLE_API_KEY="<your Gemini API key>"
export ORBITLANCE_AUDIT_DB="$HOME/orbitlance-audit.db"

python examples/minimal_agent/run_agent.py \
  "Are you open on Mondays?" \
  "Can I book a table for four on Friday at 7?"
```

Run this from the repository root, or give the script's full path. Each argument
is one turn of a single conversation. The script finds its project relative to
its own file, so the working directory does not affect what it loads.

- **Credentials.** `GeminiAdapter.from_environment()` reads `GOOGLE_API_KEY`,
  then `GEMINI_API_KEY`; the first non-empty one wins. The key goes straight to
  the SDK and is never stored or logged by the framework.
- **Audit database.** `activate()` refuses to start without
  `ORBITLANCE_AUDIT_DB`. The SQLite file is created on first use; its directory
  must already exist. One record is written per turn: the outcome flags, the
  channel and the IDs — never the message or the answer.
- **Network.** Creating the adapter calls Gemini once to read the model's token
  limits, and every turn counts tokens through the API before generating.

## What the script does

The core of `run_agent.py`, abridged (imports and error handling omitted):

```python
core = CoreLoader(FilesystemCoreSource(bundled_core_root())).get_core_bundle()
providers = ProviderRegistry().register(GeminiAdapter.from_environment())
engine = activate(core, PROJECTS_ROOT, "lantern_kitchen", providers)

response = engine.handle_request(
    RuntimeRequest(project_id="lantern_kitchen", conversation_id=conversation_id,
                   message=message, channel="cli")
)
```

`activate` loads, resolves and validates the project once. `handle_request`
never raises: every failure inside a turn becomes a `RuntimeResponse`.

| Field | Meaning |
|---|---|
| `text` | The model's answer, unchanged. Empty when the turn produced no answer. |
| `blocked` | A guardrail stopped the answer. `text` is always empty. |
| `degraded` | The turn took a reduced path — for example a contained failure, or a provider result with no usable answer. |
| `escalate` | A guardrail flagged this turn for escalation. An answer may still be present; what to do with the flag is the caller's decision. |

When `text` is empty, wording for the customer is the caller's job; the
framework supplies flags, not sentences. `describe()` in `run_agent.py` is a
minimal version. The script exits 0 when every turn was answered, 1 when one
was not, and 2 when setup failed.

To build your own agent, copy `lantern_kitchen/` into a projects directory of
your own, rename it and edit the knowledge. The project ID passed to `activate`
must be that directory's name; in `run_agent.py`, update `PROJECTS_ROOT` and
`PROJECT_ID` to match.

## When setup fails

| Message | Cause |
|---|---|
| `the Gemini SDK is not installed` | Install with `pip install -e ".[gemini]"`. |
| `no Gemini credential in the environment; set one of GOOGLE_API_KEY, GEMINI_API_KEY` | Neither variable is set, or both are empty. |
| `Gemini model metadata for gemini-3.6-flash could not be established: …` | The key was rejected or Gemini was unreachable. The reason follows, with any credential redacted. |
| `audit database: no durable audit database is configured; set ORBITLANCE_AUDIT_DB …` | Set the variable. |
| `audit database: could not open or initialise the audit database at …` | The database's directory does not exist or is not writable. |
| `the project could not be loaded: Project '…' was not found at …` | `PROJECT_ID` does not match a directory under `PROJECTS_ROOT`. |
| `project 'lantern_kitchen' has not passed validation …` | The script prints each issue above this line as `severity CODE file: message`. Errors block activation; warnings do not. |

A turn answered with `[no answer: …]` is not a setup failure. Each turn is
recorded in the audit database with its `blocked`, `escalate` and `degraded`
flags, and with the failing stage when a module failed.

## Tests

```bash
pip install -e ".[dev,gemini]"
pytest -q
```

The offline suite needs no credential and no network. It includes
`tests/test_minimal_agent_example.py`, which runs this example through real
validation, activation and the runtime with an offline adapter in place of
Gemini. It does not prove Gemini connectivity.

The live Gemini tests are skipped unless explicitly enabled; they make real
calls and use real tokens:

```bash
GEMINI_LIVE_TESTS=1 GOOGLE_API_KEY="<your key>" pytest -q tests/provider/adapters/test_gemini_live.py
```

## Current limits

- One request at a time per engine; concurrent use is unsupported.
- Conversation history is held in memory and lost when the process exits. Only
  the audit records persist.
- Tools never execute: nothing in the runtime produces a tool request yet.
- The Gemini adapter is the only provider adapter.

Open design questions are tracked in
[`known-issues-runtime.md`](known-issues-runtime.md).
