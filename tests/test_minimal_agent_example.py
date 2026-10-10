"""The Quick Start example, run offline through the real framework.

Everything is real except the provider: bundled Core, the example project, the
Validation Layer, `activate` and the Runtime Engine. The adapter is an offline
double bound to the Gemini adapter's own identity, so the project's
`LLM Provider` section is validated exactly as it is for a live run.
"""

from __future__ import annotations

import importlib.util
import pathlib
import shutil

import pytest

from runtime.core_loader import CoreLoader, FilesystemCoreSource, bundled_core_root
from runtime.loader import FilesystemProjectSource, ProjectLoader
from runtime.models.provider import ProviderCapabilities, ProviderResponse
from runtime.provider import ModelBinding
from runtime.provider.adapters.gemini import GEMINI_IDENTITY
from runtime.provider_registry import ProviderRegistry
from runtime.validation import Validator

EXAMPLE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "minimal_agent"
ANSWER = "We are open Tuesday to Saturday, 5 pm to 11 pm."


def _load_example():
    spec = importlib.util.spec_from_file_location("run_agent", EXAMPLE / "run_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _WordTokenizer:
    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def model_identity(self):
        return GEMINI_IDENTITY


class OfflineGemini:
    """Answers without a network call, under the Gemini adapter's identity."""

    def __init__(self, text: str = ANSWER) -> None:
        self._binding = ModelBinding(
            identity=GEMINI_IDENTITY,
            capabilities=ProviderCapabilities(100_000, 64),
            tokenizer=_WordTokenizer(),
        )
        self._text = text

    def get_capabilities(self) -> ProviderCapabilities:
        return self._binding.capabilities

    def model_binding(self) -> ModelBinding:
        return self._binding

    def generate(self, prompt_bundle, history) -> ProviderResponse:  # noqa: ARG002
        return ProviderResponse(text=self._text)


@pytest.fixture
def example(monkeypatch, tmp_path):
    """The example module, run from an unrelated directory with its own audit DB."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ORBITLANCE_AUDIT_DB", str(tmp_path / "audit.db"))
    return _load_example()


def test_the_example_project_validates_without_issues() -> None:
    core = CoreLoader(FilesystemCoreSource(bundled_core_root())).get_core_bundle()
    project = ProjectLoader(FilesystemProjectSource(EXAMPLE / "projects")).load(
        "lantern_kitchen"
    )
    registry = ProviderRegistry().register(OfflineGemini())
    result = Validator(provider_registry=registry).validate_project(project, core)
    assert result.valid
    assert result.issues == ()


def test_the_example_answers_through_the_runtime(example, capsys, tmp_path) -> None:
    registry = ProviderRegistry().register(OfflineGemini())
    assert example.run(["What time do you open?"], registry) == 0
    out = capsys.readouterr().out
    assert "> What time do you open?" in out
    assert ANSWER in out
    assert (tmp_path / "audit.db").is_file()


def test_a_turn_without_an_answer_is_worded_by_the_channel(example, capsys) -> None:
    """An empty provider answer is a degraded turn (RE-9); the example, as the
    channel, says so without inventing a cause (RE-5)."""
    registry = ProviderRegistry().register(OfflineGemini(text=""))
    assert example.run(["Hello"], registry) == 1
    out = capsys.readouterr().out
    assert "[no answer: the runtime could not produce one; the turn is marked degraded]" in out


def test_an_invalid_project_reports_its_validation_issues(
    example, capsys, monkeypatch, tmp_path
) -> None:
    projects = tmp_path / "projects"
    shutil.copytree(EXAMPLE / "projects", projects)
    config = projects / "lantern_kitchen" / "config.md"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "- **Primary:** google", "- **Primary:** unregistered"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(example, "PROJECTS_ROOT", projects)
    registry = ProviderRegistry().register(OfflineGemini())
    assert example.run(["Hello"], registry) == 2
    err = capsys.readouterr().err
    assert "error CONF005 config.md:" in err
    assert "has not passed validation" in err


def test_an_unopenable_audit_database_is_a_setup_failure(
    example, capsys, monkeypatch, tmp_path
) -> None:
    missing_dir = tmp_path / "missing"
    monkeypatch.setenv("ORBITLANCE_AUDIT_DB", str(missing_dir / "audit.db"))
    registry = ProviderRegistry().register(OfflineGemini())
    assert example.run(["Hello"], registry) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: audit database: could not open or initialise")
    assert str(missing_dir) in err


def test_a_project_id_without_a_directory_is_a_setup_failure(
    example, capsys, monkeypatch, tmp_path
) -> None:
    """Copying the project under a new name without changing `PROJECT_ID`."""
    projects = tmp_path / "projects"
    shutil.copytree(EXAMPLE / "projects", projects)
    (projects / "lantern_kitchen").rename(projects / "my_bistro")
    monkeypatch.setattr(example, "PROJECTS_ROOT", projects)
    registry = ProviderRegistry().register(OfflineGemini())
    assert example.run(["Hello"], registry) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: the project could not be loaded: Project 'lantern_kitchen'")
    assert str((projects / "lantern_kitchen").resolve()) in err


def test_missing_credentials_are_reported_before_any_network_call(
    example, capsys, monkeypatch
) -> None:
    pytest.importorskip("google.genai")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert example.main(["Hello"]) == 2
    err = capsys.readouterr().err
    assert "GOOGLE_API_KEY" in err
    assert "GEMINI_API_KEY" in err
