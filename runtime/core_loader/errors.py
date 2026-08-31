"""Core Loader failures. All of them stop the runtime starting.

Specification §1.9 is unambiguous: a missing required core file or an
unparseable structure is a **hard fail — runtime does not start**. There is no
degraded Core, no partial bundle, and no default substituted for a file that
should have been there. Core is the framework's own content; if it is wrong,
every project built on it is wrong, and continuing would mean serving prompts
assembled from something nobody verified.

That is why nothing here is recoverable and none of these carry a "continue
anyway" variant. §1.9 also requires naming the specific file or section, so
every message below identifies exactly what was looked for and where.
"""

from __future__ import annotations


class CoreLoaderError(Exception):
    """Base for every Core Loader failure. Always fatal to startup."""


class CoreDirectoryNotFoundError(CoreLoaderError):
    """`core/` itself is absent or is not a directory."""

    def __init__(self, location: str) -> None:
        super().__init__(
            f"Core was not found at '{location}'. The runtime cannot start "
            "without it, and no built-in default is substituted."
        )
        self.location = location


class MissingCoreFileError(CoreLoaderError):
    """A file §1.10 requires is not present.

    Names the file and the directory that was searched, so the fix is obvious
    from the message alone without opening the loader.
    """

    def __init__(self, relative_path: str, searched: str) -> None:
        super().__init__(
            f"Required core file '{relative_path}' is missing (searched "
            f"'{searched}'). Specification 1.10 requires every file under "
            "core/prompts/, core/guardrails/, core/workflows/ and core/tools/ "
            "to exist; the runtime fails closed rather than assembling prompts "
            "from an incomplete Core."
        )
        self.relative_path = relative_path
        self.searched = searched


class MalformedCoreDocumentError(CoreLoaderError):
    """A required core document exists but does not parse into any section.

    §1.9 calls for a hard fail "naming the specific file/section". A document
    with no headings has no sections to name, which is itself the defect: every
    Core document is structured Markdown, and one that parses to nothing is
    either empty or not the document it claims to be.
    """

    def __init__(self, relative_path: str, reason: str) -> None:
        super().__init__(
            f"Core document '{relative_path}' could not be parsed: {reason}"
        )
        self.relative_path = relative_path
        self.reason = reason


class CoreReadError(CoreLoaderError):
    """A core file exists but could not be read as UTF-8 text."""

    def __init__(self, location: str, cause: Exception) -> None:
        super().__init__(f"Core file '{location}' could not be read: {cause}")
        self.location = location
        self.cause = cause


class PlaybookContentLeakError(CoreLoaderError):
    """A playbook document reached the bundle. §1.10 calls this a loader defect.

    Deliberately not a validation warning. The Validation Layer's CORE005 checks
    the same property from the outside, but by then the content is already in
    memory and reachable by the Prompt Assembler. This check runs before the
    bundle is returned, so the defect cannot escape the module that caused it.
    """

    def __init__(self, relative_path: str) -> None:
        super().__init__(
            f"Industry playbook document '{relative_path}' was loaded into the "
            "CoreBundle. Playbooks are reference-only: they guide the human "
            "authoring a project's Knowledge and must never reach the runtime. "
            "Specification 1.10 makes their presence here a Core Loader defect, "
            "not a data problem."
        )
        self.relative_path = relative_path
