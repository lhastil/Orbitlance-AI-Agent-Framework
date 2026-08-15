"""Token Budget Manager failure modes.

Every one is explicit and terminal. There is no degraded path: the module either
returns a selection whose arithmetic it has verified, or it refuses. Silently
trimming content to make a budget balance is the failure this module exists to
prevent.

The order these can occur in is fixed and meaningful — capability, tokenizer,
overhead, reserved, Knowledge — so a caller can tell an upstream configuration
problem from a genuine capacity limit rather than seeing one generic error.
"""

from __future__ import annotations


class BudgetError(Exception):
    """Base for every Token Budget Manager failure."""


class ProviderCapabilityError(BudgetError):
    """The target provider's capacity could not be established.

    First in the failure order: without a window size nothing downstream means
    anything. No default window is assumed — guessing one would produce a budget
    that looks authoritative and is not.
    """


class TokenizerError(BudgetError):
    """A required token count could not be obtained.

    Hard by design. An approximation here would silently turn an exact budget
    into an estimate, which is the defect the render-and-count seam was built to
    remove.
    """


class FixedOverheadExceedsWindowError(BudgetError):
    """Core's fixed rendered content alone exceeds the context window.

    An invalid upstream state, not a capacity decision this module owns.
    Specification §5.9 assigns the invariant to the Validation Layer and says it
    must never be discovered mid-request; this module refuses to mask it but
    does not become a second validation boundary.
    """


class ReservedContentExceedsWindowError(BudgetError):
    """Fixed content, the latest message and the serialization reserve do not fit.

    Distinct from the case above: Core alone is fine, but the mandatory content
    together exceeds capacity. `latest_message` is never truncated to resolve
    it.
    """


class KnowledgeDoesNotFitError(BudgetError):
    """The complete Knowledge set does not fit the available budget.

    Phase 1 is all-or-nothing. Selecting a subset would require deciding which
    business facts the agent may do without, and no authoritative retrieval
    mechanism exists to make that judgement. Failing closed is the framework's
    stated preference over answering from partial Knowledge.
    """


class BudgetInvariantError(BudgetError):
    """The final arithmetic check failed.

    A defect indicator rather than an expected outcome: the earlier checks
    should already have caught anything that does not fit. Raised instead of
    trimming, so a bug surfaces here rather than as a silently oversized prompt.
    """
