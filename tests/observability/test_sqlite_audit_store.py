"""Durable audit store tests — OB-1.

Proves that `SqliteAuditLogStore` satisfies the same `AuditLogStore` contract as
the in-memory store *and* survives destruction of the store object — the minimal
definition of "durable" ruled for OB-1.

**What these tests deliberately do not prove**, because the ruling puts each out
of scope and faking a test for it would be worse than its absence:

* multi-process durability — no coordination exists and none is claimed;
* thread safety — likewise;
* retention — records are kept indefinitely, by ruling;
* access control — whatever the host filesystem provides;
* **production durability** — `activate()` still wires `InMemoryAuditLogStore`,
  and a test below pins that it still does.

Every test here is deterministic and offline: `tmp_path` gives a real file, and
nothing reaches a network or a process boundary.
"""

from __future__ import annotations

import ast
import pathlib
import sqlite3

import pytest

from runtime.core_loader import CoreLoader, FilesystemCoreSource
from runtime.models.audit import AuditEvent, AuditFilters
from runtime.models.core_bundle import CoreBundle
from runtime.models.runtime import RuntimeRequest
from runtime.observability import AuditLogger, AuditLogStore, InMemoryAuditLogStore
from runtime.observability.adapters.sqlite_store import (
    TABLE,
    SqliteAuditLogStore,
    SqliteAuditLogStoreError,
)
from runtime.provider_registry import ProviderRegistry
from runtime.runtime_engine import activate

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTERS = REPO_ROOT / "runtime" / "observability" / "adapters"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "projects"
FIXTURE_ID = "fixture_clinic"



