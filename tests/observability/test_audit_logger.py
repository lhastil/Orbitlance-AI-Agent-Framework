"""Audit Logger tests — specification §15.

Covers the §15.12 scenarios that are implementable, and pins the ruled decisions
— including the ones expressed as *absences*: no durability, no duplicate-id
rejection, no alert on failure, no retention, no pagination, no redaction.

Two of the four §15.12 scenarios are **not faked**:

* **(d) duplicate event IDs** — ids are generated per call by the logger, so a
  caller cannot supply one and two calls can never collide. Rather than write
  artificial duplicate detection, the tests below pin *why* the scenario cannot
  arise, so the limitation is visible and fails loudly the day callers can
  supply an id.
* **(b) store unavailability doesn't block the conversation** — proven at the
  §14 seam with a real engine, in `tests/runtime_engine/`, plus the
  end-to-end check here.

Tests citing a clause assert a **frozen requirement**; those marked
*implementation decision* assert a ruling §15 does not state.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from runtime.core_loader import CoreLoader, FilesystemCoreSource
from runtime.models.audit import AuditEvent, AuditFilters
from runtime.models.core_bundle import CoreBundle
from runtime.models.runtime import RuntimeRequest
from runtime.observability import (
    AuditLog,
    AuditLogger,
    AuditLogStore,
    InMemoryAuditLogStore,
)
from runtime.provider_registry import ProviderRegistry
from runtime.runtime_engine import activate

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "runtime" / "observability"
MODEL_FILE = REPO_ROOT / "runtime" / "models" / "audit.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "projects"
FIXTURE_ID = "fixture_clinic"


def event(
    type_: str = "runtime.turn_completed",
    project_id: str = "p1",
    conversation_id: str = "c1",
    **payload: str,
) -> AuditEvent:
    return AuditEvent(
        type=type_,
        project_id=project_id,
        conversation_id=conversation_id,
        payload=payload,
    )


class BrokenStore:
    """A store whose backing system is unavailable (§15.9)."""

    def append(self, event: AuditEvent) -> None:
        del event
        raise RuntimeError("the audit store is unreachable")

    def query(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
        del filters
        raise RuntimeError("the audit store is unreachable")


def source_files() -> list[pathlib.Path]:
    """The §15 **core**: storage-agnostic by design, and scanned as such."""
    return sorted(PACKAGE.glob("*.py")) + [MODEL_FILE]


def all_source_files() -> list[pathlib.Path]:
    """The core **and every adapter subtree**, recursively.

    `source_files()` globs one directory. That was right while the package held
    only the core, but it would let an adapter subtree escape the dependency
    scan simply by existing one level down — and code is not made compliant by
    being placed where a test does not look. This is the deliberate extension
    (OB-1): the dependency scan below walks the whole package, and permits a
    storage technology only inside `adapters/`.
    """
    return sorted(PACKAGE.rglob("*.py")) + [MODEL_FILE]


def trees() -> list[tuple[pathlib.Path, ast.Module]]:
    return [(p, ast.parse(p.read_text(encoding="utf-8"))) for p in source_files()]


def all_trees() -> list[tuple[pathlib.Path, ast.Module]]:
    return [(p, ast.parse(p.read_text(encoding="utf-8"))) for p in all_source_files()]


def is_adapter(path: pathlib.Path) -> bool:
    return "adapters" in path.parts


# =============================================================================
# event creation — §15.2's "timestamp and tag"
# =============================================================================
def test_the_logger_assigns_an_event_id() -> None:
    """Ruled: identity is the logger's, never the caller's."""
    recorded = AuditLogger().log_event(event())
    assert recorded.event_id
    assert len(recorded.event_id) == 32  # uuid4().hex, per SessionManager's precedent


def test_each_event_gets_a_distinct_id() -> None:
    logger = AuditLogger()
    ids = {logger.log_event(event()).event_id for _ in range(50)}
    assert len(ids) == 50


def test_the_logger_assigns_a_timestamp() -> None:
    """§15.2: 'timestamp and tag with project_id/conversation_id'."""
    recorded = AuditLogger(clock=lambda: "2026-09-01T12:00:00+00:00").log_event(event())
    assert recorded.timestamp == "2026-09-01T12:00:00+00:00"
    assert recorded.is_recorded


def test_the_caller_supplied_fields_are_preserved() -> None:
    """§15.4's four fields survive unchanged."""
    recorded = AuditLogger().log_event(
        event("runtime.turn_blocked", "sunrise", "conv-9", blocked="True")
    )
    assert recorded.type == "runtime.turn_blocked"
    assert recorded.project_id == "sunrise"
    assert recorded.conversation_id == "conv-9"
    assert dict(recorded.payload) == {"blocked": "True"}


