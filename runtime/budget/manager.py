"""Token Budget Manager — Runtime Module 5.

Implements module 5 of docs/runtime-specification.md:

    select(request) -> BudgetSelection

Decides which Knowledge and how much conversation history fit the target
provider's context window, given the fixed overhead the Prompt Assembler has
already rendered.

**This module counts; it never renders.** Every string it measures arrives
through `BudgetRequest` exactly as it will ship — the fixed slots, the composed
Knowledge slot, the latest message, the conversation turns. It holds no
knowledge of headings, heading levels, separators, Markdown, or how any of that
text was produced. If the assembler changes its formatting, the strings change
and the counts follow automatically; there is nothing here to keep in sync.

**Knowledge is counted as one composed string, never summed.** Adding
per-section counts would omit the assembler's joins and would be approximate
regardless, because token counting is not additive across a boundary. The
assembler supplies `knowledge_text` for exactly this reason.

**Phase 1 Knowledge policy is all-or-nothing.** Complete Knowledge or an
explicit failure — no ranking, no truncation, no subset. Choosing which business
facts to drop requires an authoritative retrieval mechanism, and inventing one
here would be a product decision disguised as a token-management one.

Ownership boundaries this module respects: the assembler renders and composes;
the provider adapter serializes and asserts the final payload; the Validation
Layer owns §5.9's configuration invariant. This module owns counting, budget
arithmetic, and selection.
"""

from __future__ import annotations

from runtime.budget.errors import (
    BudgetInvariantError,
    FixedOverheadExceedsWindowError,
    KnowledgeDoesNotFitError,
    ProviderCapabilityError,
    ReservedContentExceedsWindowError,
    TokenizerError,
)
from runtime.budget.ports import (
    ProviderCapabilities,
    ProviderCapabilityPort,
    TokenizerPort,
)
from runtime.models.budget import BudgetRequest, BudgetSelection
from runtime.models.conversation import ConversationContext, Turn, TurnRole


class TokenBudgetManager:
    """Counts the prompt and decides what fits.

    Both collaborators are mandatory. A default tokenizer would have to guess,
    and a default capability query would have to assume a window — either turns
    an unmeasured budget into one that reports success. Absence is a failure,
    not a degraded mode.
    """

    __slots__ = ("_tokenizer", "_capabilities")

    def __init__(
        self, *, tokenizer: TokenizerPort, capabilities: ProviderCapabilityPort
    ) -> None:
        self._tokenizer = tokenizer
        self._capabilities = capabilities

    # --- public interface ---------------------------------------------------
    def select(self, request: BudgetRequest) -> BudgetSelection:
        """Choose the Knowledge and history that fit.

        Failure order is fixed and meaningful: capability, tokenizer, fixed
        overhead, reserved content, Knowledge. History never fails — it is the
        one thing this module may reduce.
        """
        caps = self._provider_capabilities()

        fixed_tokens = sum(self._count(text) for text in request.fixed_text)
        latest_tokens = self._count(request.latest_message)
        knowledge_tokens = self._count(request.knowledge_text)

        if fixed_tokens > caps.context_window:
            raise FixedOverheadExceedsWindowError(
                f"Rendered fixed content is {fixed_tokens} tokens against a "
                f"{caps.context_window}-token window. Core alone cannot fit; "
                "this is an upstream configuration state, not a budget outcome."
            )

        reserved = caps.serialization_reserve + fixed_tokens + latest_tokens
        if reserved > caps.context_window:
            raise ReservedContentExceedsWindowError(
                f"Mandatory content is {reserved} tokens (reserve "
                f"{caps.serialization_reserve} + fixed {fixed_tokens} + latest "
                f"message {latest_tokens}) against a {caps.context_window}-token "
                "window. The latest message is never truncated to make it fit."
            )

        available = caps.context_window - reserved
        if knowledge_tokens > available:
            raise KnowledgeDoesNotFitError(
                f"Complete Knowledge is {knowledge_tokens} tokens against "
                f"{available} available. Phase 1 includes all Knowledge or none "
                "— selecting a subset needs an authoritative retrieval "
                "mechanism, which does not exist yet."
            )

        history = self._select_history(
            request.conversation, available - knowledge_tokens
        )

        selection = BudgetSelection(
            knowledge_sections=tuple(c.ref for c in request.knowledge_candidates),
            history_window=history,
        )
        self._assert_fits(caps, fixed_tokens, latest_tokens, knowledge_tokens, history)
        return selection

    # --- collaborators ------------------------------------------------------
    def _provider_capabilities(self) -> ProviderCapabilities:
        try:
            return self._capabilities.capabilities()
        except Exception as exc:  # noqa: BLE001 - normalised at the boundary
            raise ProviderCapabilityError(
                "The target provider's capabilities could not be established. "
                "No window size is assumed."
            ) from exc

    def _count(self, text: str) -> int:
        """Token cost of the literal text supplied. Never an estimate."""
        try:
            return self._tokenizer.count_tokens(text)
        except Exception as exc:  # noqa: BLE001 - normalised at the boundary
            raise TokenizerError(
                "A required token count could not be obtained. No approximation "
                "is substituted."
            ) from exc

    # --- history ------------------------------------------------------------
    def _select_history(
        self, conversation: ConversationContext | None, budget: int
    ) -> tuple[Turn, ...]:
        """Newest turns that fit, oldest dropped first, order preserved.

        The latest user turn is excluded **by position** — the last `USER` turn
        in the sequence — because the assembler carries it separately as
        `latest_message`. Identifying it by position rather than by content
        keeps repeated identical messages distinguishable, and holds even when
        the conversation ends on an agent turn.

        Turns are atomic: one is included whole or not at all. A turn that does
        not fit stops the walk rather than being partially rendered.
        """
        if conversation is None or budget <= 0:
            return ()

        eligible = _history_turns(conversation)
        kept: list[Turn] = []
        remaining = budget
        for turn in reversed(eligible):
            cost = self._count(turn.content)
            if cost > remaining:
                break
            kept.append(turn)
            remaining -= cost
        kept.reverse()
        return tuple(kept)

    # --- final arithmetic ---------------------------------------------------
    def _assert_fits(
        self,
        caps: ProviderCapabilities,
        fixed_tokens: int,
        latest_tokens: int,
        knowledge_tokens: int,
        history: tuple[Turn, ...],
    ) -> None:
        """Verify the selection against the window before returning it.

        Every term is a count of a literal string this module was given. If the
        sum exceeds the window, that is a defect in the arithmetic above, and it
        is raised rather than resolved by quietly dropping content.
        """
        history_tokens = sum(self._count(turn.content) for turn in history)
        total = (
            caps.serialization_reserve
            + fixed_tokens
            + latest_tokens
            + knowledge_tokens
            + history_tokens
        )
        if total > caps.context_window:
            raise BudgetInvariantError(
                f"Selected content totals {total} tokens against a "
                f"{caps.context_window}-token window. Refusing to trim to fit."
            )


def _history_turns(conversation: ConversationContext) -> tuple[Turn, ...]:
    """Conversation turns minus the latest user turn, identified by position.

    `ConversationContext.history` drops the trailing turn only when it is a user
    turn, so a conversation ending on an agent turn would keep the latest user
    message and duplicate it against `latest_message`. Locating the last `USER`
    index directly holds in every shape.
    """
    turns = conversation.turns
    for index in range(len(turns) - 1, -1, -1):
        if turns[index].role is TurnRole.USER:
            return turns[:index] + turns[index + 1 :]
    return turns
