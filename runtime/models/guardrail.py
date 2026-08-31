"""GuardrailResult — the outcome of one guardrail checkpoint.

Implements the `GuardrailResult` data model from docs/runtime-specification.md
(blocked, reason, escalate, checkpoint, triggeredRule). Written solely by the
Guardrail Engine and consumed immediately by the Runtime Engine.

**A result, never an exception.** §8.9 requires the Engine to fail *closed* on
its own internal failure — *"a broken Guardrail Engine must never silently
become a no-op"* — which means an internal error becomes a blocked result the
Runtime Engine can act on, not a traceback it might catch and ignore.

**Origin is carried by `triggered_rule`, not a separate field.** §8.10 requires
every block to record "whether it was triggered by a Core guardrail or a project
Operating Constraint". The frozen field list has no origin column, so rule
identifiers are namespaced — `core.*` versus `project.*` — and `origin` reads
that prefix. Nothing was added to the frozen contract to satisfy §8.10.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Checkpoint(enum.StrEnum):
    """Which checkpoint produced a result.

    The two values the frozen data-model row names verbatim: `"pre-flight"` and
    `"post-response"`.
    """

    PRE_FLIGHT = "pre-flight"
    POST_RESPONSE = "post-response"


class GuardrailOrigin(enum.StrEnum):
    """What authority a block rests on (§8.10).

    `CORE` is a universal guardrail from `core/guardrails/`; `PROJECT` is a
    project's additive Operating Constraints. `ENGINE` covers the Engine's own
    internal failure, which is neither — §8.9 requires that to block too, and
    attributing it to a guardrail it did not come from would misreport why the
    conversation stopped.
    """

    CORE = "core"
    PROJECT = "project"
    ENGINE = "engine"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    """One checkpoint's verdict. Immutable; created fresh per check call.

    A passing result carries no reason and no rule: there is nothing to report.
    A blocking result must carry both — §8.10 requires "a specific reason (for
    observability and for constructing an honest, specific fallback rather than
    a generic one)", and a rule identifier is what makes the origin recoverable.
    """

    checkpoint: Checkpoint
    blocked: bool = False
    reason: str | None = None
    escalate: bool = False
    triggered_rule: str | None = None

    def __post_init__(self) -> None:
        if self.blocked and not self.reason:
            raise ValueError(
                "a blocking GuardrailResult must carry a specific reason "
                "(specification 8.10)"
            )
        if self.blocked and not self.triggered_rule:
            raise ValueError(
                "a blocking GuardrailResult must name the rule that triggered "
                "it, so its Core-or-project origin is recoverable (8.10)"
            )

    @property
    def origin(self) -> GuardrailOrigin:
        """Whether a Core guardrail, a project constraint or the Engine blocked.

        Read from the rule identifier's namespace rather than stored separately,
        so the two can never disagree.
        """
        if self.triggered_rule is None:
            return GuardrailOrigin.NONE
        namespace = self.triggered_rule.split(".", 1)[0]
        try:
            return GuardrailOrigin(namespace)
        except ValueError:
            return GuardrailOrigin.NONE

    @property
    def passed(self) -> bool:
        return not self.blocked
