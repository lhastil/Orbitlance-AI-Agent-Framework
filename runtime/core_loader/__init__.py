"""Core Loader — specification §1.

Reads `core/` into an immutable `CoreBundle` and caches it for the process
lifetime. The root of the module graph: nothing runs before it, and every
consumer of `CoreBundle` finally has a producer.

    from runtime.core_loader import CoreLoader, FilesystemCoreSource

    loader = CoreLoader(FilesystemCoreSource("core"))
    core = loader.get_core_bundle()   # cached for the process lifetime
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
from runtime.core_loader.sources import CoreSource, FilesystemCoreSource

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
]
