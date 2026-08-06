"""Optional caching for the Project Loader.

The frozen spec requires the Loader to "cache per project; invalidate on
detected change". Task 2's engineering rules forbid hidden state and global
caches. Both are satisfied by making caching an **injected collaborator** with
no default: a `ProjectLoader` built without one is pure, and a caller that
wants caching opts in visibly.

There is deliberately no module-level or class-level cache instance anywhere in
this package. A cache that appears by default is exactly the hidden, shared,
process-wide state the rules prohibit -- and at thousands of agents it is also
how one project's data reaches another.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from runtime.models.project_context import ProjectContext


@runtime_checkable
class ProjectCache(Protocol):
    """What the Loader requires of a cache.

    Implementations own their eviction and invalidation policy, including the
    spec's "invalidate on detected change" -- detecting change is a storage
    concern, and putting it here would make the Loader responsible for watching
    the filesystem.
    """

    def get(self, project_id: str) -> ProjectContext | None:
        """The cached context, or None on a miss."""
        ...

    def put(self, project_id: str, context: ProjectContext) -> None:
        ...

    def invalidate(self, project_id: str) -> None:
        """Drop one entry. Must not raise when the entry is absent."""
        ...


class InMemoryProjectCache:
    """A minimal, explicitly-constructed, per-instance cache.

    Safe to share only as far as the caller chooses to share the instance. It
    is never created implicitly, so a `ProjectLoader` can never acquire one by
    accident.

    Entries are `ProjectContext` objects, which are immutable -- so a cache hit
    cannot be mutated by one caller and observed by another.
    """

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: dict[str, ProjectContext] = {}

    def get(self, project_id: str) -> ProjectContext | None:
        return self._entries.get(project_id)

    def put(self, project_id: str, context: ProjectContext) -> None:
        self._entries[project_id] = context

    def invalidate(self, project_id: str) -> None:
        self._entries.pop(project_id, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