def test_the_recorded_event_is_returned_as_confirmation() -> None:
    """§15.5: 'persistence confirmation' — and the only way to learn the id."""
    logger = AuditLogger()
    recorded = logger.log_event(event())
    stored = logger.query_audit_log(AuditFilters())
    assert stored == (recorded,)


# =============================================================================
# §15.12(d) — callers cannot supply an event id, so duplicates cannot arise
# =============================================================================
def test_an_id_a_caller_puts_on_an_event_is_replaced() -> None:
    """The mechanism behind the ruling, asserted rather than described.

    §15.12(d) asks that a second write to the same event ID be rejected or
    versioned. Because the logger generates every id, the case cannot arise from
    outside — and no artificial duplicate check was written to hide that.
    Recorded as OB-2.
    """
    smuggled = AuditEvent(
        type="t", project_id="p", conversation_id="c", event_id="caller-chosen"
    )
    recorded = AuditLogger().log_event(smuggled)
    assert recorded.event_id != "caller-chosen"


def test_logging_the_same_event_twice_produces_two_records() -> None:
    """Identical content is not identical identity — and must not be collapsed."""
    logger = AuditLogger()
    first = logger.log_event(event())
    second = logger.log_event(event())
    assert first.event_id != second.event_id
    assert len(logger.query_audit_log(AuditFilters())) == 2


def test_no_duplicate_detection_was_written() -> None:
    """Structural: nothing here pretends to check for a collision it cannot see."""
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name | ast.Attribute):
                name = node.id if isinstance(node, ast.Name) else node.attr
                assert name not in {"duplicate", "is_duplicate", "seen", "known_ids"}, (
                    f"{path.name} implements duplicate detection it cannot honour"
                )


# =============================================================================
# §15.12(a) — log then retrieve, and the three authorized filters
# =============================================================================
def test_a_logged_event_is_retrievable() -> None:
    """§15.12(a)."""
    logger = AuditLogger()
    logger.log_event(event())
    assert len(logger.query_audit_log(AuditFilters())) == 1


def test_empty_filters_return_everything() -> None:
    logger = AuditLogger()
    for i in range(3):
        logger.log_event(event(conversation_id=f"c{i}"))
    assert len(logger.query_audit_log(AuditFilters())) == 3
    assert AuditFilters().is_empty


def test_filter_by_type() -> None:
    logger = AuditLogger()
    logger.log_event(event("runtime.turn_completed"))
    logger.log_event(event("runtime.turn_blocked"))
    found = logger.query_audit_log(AuditFilters(type="runtime.turn_blocked"))
    assert [e.type for e in found] == ["runtime.turn_blocked"]


def test_filter_by_project_id() -> None:
    logger = AuditLogger()
    logger.log_event(event(project_id="alpha"))
    logger.log_event(event(project_id="beta"))
    found = logger.query_audit_log(AuditFilters(project_id="beta"))
    assert [e.project_id for e in found] == ["beta"]


def test_filter_by_conversation_id() -> None:
    logger = AuditLogger()
    logger.log_event(event(conversation_id="c1"))
    logger.log_event(event(conversation_id="c2"))
    found = logger.query_audit_log(AuditFilters(conversation_id="c2"))
    assert [e.conversation_id for e in found] == ["c2"]


def test_multiple_filters_are_conjunctive() -> None:
    """Ruled: supplied filters AND together."""
    logger = AuditLogger()
    logger.log_event(event("a", "alpha", "c1"))
    logger.log_event(event("a", "beta", "c1"))
    logger.log_event(event("b", "alpha", "c1"))
    logger.log_event(event("a", "alpha", "c2"))
    found = logger.query_audit_log(
        AuditFilters(type="a", project_id="alpha", conversation_id="c1")
    )
    assert len(found) == 1
    assert (found[0].type, found[0].project_id, found[0].conversation_id) == (
        "a",
        "alpha",
        "c1",
    )


def test_a_filter_that_matches_nothing_returns_empty() -> None:
    logger = AuditLogger()
    logger.log_event(event())
    assert logger.query_audit_log(AuditFilters(project_id="absent")) == ()


def test_results_come_back_in_insertion_order() -> None:
    """Ruled: oldest first, and *not* sorted by timestamp or id.

    Insertion order is the one ordering an append-only store gives without
    inventing a comparison — and two events can share a timestamp.
    """
    logger = AuditLogger(clock=lambda: "identical-for-every-event")
    for i in range(10):
        logger.log_event(event(conversation_id=f"c{i}"))
    found = logger.query_audit_log(AuditFilters())
    assert [e.conversation_id for e in found] == [f"c{i}" for i in range(10)]


