"""Packaging: what the distribution ships, and how Core is found once installed.

`pyproject.toml` lists the runtime's packages explicitly, because automatic
discovery cannot ship `core/` (see the comment there). An explicit list can
drift: a new subpackage left out of it would install without its code. These
tests keep the list equal to the source tree, and prove that the Core the
distribution ships is the Core the loader reads.
"""

from __future__ import annotations

import pathlib
import tomllib

import pytest

import runtime.core_loader.sources as core_sources
from runtime.core_loader import (
    CoreDirectoryNotFoundError,
    CoreLoader,
    FilesystemCoreSource,
    bundled_core_root,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _setuptools_config() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["setuptools"]


def test_every_runtime_package_is_listed_for_distribution() -> None:
    source_packages = {
        ".".join(init.parent.relative_to(REPO_ROOT).parts)
        for init in (REPO_ROOT / "runtime").rglob("__init__.py")
    }
    listed = set(_setuptools_config()["packages"])
    assert listed == source_packages | {"runtime._core"}


def test_core_ships_inside_the_package_with_every_document() -> None:
    config = _setuptools_config()
    assert config["package-dir"] == {"runtime._core": "core"}
    assert config["package-data"] == {"runtime._core": ["**/*.md"]}
    shipped = list((REPO_ROOT / "core").rglob("*"))
    assert all(p.suffix == ".md" for p in shipped if p.is_file()), (
        "core/ holds a non-Markdown file the package-data glob would not ship"
    )


def test_projects_and_assets_are_not_distributed() -> None:
    config = _setuptools_config()
    names = set(config["packages"]) | set(config["package-dir"].values())
    assert not any(n.split(".")[0] in {"projects", "assets", "tests"} for n in names)


def test_bundled_core_root_is_the_checkout_core_and_loads(monkeypatch, tmp_path) -> None:
    """In a source checkout it is the repository's `core/`, wherever the
    process happens to be running from."""
    monkeypatch.chdir(tmp_path)
    root = bundled_core_root()
    assert root == (REPO_ROOT / "core").resolve()
    bundled = CoreLoader(FilesystemCoreSource(root)).get_core_bundle()
    reference = CoreLoader(FilesystemCoreSource(REPO_ROOT / "core")).get_core_bundle()
    assert bundled == reference


def _locate_from(monkeypatch, install_root: pathlib.Path) -> None:
    """Make the locator believe its module lives at
    `<install_root>/runtime/core_loader/sources.py`, as it would in a wheel."""
    module = install_root / "runtime" / "core_loader" / "sources.py"
    module.parent.mkdir(parents=True)
    monkeypatch.setattr(core_sources, "__file__", str(module))


def test_bundled_core_root_prefers_the_core_shipped_in_the_package(
    monkeypatch, tmp_path
) -> None:
    """The installed-wheel branch: `runtime/_core` wins, even over a sibling
    `core/` beside the package."""
    _locate_from(monkeypatch, tmp_path)
    shipped = tmp_path / "runtime" / "_core"
    shipped.mkdir()
    (tmp_path / "core").mkdir()
    assert bundled_core_root() == shipped.resolve()


def test_bundled_core_root_raises_when_no_core_exists(monkeypatch, tmp_path) -> None:
    """Neither location exists: the locator refuses rather than guessing."""
    _locate_from(monkeypatch, tmp_path)
    with pytest.raises(CoreDirectoryNotFoundError) as caught:
        bundled_core_root()
    location = caught.value.location
    assert str((tmp_path / "runtime" / "_core").resolve()) in location
    assert str((tmp_path / "core").resolve()) in location
