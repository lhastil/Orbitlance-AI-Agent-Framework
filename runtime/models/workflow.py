"""WorkflowTransitionDecision — what the Workflow Router proposes.

The Workflow Router (§6) produces one of these each turn as a **candidate**;
the Workflow State Manager (§7) is what commits it. Router decides, Manager
persists — §7.3 is explicit that the Manager "never decides what the next state
should be (only persists/commits what Router hands it)".

Lives in `runtime/models/` because it crosses a module boundary: §6 outputs it
and §7 consumes it, so neither can own it without the other depending on a
module it must not depend on.

**Deliberately minimal.** The frozen specification names this type five times
but gives it no data-model row and no field list; the only stated constraint is
§6.10 — a decision "must always name a workflow that exists in `CoreBundle`".
Two fields are therefore defined and no more: a rationale field, a confidence
score, a timestamp and a "changed/unchanged" flag were all considered and left
out. Speculative fields on a type whose producer does not exist yet would be
guesses that later code would have to honour.

`collected_data` is here because without it `WorkflowState.collected_data` has
no writer at all: §7.6 exposes only `getState` and `commitTransition`, so data
that does not arrive on the decision can never be persisted, and §7.2's
"collected data-so-far" would be permanently empty.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class WorkflowTransitionDecision:
    """A proposed workflow transition, not yet committed.

    Immutable and copy-safe: `collected_data` is copied and wrapped at
    construction, so a caller that keeps and later mutates the mapping it passed
    cannot reach a decision that has already been handed to the State Manager.
    """

    target_workflow: str
    collected_data: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "collected_data", MappingProxyType(dict(self.collected_data))
        )