def test_only_three_filter_fields_exist() -> None:
    """No pagination, no ordering field, no retention window, no scope."""
    assert set(AuditFilters.__dataclass_fields__) == {
        "type",
        "project_id",
        "conversation_id",
    }


# =============================================================================
# §15.10 — immutability and append-only
# =============================================================================
def test_a_retrieved_event_cannot_be_mutated() -> None:
    """§15.10: 'Logged events are immutable once written.'"""
    logger = AuditLogger()
    logger.log_event(event(blocked="False"))
    stored = logger.query_audit_log(AuditFilters())[0]
    with pytest.raises(Exception):  # noqa: B017 - frozen dataclass
        stored.type = "tampered"  # type: ignore[misc]
    with pytest.raises(TypeError):
        stored.payload["blocked"] = "True"  # type: ignore[index]


def test_the_event_model_is_frozen_with_slots() -> None:
    for model in (AuditEvent, AuditFilters):
        assert model.__dataclass_params__.frozen
        assert hasattr(model, "__slots__")


def test_later_writes_do_not_disturb_earlier_events() -> None:
    logger = AuditLogger()
    first = logger.log_event(event(conversation_id="first"))
    for i in range(5):
        logger.log_event(event(conversation_id=f"later-{i}"))
    stored = logger.query_audit_log(AuditFilters(conversation_id="first"))
    assert stored == (first,)


def test_the_store_never_replaces_an_entry() -> None:
    """Structural: the in-memory store has no write path but append."""
    tree = ast.parse((PACKAGE / "store.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"insert", "remove", "pop", "clear", "__setitem__"}
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            raise AssertionError("the store assigns into its list by index")


def test_query_returns_no_mutation_handle() -> None:
    """A caller holds a tuple of frozen events, never the store's own list."""
    store = InMemoryAuditLogStore()
    logger = AuditLogger(store)
    logger.log_event(event())
    found = logger.query_audit_log(AuditFilters())
    assert isinstance(found, tuple)
    assert len(store) == 1
    del found
    assert len(store) == 1


# =============================================================================
# §15.9 — failure containment
# =============================================================================
def test_a_broken_store_raises_from_the_logger() -> None:
    """The logger reports honestly; containment is the caller's guarantee.

    §15.9 requires the *conversation* to be unaffected, which §14's guard
    provides. Swallowing the failure here would leave nobody able to see it.
    """
    with pytest.raises(RuntimeError, match="unreachable"):
        AuditLogger(BrokenStore()).log_event(event())


def test_a_broken_store_does_not_affect_a_conversation(core: CoreBundle) -> None:
    """§15.12(b), end to end through the real engine."""
    from tests.runtime_engine.test_runtime_engine import FixtureAdapter

    adapter = FixtureAdapter()
    engine = activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(adapter)
    )
    engine._audit = AuditLogger(BrokenStore())  # noqa: SLF001 - substituting the seam
    response = engine.handle_request(
        RuntimeRequest(FIXTURE_ID, "conv-1", "hello", "web")
    )
    assert response.text
    assert not response.degraded
    assert not response.blocked
    assert not response.escalate


def test_the_logger_raises_no_alert_of_its_own() -> None:
    """§15.9 also asks for an alert/metric. There is no seam for one (OB-3).

    Structural, so the gap stays visible: nothing here logs, prints, or reaches
    a monitoring system, and §15.9 is therefore only partially met.
    """
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "logging", path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"print", "warn", "alert"}, path.name