def sql_literals(path: pathlib.Path) -> str:
    """Every non-docstring string constant in a module, upper-cased.

    Docstrings are excluded deliberately: this module's prose explains *why* it
    contains no `UNIQUE`, no `UPDATE` and no `ON CONFLICT`, and a plain text
    scan would mistake the explanation for the thing. Identity, not text —
    `ast.get_docstring` returns a *cleaned* string that never matches the raw
    constant.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr):
            first = body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                docstrings.add(id(first))
    return " ".join(
        node.value.upper()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    )


def event(
    type_: str = "runtime.turn_completed",
    project_id: str = "p1",
    conversation_id: str = "c1",
    event_id: str = "e1",
    timestamp: str = "2026-09-01T12:00:00+00:00",
    **payload: str,
) -> AuditEvent:
    """A fully recorded event, as a logger would hand it to a store."""
    return AuditEvent(
        type=type_,
        project_id=project_id,
        conversation_id=conversation_id,
        payload=payload,
        event_id=event_id,
        timestamp=timestamp,
    )


@pytest.fixture
def store(tmp_path: pathlib.Path) -> SqliteAuditLogStore:
    return SqliteAuditLogStore(tmp_path / "audit.sqlite3")


# =============================================================================
# contract satisfaction
# =============================================================================
def test_the_adapter_satisfies_the_store_protocol(store: SqliteAuditLogStore) -> None:
    """Structurally — the adapter inherits nothing and imports no Protocol."""
    assert isinstance(store, AuditLogStore)


def test_the_adapter_does_not_import_the_protocol_it_satisfies() -> None:
    """A structural Protocol needs no import; not taking one keeps the edge out."""
    tree = ast.parse((ADAPTERS / "sqlite_store.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "runtime.observability"
            assert not (node.module or "").startswith("runtime.observability.")


def test_a_logger_works_over_the_durable_store(tmp_path: pathlib.Path) -> None:
    """The seam is real: `AuditLogger` takes this store like any other."""
    logger = AuditLogger(SqliteAuditLogStore(tmp_path / "audit.sqlite3"))
    recorded = logger.log_event(
        AuditEvent(type="t", project_id="p", conversation_id="c")
    )
    assert recorded.event_id and recorded.timestamp
    assert logger.query_audit_log(AuditFilters()) == (recorded,)


# =============================================================================
# append / query round-trip
# =============================================================================
def test_an_appended_event_is_retrievable(store: SqliteAuditLogStore) -> None:
    store.append(event())
    assert len(store.query(AuditFilters())) == 1


def test_every_field_round_trips(store: SqliteAuditLogStore) -> None:
    store.append(
        event(
            "runtime.turn_blocked",
            "sunrise",
            "conv-9",
            "abc123",
            "2026-01-02T03:04:05+00:00",
            blocked="True",
            channel="voice",
        )
    )
    stored = store.query(AuditFilters())[0]
    assert stored.type == "runtime.turn_blocked"
    assert stored.project_id == "sunrise"
    assert stored.conversation_id == "conv-9"
    assert stored.event_id == "abc123"
    assert stored.timestamp == "2026-01-02T03:04:05+00:00"
    assert dict(stored.payload) == {"blocked": "True", "channel": "voice"}


def test_an_empty_payload_round_trips(store: SqliteAuditLogStore) -> None:
    store.append(event())
    assert dict(store.query(AuditFilters())[0].payload) == {}


def test_an_absent_timestamp_round_trips(store: SqliteAuditLogStore) -> None:
    """`AuditEvent.timestamp` is nullable; the column follows it."""
    store.append(
        AuditEvent(type="t", project_id="p", conversation_id="c", event_id="e")
    )
    assert store.query(AuditFilters())[0].timestamp is None


def test_a_payload_with_awkward_characters_round_trips(
    store: SqliteAuditLogStore,
) -> None:
    awkward = {"quote": 'he said "hi"', "unicode": "café — ✓", "empty": ""}
    store.append(
        AuditEvent(
            type="t",
            project_id="p",
            conversation_id="c",
            event_id="e",
            payload=awkward,
        )
    )
    assert dict(store.query(AuditFilters())[0].payload) == awkward


# =============================================================================
# filters — the same three, the same AND, the same ordering
# =============================================================================
def test_empty_filters_return_everything(store: SqliteAuditLogStore) -> None:
    for i in range(3):
        store.append(event(conversation_id=f"c{i}", event_id=f"e{i}"))
    assert len(store.query(AuditFilters())) == 3


def test_filter_by_type(store: SqliteAuditLogStore) -> None:
    store.append(event("runtime.turn_completed", event_id="e1"))
    store.append(event("runtime.turn_blocked", event_id="e2"))
    found = store.query(AuditFilters(type="runtime.turn_blocked"))
    assert [e.event_id for e in found] == ["e2"]


def test_filter_by_project_id(store: SqliteAuditLogStore) -> None:
    store.append(event(project_id="alpha", event_id="e1"))
    store.append(event(project_id="beta", event_id="e2"))
    found = store.query(AuditFilters(project_id="beta"))
    assert [e.event_id for e in found] == ["e2"]


def test_filter_by_conversation_id(store: SqliteAuditLogStore) -> None:
    store.append(event(conversation_id="c1", event_id="e1"))
    store.append(event(conversation_id="c2", event_id="e2"))
    found = store.query(AuditFilters(conversation_id="c2"))
    assert [e.event_id for e in found] == ["e2"]


def test_multiple_filters_are_conjunctive(store: SqliteAuditLogStore) -> None:
    store.append(event("a", "alpha", "c1", "match"))
    store.append(event("a", "beta", "c1", "wrong-project"))
    store.append(event("b", "alpha", "c1", "wrong-type"))
    store.append(event("a", "alpha", "c2", "wrong-conversation"))
    found = store.query(
        AuditFilters(type="a", project_id="alpha", conversation_id="c1")
    )
    assert [e.event_id for e in found] == ["match"]


def test_a_project_filter_returns_no_other_projects_records(
    store: SqliteAuditLogStore,
) -> None:
    """S-10: isolation at the query level, over shared physical storage.

    Two projects share one database file. That is *not* the structural
    separation two in-memory stores give, and this test asserts only what the
    ruling claims: a `project_id` filter never returns another project's rows.
    """
    store.append(event(project_id="alpha", event_id="a1"))
    store.append(event(project_id="beta", event_id="b1"))
    alpha = store.query(AuditFilters(project_id="alpha"))
    assert [e.project_id for e in alpha] == ["alpha"]
    assert all(e.event_id != "b1" for e in alpha)


def test_a_filter_that_matches_nothing_returns_empty(
    store: SqliteAuditLogStore,
) -> None:
    store.append(event())
    assert store.query(AuditFilters(project_id="absent")) == ()


def test_results_come_back_in_insertion_order(store: SqliteAuditLogStore) -> None:
    """Ordered by `seq`, not by timestamp — every event here shares one."""
    for i in range(10):
        store.append(event(conversation_id=f"c{i}", event_id=f"e{i}"))
    found = store.query(AuditFilters())
    assert [e.event_id for e in found] == [f"e{i}" for i in range(10)]


def test_insertion_order_survives_reconstruction(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "audit.sqlite3"
    first = SqliteAuditLogStore(path)
    for i in range(5):
        first.append(event(event_id=f"e{i}"))
    del first
    reopened = SqliteAuditLogStore(path)
    for i in range(5, 10):
        reopened.append(event(event_id=f"e{i}"))
    assert [e.event_id for e in reopened.query(AuditFilters())] == [
        f"e{i}" for i in range(10)
    ]


# =============================================================================
# durability — the OB-1 definition, exactly
# =============================================================================
def test_events_survive_destruction_of_the_store_object(
    tmp_path: pathlib.Path,
) -> None:
    """The ruled definition: survives the object, readable by a new one.

    This is the whole durability claim. It says nothing about processes.
    """
    path = tmp_path / "audit.sqlite3"
    store = SqliteAuditLogStore(path)
    store.append(event(event_id="persisted", channel="web"))
    del store

    reopened = SqliteAuditLogStore(path)
    stored = reopened.query(AuditFilters())
    assert [e.event_id for e in stored] == ["persisted"]
    assert dict(stored[0].payload) == {"channel": "web"}


def test_two_stores_on_one_path_share_the_database(tmp_path: pathlib.Path) -> None:
    """S-10: shared backing storage, by construction with the same path."""
    path = tmp_path / "audit.sqlite3"
    writer = SqliteAuditLogStore(path)
    reader = SqliteAuditLogStore(path)
    writer.append(event(event_id="written-by-the-first"))
    assert [e.event_id for e in reader.query(AuditFilters())] == [
        "written-by-the-first"
    ]


def test_two_stores_on_different_paths_do_not_share(tmp_path: pathlib.Path) -> None:
    first = SqliteAuditLogStore(tmp_path / "one.sqlite3")
    second = SqliteAuditLogStore(tmp_path / "two.sqlite3")
    first.append(event())
    assert second.query(AuditFilters()) == ()


def test_the_database_file_is_created_at_construction(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "audit.sqlite3"
    assert not path.exists()
    store = SqliteAuditLogStore(path)
    assert path.exists()
    assert store.database_path == path


def test_the_path_is_explicit_with_no_default(tmp_path: pathlib.Path) -> None:
    """S-3: no environment variable, no settings object, no default location."""
    import inspect

    parameters = inspect.signature(SqliteAuditLogStore.__init__).parameters
    assert list(parameters) == ["self", "database_path"]
    assert parameters["database_path"].default is inspect.Parameter.empty
    del tmp_path


# =============================================================================
# immutability and append-only
# =============================================================================
def test_a_returned_event_cannot_be_mutated(store: SqliteAuditLogStore) -> None:
    store.append(event(blocked="False"))
    stored = store.query(AuditFilters())[0]
    with pytest.raises(Exception):  # noqa: B017 - frozen dataclass
        stored.type = "tampered"  # type: ignore[misc]
    with pytest.raises(TypeError):
        stored.payload["blocked"] = "True"  # type: ignore[index]


def test_later_writes_do_not_disturb_earlier_events(
    store: SqliteAuditLogStore,
) -> None:
    store.append(event(event_id="first", channel="web"))
    for i in range(5):
        store.append(event(event_id=f"later-{i}"))
    first = store.query(AuditFilters())[0]
    assert first.event_id == "first"
    assert dict(first.payload) == {"channel": "web"}


def test_the_adapter_contains_no_update_or_delete(tmp_path: pathlib.Path) -> None:
    """Append-only as a property of the code, not a promise about it."""
    sql = sql_literals(ADAPTERS / "sqlite_store.py")
    for forbidden in ("UPDATE ", "DELETE ", "DROP ", "REPLACE ", "ON CONFLICT"):
        assert forbidden not in sql, f"the adapter's SQL contains {forbidden.strip()}"
    del tmp_path


def test_no_duplicate_id_mechanism_exists(store: SqliteAuditLogStore) -> None:
    """OB-2: ids are logger-generated, so a collision cannot arise from outside.

    No `UNIQUE` constraint, no lookup-before-insert. Two events carrying one id
    are two rows — a check that can never fire is worse than an honest absence.
    """
    assert "UNIQUE" not in sql_literals(ADAPTERS / "sqlite_store.py")
    store.append(event(event_id="same"))
    store.append(event(event_id="same"))
    assert len(store.query(AuditFilters())) == 2


# =============================================================================
# corruption and failure — S-11
# =============================================================================
def test_a_malformed_payload_raises_and_is_never_skipped(
    tmp_path: pathlib.Path,
) -> None:
    """S-11: a corrupt record raises; it is not silently dropped."""
    path = tmp_path / "audit.sqlite3"
    store = SqliteAuditLogStore(path)
    store.append(event(event_id="good"))

    connection = sqlite3.connect(path)
    with connection:
        connection.execute(
            f"INSERT INTO {TABLE} "  # noqa: S608 - fixed table name, test fixture
            "(event_id, type, project_id, conversation_id, timestamp, payload) "
            "VALUES ('broken', 't', 'p', 'c', NULL, 'not-json')"
        )
    connection.close()

    with pytest.raises(SqliteAuditLogStoreError, match="unreadable payload"):
        store.query(AuditFilters())


def test_a_payload_of_the_wrong_shape_raises(tmp_path: pathlib.Path) -> None:
    """The model declares `Mapping[str, str]`; a stored list is not one."""
    path = tmp_path / "audit.sqlite3"
    store = SqliteAuditLogStore(path)
    connection = sqlite3.connect(path)
    with connection:
        connection.execute(
            f"INSERT INTO {TABLE} "  # noqa: S608 - fixed table name, test fixture
            "(event_id, type, project_id, conversation_id, timestamp, payload) "
            "VALUES ('broken', 't', 'p', 'c', NULL, '[1, 2, 3]')"
        )
    connection.close()

    with pytest.raises(SqliteAuditLogStoreError, match="not a mapping"):
        store.query(AuditFilters())


def test_a_corrupt_database_raises_on_query(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "audit.sqlite3"
    SqliteAuditLogStore(path)
    store = SqliteAuditLogStore(path)
    path.write_bytes(b"this is not a database")
    with pytest.raises(SqliteAuditLogStoreError):
        store.query(AuditFilters())


def test_an_unusable_path_raises_at_construction(tmp_path: pathlib.Path) -> None:
    """A directory is not a database file."""
    directory = tmp_path / "a_directory"
    directory.mkdir()
    with pytest.raises(SqliteAuditLogStoreError):
        SqliteAuditLogStore(directory)


def test_no_sqlite_type_ever_crosses_the_seam(tmp_path: pathlib.Path) -> None:
    """Every backing-store failure is normalised, as §9.9 does for providers."""
    directory = tmp_path / "a_directory"
    directory.mkdir()
    try:
        SqliteAuditLogStore(directory)
    except SqliteAuditLogStoreError as raised:
        assert not isinstance(raised, sqlite3.Error)
    else:  # pragma: no cover - the call above must raise
        pytest.fail("expected SqliteAuditLogStoreError")


# =============================================================================
# the store's failures stay outside RuntimeResponse — §15.9
# =============================================================================
@pytest.fixture(scope="module")
def core() -> CoreBundle:
    return CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()


def test_a_failing_durable_store_does_not_change_the_response(
    core: CoreBundle, tmp_path: pathlib.Path
) -> None:
    """§15.9 end to end, with the durable adapter behind a real engine."""
    from tests.runtime_engine.test_runtime_engine import FixtureAdapter

    path = tmp_path / "audit.sqlite3"
    engine = activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(FixtureAdapter())
    )
    healthy = engine.handle_request(
        RuntimeRequest(FIXTURE_ID, "conv-1", "hello", "web")
    )

    broken = activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(FixtureAdapter())
    )
    store = SqliteAuditLogStore(path)
    path.write_bytes(b"this is not a database")
    broken._audit = AuditLogger(store)  # noqa: SLF001 - substituting the seam
    degraded_attempt = broken.handle_request(
        RuntimeRequest(FIXTURE_ID, "conv-1", "hello", "web")
    )

    assert degraded_attempt == healthy
    assert not degraded_attempt.blocked
    assert not degraded_attempt.degraded


def test_the_production_path_still_uses_the_in_memory_store(
    core: CoreBundle,
) -> None:
    """OB-1 is *not* closed by this change: `activate()` is untouched.

    "Durable adapter implemented" is not "production audit persistence
    durable", and this test is what keeps the two apart.
    """
    from tests.runtime_engine.test_runtime_engine import FixtureAdapter

    engine = activate(
        core, FIXTURES, FIXTURE_ID, ProviderRegistry().register(FixtureAdapter())
    )
    assert isinstance(engine._audit._store, InMemoryAuditLogStore)  # noqa: SLF001

    activation = (
        REPO_ROOT / "runtime" / "runtime_engine" / "activation.py"
    ).read_text(encoding="utf-8")
    assert "SqliteAuditLogStore" not in activation
    assert "InMemoryAuditLogStore" in activation


# =============================================================================
# structural: dependencies, concurrency, isolation of the subtree
# =============================================================================
def test_the_adapter_imports_only_models_and_the_standard_library() -> None:
    allowed_runtime = {"runtime.models"}
    permitted_stdlib = {"__future__", "json", "sqlite3", "pathlib", "collections", "typing"}
    for path in ADAPTERS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] in permitted_stdlib, path.name
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("runtime"):
                    assert ".".join(module.split(".")[:2]) in allowed_runtime, path.name
                else:
                    assert module.split(".")[0] in permitted_stdlib, path.name


def test_the_adapter_introduces_no_third_party_dependency() -> None:
    """`dependencies = []` must still hold; `sqlite3` and `json` are stdlib."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject
    for package in ("sqlalchemy", "redis", "psycopg", "pymongo", "boto3"):
        assert package not in pyproject


