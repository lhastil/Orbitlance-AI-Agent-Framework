"""A minimal Orbitlance agent: one project, the Gemini adapter, a command-line channel.

    python examples/minimal_agent/run_agent.py "Are you open on Mondays?"

Each argument is one customer message; all of them form one conversation. The
framework must be installed with the `gemini` extra, a Gemini API key must be in
`GOOGLE_API_KEY` or `GEMINI_API_KEY`, and `ORBITLANCE_AUDIT_DB` must name a
writable SQLite file. See `docs/quickstart.md`.

Exit status: 0 when every message got an answer, 1 when at least one did not,
2 when the agent could not be set up.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# `SqliteAuditLogStoreError` and `AuditStoreNotConfiguredError` are failures
# `activate()` documents but its package does not re-export, so they come from
# the modules that define them.
from runtime.core_loader import CoreLoader, FilesystemCoreSource, bundled_core_root
from runtime.loader import FilesystemProjectSource, LoaderError, ProjectLoader
from runtime.models.core_bundle import CoreBundle
from runtime.observability.adapters.sqlite_store import SqliteAuditLogStoreError
from runtime.provider import ProviderError
from runtime.provider.adapters.gemini import GeminiAdapter
from runtime.provider_registry import ProviderRegistry
from runtime.runtime_engine import (
    ProjectNotActivatedError,
    RuntimeRequest,
    RuntimeResponse,
    activate,
)
from runtime.runtime_engine.errors import AuditStoreNotConfiguredError
from runtime.validation import Validator

# The project is caller-owned data; it lives beside this script, not in the
# framework. Resolved from this file so the working directory does not matter.
PROJECTS_ROOT = Path(__file__).resolve().parent / "projects"
PROJECT_ID = "lantern_kitchen"
CHANNEL = "cli"


def main(argv: list[str] | None = None) -> int:
    messages = sys.argv[1:] if argv is None else argv
    if not messages:
        return _fail("usage: run_agent.py MESSAGE [MESSAGE ...]")
    try:
        adapter = GeminiAdapter.from_environment()
    except ImportError as exc:
        return _fail(f"the Gemini SDK is not installed ({exc}); install the 'gemini' extra")
    except ProviderError as exc:
        return _fail(f"the Gemini adapter could not be created: {exc}")
    return run(messages, ProviderRegistry().register(adapter))


def run(messages: list[str], providers: ProviderRegistry) -> int:
    """Activate the project, then send each message as one turn."""
    core = CoreLoader(FilesystemCoreSource(bundled_core_root())).get_core_bundle()
    try:
        engine = activate(core, PROJECTS_ROOT, PROJECT_ID, providers)
    except (AuditStoreNotConfiguredError, SqliteAuditLogStoreError) as exc:
        return _fail(f"audit database: {exc}")
    except LoaderError as exc:
        return _fail(f"the project could not be loaded: {exc}")
    except ProjectNotActivatedError as exc:
        _report_validation_issues(core, providers)
        return _fail(str(exc))
    except ProviderError as exc:
        return _fail(f"no usable provider for {PROJECT_ID}: {exc}")

    conversation_id = uuid.uuid4().hex
    every_turn_answered = True
    for message in messages:
        response = engine.handle_request(
            RuntimeRequest(
                project_id=PROJECT_ID,
                conversation_id=conversation_id,
                message=message,
                channel=CHANNEL,
            )
        )
        print(f"> {message}")
        print(describe(response))
        every_turn_answered = every_turn_answered and response.text != ""
    return 0 if every_turn_answered else 1


def describe(response: RuntimeResponse) -> str:
    """What this channel shows for one turn.

    The runtime never writes wording for a turn without an answer; the channel
    does, from the flags alone (RE-5). It must not claim a cause the flags do
    not state.
    """
    if response.text != "":
        lines = [response.text]
        if response.degraded:
            lines.append("[answered on a reduced path: the turn is marked degraded]")
    elif response.blocked:
        lines = ["[no answer: a guardrail blocked this turn]"]
    elif response.degraded:
        lines = ["[no answer: the runtime could not produce one; the turn is marked degraded]"]
    else:
        lines = ["[no answer]"]
    if response.escalate:
        lines.append("[a guardrail flagged this turn for escalation]")
    return "\n".join(lines)


def _report_validation_issues(core: CoreBundle, providers: ProviderRegistry) -> None:
    # `activate` reports only that validation failed; the issues themselves come
    # from running the same Validator against the same project.
    project = ProjectLoader(FilesystemProjectSource(PROJECTS_ROOT)).load(PROJECT_ID)
    result = Validator(provider_registry=providers).validate_project(project, core)
    for issue in result.issues:
        print(f"{issue.severity.value} {issue.code} {issue.file}: {issue.message}", file=sys.stderr)


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