# =============================================================================
# §15.3 — a pure recorder
# =============================================================================
def test_the_logger_makes_no_decision_about_what_it_records() -> None:
    """§15.3: 'a pure recorder, not a decision-maker'.

    It never inspects a payload, compares events, counts, or returns a verdict.
    """
    tree = ast.parse((PACKAGE / "logger.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name | ast.Attribute):
            name = node.id if isinstance(node, ast.Name) else node.attr
            assert name not in {
                "blocked", "escalate", "degraded", "redact", "sanitize", "scrub",
                "threshold", "count", "detect",
            }, f"the logger inspects {name}"


def test_the_payload_is_recorded_verbatim() -> None:
    """No redaction: §15.3's PII rule has no machine-checkable allowance to apply.

    Deciding what may be in a payload belongs to the module that builds one —
    §14 already builds five outcome scalars and is tested for it.
    """
    logger = AuditLogger()
    recorded = logger.log_event(event(channel="voice", failed_stage="provider"))
    assert dict(recorded.payload) == {"channel": "voice", "failed_stage": "provider"}


def test_no_event_type_enum_exists() -> None:
    """§15.2 accepts events 'from any module'; a central enum would block that."""
    import runtime.observability as observability

    assert not hasattr(observability, "EventType")
    logger = AuditLogger()
    recorded = logger.log_event(event("some.future.module.event"))
    assert recorded.type == "some.future.module.event"


# =============================================================================
# §15.7 — a leaf module; §15.8 — persistence seam
# =============================================================================
def test_the_package_imports_only_models() -> None:
    """§15.7: 'it depends on nothing else in the runtime'."""
    allowed = {"runtime.models", "runtime.observability"}
    for path, tree in trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "runtime"
            ):
                package = ".".join(node.module.split(".")[:2])
                assert package in allowed, f"{path.name} imports {node.module}"


def test_no_third_party_filesystem_network_or_concurrency() -> None:
    """No dependency was added, and no concurrency claim is made.

    Scanned **recursively**, so an adapter subtree cannot escape it (OB-1).

    A storage technology is permitted **only** under `adapters/`, and only from
    the standard library: `sqlite3`, `json` and `pathlib`. That is the whole
    extension. The core — `logger.py`, `store.py`, `__init__.py` and the model —
    stays exactly as strict as before, and every third-party package and every
    concurrency primitive remains forbidden everywhere, adapters included.
    """
    forbidden = {
        "sqlite3", "redis", "psycopg2", "pymongo", "requests", "httpx", "socket",
        "urllib", "pathlib", "os", "shutil", "threading", "asyncio", "multiprocessing",
        "json", "pickle",
    }
    #: Standard-library storage, adapter-only. Nothing third-party, nothing
    #: concurrent, nothing that reaches a network.
    adapter_allowance = {"sqlite3", "json", "pathlib"}

    for path, tree in all_trees():
        banned = forbidden - adapter_allowance if is_adapter(path) else forbidden
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned, path.name
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned, path.name
            assert not isinstance(node, ast.AsyncFunctionDef), path.name
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"Lock", "RLock", "acquire"}, path.name


