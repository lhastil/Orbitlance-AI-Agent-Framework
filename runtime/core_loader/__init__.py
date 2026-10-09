"""Core Loader — specification §1.

Reads `core/` into an immutable `CoreBundle` and caches it for the process
lifetime. The root of the module graph: nothing runs before it, and every
consumer of `CoreBundle` finally has a producer.

    from runtime.core_loader import CoreLoader, FilesystemCoreSource

    loader = CoreLoader(FilesystemCoreSource("core"))
    core = loader.get_core_bundle()   # cached for the process lifetime

`bundled_core_root()` returns the Core that ships with this copy of the
framework — inside an installed package or at a checkout's root — so a caller
need not depend on the working directory:

    loader = CoreLoader(FilesystemCoreSource(bundled_core_root()))
"""

from runtime.core_loader.core_loader import CoreLoader
from runtime.core_loader.errors import (
    CoreDirectoryNotFoundError,
    CoreLoaderError,
    CoreReadError,
    MalformedCoreDocumentError,
    MissingCoreFileError,
    PlaybookContentLeakError,
)
from runtime.core_loader.manifest import (
    REQUIRED_FILES,
    REQUIRED_GUARDRAILS,
    REQUIRED_PROMPTS,
    REQUIRED_TOOL_CONTRACTS,
    REQUIRED_WORKFLOWS,
)
from runtime.core_loader.sources import (
    CoreSource,
    FilesystemCoreSource,
    bundled_core_root,
)

__all__ = [
    "REQUIRED_FILES",
    "REQUIRED_GUARDRAILS",
    "REQUIRED_PROMPTS",
    "REQUIRED_TOOL_CONTRACTS",
    "REQUIRED_WORKFLOWS",
    "CoreDirectoryNotFoundError",
    "CoreLoader",
    "CoreLoaderError",
    "CoreReadError",
    "CoreSource",
    "FilesystemCoreSource",
    "MalformedCoreDocumentError",
    "MissingCoreFileError",
    "PlaybookContentLeakError",
    "bundled_core_root",
]