def test_the_adapter_claims_no_concurrency() -> None:
    """RE-3 and V-7 are untouched: no lock, no thread, no async, no pool."""
    forbidden_modules = {"threading", "asyncio", "concurrent", "multiprocessing"}
    forbidden_attrs = {"Lock", "RLock", "acquire", "Thread", "gather", "submit"}
    for path in ADAPTERS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not isinstance(node, ast.AsyncFunctionDef), path.name
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_modules, path.name
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden_modules
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden_attrs, path.name


def test_the_adapters_package_imports_no_implementation() -> None:
    """No auto-discovery, and no de facto default — the §9 adapter rule."""
    tree = ast.parse((ADAPTERS / "__init__.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


def test_nothing_in_the_runtime_imports_the_adapter() -> None:
    """It is reachable only by an explicit import that nothing makes today."""
    for path in (REPO_ROOT / "runtime").rglob("*.py"):
        if path.parent == ADAPTERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "adapters.sqlite_store" not in (node.module or ""), path
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "adapters.sqlite_store" not in alias.name, path


def test_the_observability_core_gained_no_storage_knowledge() -> None:
    """`logger.py`, `store.py` and the model stay storage-agnostic."""
    core_files = [
        REPO_ROOT / "runtime" / "observability" / "logger.py",
        REPO_ROOT / "runtime" / "observability" / "store.py",
        REPO_ROOT / "runtime" / "observability" / "__init__.py",
        REPO_ROOT / "runtime" / "models" / "audit.py",
    ]
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        for forbidden in ("sqlite3", "import json", "SqliteAuditLogStore"):
            assert forbidden not in source, f"{path.name} references {forbidden}"