def test_the_core_never_gains_a_storage_technology() -> None:
    """The allowance above is adapter-only, asserted from the other direction."""
    for path, tree in trees():
        assert not is_adapter(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in {
                        "sqlite3", "json", "pathlib",
                    }, path.name


def test_every_package_file_is_covered_by_the_recursive_scan() -> None:
    """The scan finds every `.py` under the package, not just the top level."""
    scanned = {p.resolve() for p in all_source_files()}
    for path in PACKAGE.rglob("*.py"):
        assert path.resolve() in scanned, f"{path} escapes the structural scan"


def test_the_store_is_a_protocol_with_an_in_memory_implementation() -> None:
    """The pattern three committed modules already use (§15.8's seam)."""
    assert isinstance(InMemoryAuditLogStore(), AuditLogStore)
    assert isinstance(AuditLogger(), AuditLog)


def test_a_durable_store_can_replace_the_in_memory_one() -> None:
    """The seam is real: the logger takes any store satisfying the Protocol."""

    class ElsewhereStore:
        def __init__(self) -> None:
            self.appended: list[AuditEvent] = []

        def append(self, event: AuditEvent) -> None:
            self.appended.append(event)

        def query(self, filters: AuditFilters) -> tuple[AuditEvent, ...]:
            return tuple(e for e in self.appended if filters.matches(e))

    store = ElsewhereStore()
    AuditLogger(store).log_event(event())
    assert len(store.appended) == 1


def test_nothing_in_the_runtime_imports_the_store_implementation() -> None:
    """Consumers depend on the interface, not on where events are kept.

    The composition root is the one exception — constructing the store is
    exactly its job.
    """
    root = REPO_ROOT / "runtime" / "runtime_engine" / "activation.py"
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.parent == PACKAGE or path == root:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "InMemoryAuditLogStore", path


def test_the_logger_holds_no_module_level_state() -> None:
    for path, tree in trees():
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(target, ast.Name) and not target.id.startswith("__"):
                    raise AssertionError(f"{path.name} declares module-level state")


# =============================================================================
# production wiring
# =============================================================================
@pytest.fixture(autouse=True)
def audit_database(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Every `activate()` needs `ORBITLANCE_AUDIT_DB` (R-2), and gets its own.

    The composition root fails fast without it, by design — a deployment that
    keeps no durable audit trail must not start. Each test therefore points the
    variable at its own temporary database, so nothing is shared between tests
    and nothing is written outside `tmp_path`.
    """
    path = tmp_path / "activation-audit.sqlite3"
    monkeypatch.setenv("ORBITLANCE_AUDIT_DB", str(path))
    return path


@pytest.fixture(scope="module")
def core() -> CoreBundle:
    return CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()


def activated(core: CoreBundle):
    from tests.runtime_engine.test_runtime_engine import FixtureAdapter

    return activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(FixtureAdapter())
    )


def test_activation_produces_a_working_audit_log(core: CoreBundle) -> None:
    """RE-4: the production path keeps a trail rather than discarding events."""
    engine = activated(core)
    engine.handle_request(RuntimeRequest(FIXTURE_ID, "conv-1", "hello", "web"))
    logged = engine._audit.query_audit_log(AuditFilters())  # noqa: SLF001
    assert len(logged) == 1
    assert logged[0].type == "runtime.turn_completed"
    assert logged[0].project_id == FIXTURE_ID
    assert logged[0].conversation_id == "conv-1"
    assert logged[0].event_id and logged[0].timestamp


def test_activations_share_one_backing_store_with_logical_isolation(
    core: CoreBundle,
) -> None:
    """OB-1 changed what isolates the audit trail. This records the change.

    **Before:** each activation got its own `InMemoryAuditLogStore`, so one
    activation could not see another's events **structurally** — there was no
    shared object through which they could meet.

    **Now:** every activation opens a `SqliteAuditLogStore` over the one
    database `ORBITLANCE_AUDIT_DB` names, so the events do coexist, and
    isolation is **logical** — enforced by `project_id` filtering rather than by
    separate storage. That is a real weakening of the mechanism and is recorded
    as such in AUDIT-2; this test is what keeps the remaining guarantee honest.

    Session and workflow isolation are untouched and remain structural — see
    `tests/runtime_engine/test_colliding_conversation_ids_stay_isolated_across_activations`.

    The four properties R-3 requires, in order:
    """
    first, second = activated(core), activated(core)

    # 1. separate logger and store objects still exist per activation
    assert first._audit is not second._audit  # noqa: SLF001
    assert first._audit._store is not second._audit._store  # noqa: SLF001

    # 2. ...but they address the same physical SQLite backing
    assert (
        first._audit._store.database_path  # noqa: SLF001
        == second._audit._store.database_path  # noqa: SLF001
    )

    first.handle_request(RuntimeRequest(FIXTURE_ID, "shared-id", "to the first", "web"))
    assert len(second._audit.query_audit_log(AuditFilters())) == 1  # noqa: SLF001

    # 3. project A's events are never returned by a project B query
    other_project = second._audit.query_audit_log(  # noqa: SLF001
        AuditFilters(project_id="a_different_project")
    )
    assert other_project == ()

    # 4. project_id is the isolation boundary
    same_project = second._audit.query_audit_log(  # noqa: SLF001
        AuditFilters(project_id=FIXTURE_ID)
    )
    assert len(same_project) == 1
    assert all(e.project_id == FIXTURE_ID for e in same_project)


def test_blocked_and_degraded_turns_are_recorded(core: CoreBundle) -> None:
    """The turns most worth an audit record are the ones that did not complete."""
    from tests.runtime_engine.test_runtime_engine import FixtureAdapter

    inventing = FixtureAdapter(text="That costs $4,321.")
    engine = activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(inventing)
    )
    engine.handle_request(RuntimeRequest(FIXTURE_ID, "conv-1", "how much?", "web"))
    logged = engine._audit.query_audit_log(  # noqa: SLF001
        AuditFilters(type="runtime.turn_blocked")
    )
    assert len(logged) == 1


def test_no_message_or_answer_reaches_the_audit_log(core: CoreBundle) -> None:
    """§15.3, end to end: the payload §14 builds carries no customer content."""
    engine = activated(core)
    engine.handle_request(
        RuntimeRequest(FIXTURE_ID, "conv-1", "my number is 555 0100", "web")
    )
    logged = engine._audit.query_audit_log(AuditFilters())[0]  # noqa: SLF001
    joined = " ".join(logged.payload.values())
    assert "555" not in joined
    assert "number" not in joined


@pytest.mark.parametrize("issue", ["OB-1", "OB-2", "OB-3"])
def test_every_recorded_gap_is_in_the_register(issue: str) -> None:
    """The absences above are documented, not merely omitted."""
    register = (REPO_ROOT / "docs" / "known-issues-runtime.md").read_text(
        encoding="utf-8"
    )
    assert issue in register
