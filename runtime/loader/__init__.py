"""Project Loader -- docs/runtime-specification.md module 2.

Loads one project into a fully typed `ProjectContext`. This is the boundary
between Markdown and runtime objects: it is the only Markdown parser in the
runtime (ADR 0004), and everything downstream consumes typed data.

    from runtime.loader import FilesystemProjectSource, ProjectLoader

    loader = ProjectLoader(FilesystemProjectSource("projects"))
    context = loader.load("sunrise_dental_clinic")

The Loader validates nothing. A missing extension point is reported as absent;
deciding what that means belongs to the Resolver, and judging correctness
belongs to the Validation Layer.
"""

from runtime.loader.cache import InMemoryProjectCache, ProjectCache
from runtime.loader.errors import (
    DocumentReadError,
    InvalidProjectIdError,
    LoaderError,
    MalformedConfigError,
    ProjectNotFoundError,
)
from runtime.loader.project_loader import ProjectLoader
from runtime.loader.sources import FilesystemProjectSource, ProjectSource

__all__ = [
    "DocumentReadError",
    "FilesystemProjectSource",
    "InMemoryProjectCache",
    "InvalidProjectIdError",
    "LoaderError",
    "MalformedConfigError",
    "ProjectCache",
    "ProjectLoader",
    "ProjectNotFoundError",
    "ProjectSource",
]
