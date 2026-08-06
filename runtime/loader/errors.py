"""Errors raised by the Project Loader.

The frozen spec names exactly two failure modes for this module:

    "Unknown `project_id` -> error surfaced to Runtime Engine, never swallowed.
     Malformed `config.md` -> error."

Everything else -- a missing extension point, an empty folder, an absent
document -- is *reported state*, not an error. The Loader records what is there
and lets the Resolver decide what absence means, per the frozen Resolution
Order table. Raising on a missing `branding/` would usurp that decision.
"""

from __future__ import annotations


class LoaderError(Exception):
    """Base class for every Project Loader failure."""


class ProjectNotFoundError(LoaderError):
    """`project_id` did not resolve to exactly one project directory.

    Covers both "no such project" and any ambiguity, since the frozen spec
    requires a project_id to resolve to exactly one directory.
    """

    def __init__(self, project_id: str, searched: str) -> None:
        self.project_id = project_id
        self.searched = searched
        super().__init__(
            f"Project {project_id!r} was not found at {searched!r}. "
            "The Loader never falls back to another project's data."
        )


class InvalidProjectIdError(LoaderError):
    """`project_id` could not be used to address a directory safely.

    Raised for empty ids and for any id containing path separators or parent
    traversal. This is the structural enforcement of the framework's project
    isolation rule: a project id must never be able to address a path outside
    its own directory.
    """

    def __init__(self, project_id: str, reason: str) -> None:
        self.project_id = project_id
        super().__init__(f"Invalid project id {project_id!r}: {reason}")


class DocumentReadError(LoaderError):
    """A document exists but could not be read as text."""

    def __init__(self, path: str, cause: Exception) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Could not read {path!r}: {type(cause).__name__}: {cause}")


class MalformedConfigError(LoaderError):
    """`config.md` exists but could not be parsed into a document structure.

    Deliberately narrow. "Malformed" means the file cannot be interpreted as a
    Markdown document at all -- not that its content is wrong, incomplete or
    off-template. Those are Validation Layer findings, and raising on them here
    would make the Loader a validator.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"Malformed config at {path!r}: {reason}")
