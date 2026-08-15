"""Token Budget Manager tests.

Covers the arithmetic, the Phase-1 Knowledge policy, the H-1…H-8 history rules,
the failure order, and the boundaries this module claims: it counts literal
strings, renders nothing, and knows nothing about how the text it measures was
produced.

The tokenizer double counts whitespace-separated words, which makes every
expected number in these tests readable by eye.
"""

from __future__ import annotations

import pathlib

import pytest

from runtime.budget import (
    BudgetInvariantError,
    FixedOverheadExceedsWindowError,
    KnowledgeDoesNotFitError,
    ProviderCapabilities,
    ProviderCapabilityError,
    ReservedContentExceedsWindowError,
    TokenBudgetManager,
    TokenizerError,
)
from runtime.models.budget import BudgetRequest, KnowledgeCandidate
from runtime.models.conversation import ConversationContext, Turn, TurnRole
from runtime.models.prompt_bundle import PromptSection, PromptSlot


class WordTokenizer:
    """Deterministic stand-in: one token per whitespace-separated word."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def count_tokens(self, text: str) -> int:
        self.seen.append(text)
        return len(text.split())


class FailingTokenizer:
    def count_tokens(self, text: str) -> int:  # noqa: ARG002
        raise RuntimeError("tokenizer unavailable")


class Capabilities:
    def __init__(self, window: int, reserve: int = 0) -> None:
        self._caps = ProviderCapabilities(window, reserve)

    def capabilities(self) -> ProviderCapabilities:
        return self._caps


class FailingCapabilities:
    def capabilities(self) -> ProviderCapabilities:
        raise RuntimeError("no provider configured")


def manager(window: int = 1000, reserve: int = 0, tokenizer=None, capabilities=None):
    return TokenBudgetManager(
        tokenizer=tokenizer or WordTokenizer(),
        capabilities=capabilities or Capabilities(window, reserve),
    )


def section(slot: PromptSlot, content: str) -> PromptSection:
    return PromptSection(slot=slot, sources=("core/x.md",), content=content)


def words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def request(
    *,
    fixed: int = 0,
    latest: int = 0,
    knowledge: int = 0,
    candidates: tuple[KnowledgeCandidate, ...] | None = None,
    turns: tuple[Turn, ...] = (),
) -> BudgetRequest:
    if candidates is None:
        candidates = (
            (KnowledgeCandidate("d.md", 0, words(knowledge)),) if knowledge else ()
        )
    return BudgetRequest(
        project_id="p",
        fixed_sections=(
            (section(PromptSlot.MISSION, words(fixed)),) if fixed else ()
        ),
        latest_message=words(latest),
        knowledge_candidates=candidates,
        knowledge_text=words(knowledge),
        conversation=ConversationContext("c", "p", turns=turns),
    )


def user(text: str) -> Turn:
    return Turn(TurnRole.USER, text)


def agent(text: str) -> Turn:
    return Turn(TurnRole.AGENT, text)


# --- capability ---------------------------------------------------------------
def test_valid_capabilities_are_used() -> None:
    result = manager(window=100).select(request(fixed=10, knowledge=10))
    assert result.knowledge_sections == (("d.md", 0),)


def test_capability_failure_is_first_and_hard() -> None:
    with pytest.raises(ProviderCapabilityError):
        manager(capabilities=FailingCapabilities()).select(request())


def test_capability_failure_precedes_tokenizer_failure() -> None:
    """Failure order 1 before 2: no window means nothing downstream matters."""
    with pytest.raises(ProviderCapabilityError):
        TokenBudgetManager(
            tokenizer=FailingTokenizer(), capabilities=FailingCapabilities()
        ).select(request(fixed=5))


def test_different_windows_change_what_fits() -> None:
    req = request(fixed=10, knowledge=50, turns=(user("a b c"), agent("d e"), user("q")))
    small = manager(window=65).select(req)
    large = manager(window=1000).select(req)
    assert len(large.history_window) >= len(small.history_window)


def test_serialization_reserve_consumes_capacity() -> None:
    req = request(fixed=10, knowledge=10)
    manager(window=30, reserve=10).select(req)
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=30, reserve=15).select(req)


def test_reserve_consuming_all_remaining_capacity() -> None:
    with pytest.raises(ReservedContentExceedsWindowError):
        manager(window=20, reserve=20).select(request(fixed=1))


def test_capabilities_reject_nonsense_values() -> None:
    with pytest.raises(ValueError):
        ProviderCapabilities(0, 0)
    with pytest.raises(ValueError):
        ProviderCapabilities(100, -1)


# --- tokenizer ----------------------------------------------------------------
def test_tokenizer_failure_is_hard_with_no_fallback() -> None:
    with pytest.raises(TokenizerError):
        manager(tokenizer=FailingTokenizer()).select(request(fixed=5))


def test_every_counted_string_is_one_supplied_by_the_request() -> None:
    tok = WordTokenizer()
    req = request(fixed=4, latest=2, knowledge=6, turns=(user("a b"), user("q")))
    manager(window=1000, tokenizer=tok).select(req)

    supplied = {*req.fixed_text, req.latest_message, req.knowledge_text}
    supplied |= {t.content for t in req.conversation.turns}
    assert set(tok.seen) <= supplied, "no string was invented or reconstructed"


def test_counts_are_deterministic() -> None:
    req = request(fixed=3, latest=1, knowledge=5, turns=(user("a b"), user("q")))
    assert manager().select(req) == manager().select(req)


# --- fixed content -------------------------------------------------------------
def test_fixed_content_consumes_budget() -> None:
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=20).select(request(fixed=15, knowledge=10))


def test_fixed_overhead_exceeding_window_is_its_own_failure() -> None:
    with pytest.raises(FixedOverheadExceedsWindowError):
        manager(window=10).select(request(fixed=11))


def test_fixed_overhead_failure_precedes_reserved_failure() -> None:
    """Failure order 3 before 4: Core alone failing is an upstream state."""
    with pytest.raises(FixedOverheadExceedsWindowError):
        manager(window=10, reserve=5).select(request(fixed=20, latest=20))


def test_fixed_content_fitting_exactly_leaves_nothing() -> None:
    result = manager(window=10).select(request(fixed=10))
    assert result.knowledge_sections == ()
    assert result.history_window == ()


def test_changing_fixed_text_changes_the_budget() -> None:
    assert manager(window=30).select(request(fixed=5, knowledge=20))
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=30).select(request(fixed=15, knowledge=20))


# --- latest message ------------------------------------------------------------
def test_latest_message_is_counted_exactly() -> None:
    manager(window=20).select(request(latest=20))
    with pytest.raises(ReservedContentExceedsWindowError):
        manager(window=20).select(request(latest=21))


def test_latest_message_alone_exceeding_capacity_fails() -> None:
    with pytest.raises(ReservedContentExceedsWindowError):
        manager(window=50).select(request(fixed=10, latest=45))


def test_latest_message_is_never_truncated() -> None:
    """It is reserved: the failure happens instead of a shortened message."""
    req = request(fixed=10, latest=45)
    with pytest.raises(ReservedContentExceedsWindowError):
        manager(window=50).select(req)
    assert req.latest_message == words(45), "the request is not mutated"


# --- Knowledge -----------------------------------------------------------------
def test_all_knowledge_is_selected_when_it_fits() -> None:
    cands = (
        KnowledgeCandidate("a.md", 0, words(3)),
        KnowledgeCandidate("a.md", 1, words(3)),
        KnowledgeCandidate("b.md", 0, words(3)),
    )
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text=words(11),
        conversation=ConversationContext("c", "p"),
    )
    result = manager(window=100).select(req)
    assert result.knowledge_sections == (("a.md", 0), ("a.md", 1), ("b.md", 0))


def test_knowledge_fitting_exactly_is_accepted() -> None:
    result = manager(window=20).select(request(fixed=5, knowledge=15))
    assert result.knowledge_sections == (("d.md", 0),)


def test_knowledge_exceeding_by_one_token_fails_closed() -> None:
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=20).select(request(fixed=5, knowledge=16))


def test_no_partial_knowledge_selection_ever() -> None:
    cands = tuple(KnowledgeCandidate("d.md", i, words(10)) for i in range(5))
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text=words(54),
        conversation=ConversationContext("c", "p"),
    )
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=20).select(req)


def test_empty_knowledge_is_valid() -> None:
    result = manager(window=100).select(request(fixed=5))
    assert result.knowledge_sections == ()


def test_duplicate_headings_keep_distinct_identities() -> None:
    cands = (
        KnowledgeCandidate("02_services.md", 2, "## Category\n\nPreventive"),
        KnowledgeCandidate("02_services.md", 13, "## Category\n\nCosmetic"),
        KnowledgeCandidate("02_services.md", 24, "## CATEGORY\n\nUrgent"),
    )
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text="x " * 5,
        conversation=ConversationContext("c", "p"),
    )
    refs = manager(window=1000).select(req).knowledge_sections
    assert refs == (("02_services.md", 2), ("02_services.md", 13), ("02_services.md", 24))
    assert len(set(refs)) == 3, "duplicates must not collapse"


def test_knowledge_identity_order_is_preserved() -> None:
    cands = tuple(KnowledgeCandidate("d.md", i, "x") for i in (7, 2, 9))
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text="x x x",
        conversation=ConversationContext("c", "p"),
    )
    assert manager(window=100).select(req).knowledge_sections == (
        ("d.md", 7),
        ("d.md", 2),
        ("d.md", 9),
    )


# --- the non-additivity regression --------------------------------------------
def test_knowledge_is_counted_from_the_composed_string_not_the_candidates() -> None:
    """The v1.7 reason for `knowledge_text`, asserted directly.

    The composed slot costs more than its parts because of the joins. Counting
    candidates individually would under-count and let an oversized prompt pass.
    """
    tok = WordTokenizer()
    cands = (
        KnowledgeCandidate("d.md", 0, "a b"),
        KnowledgeCandidate("d.md", 1, "c d"),
    )
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text="a b JOIN c d",
        conversation=ConversationContext("c", "p"),
    )
    manager(window=1000, tokenizer=tok).select(req)

    assert "a b JOIN c d" in tok.seen, "the composed string must be what is counted"
    assert "a b" not in tok.seen and "c d" not in tok.seen, (
        "candidates must not be counted individually"
    )


def test_composed_knowledge_drives_the_fit_decision() -> None:
    """Summing candidates (4 tokens) would fit; the composed slot (5) does not."""
    cands = (KnowledgeCandidate("d.md", 0, "a b"), KnowledgeCandidate("d.md", 1, "c d"))
    req = BudgetRequest(
        project_id="p",
        fixed_sections=(),
        latest_message="",
        knowledge_candidates=cands,
        knowledge_text="a b JOIN c d",
        conversation=ConversationContext("c", "p"),
    )
    with pytest.raises(KnowledgeDoesNotFitError):
        manager(window=4).select(req)


# --- history -------------------------------------------------------------------
def test_full_history_fits() -> None:
    turns = (user("a b"), agent("c d"), user("q"))
    result = manager(window=100).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["a b", "c d"]


def test_history_truncates_oldest_first() -> None:
    turns = (user("old old old"), agent("mid mid"), agent("new"), user("q"))
    result = manager(window=3).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["mid mid", "new"]


def test_turns_are_atomic() -> None:
    turns = (agent("one two three"), agent("four"), user("q"))
    result = manager(window=2).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["four"]


def test_chronological_order_is_preserved() -> None:
    turns = (agent("a"), agent("b"), agent("c"), user("q"))
    result = manager(window=3).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["a", "b", "c"]


def test_latest_user_turn_is_excluded_by_position() -> None:
    turns = (user("same"), agent("reply"), user("same"))
    result = manager(window=100).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["same", "reply"]
    assert len(result.history_window) == 2, "only the trailing occurrence is removed"


def test_trailing_agent_turn_still_excludes_the_latest_user_turn() -> None:
    """`ConversationContext.history` would keep it; H-1 says exclude by position."""
    turns = (agent("first"), user("latest"), agent("trailing"))
    result = manager(window=100).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["first", "trailing"]


def test_conversation_with_no_user_turn() -> None:
    turns = (agent("a"), agent("b"))
    result = manager(window=100).select(request(turns=turns))
    assert [t.content for t in result.history_window] == ["a", "b"]


def test_single_user_turn_yields_empty_history() -> None:
    result = manager(window=100).select(request(turns=(user("q"),)))
    assert result.history_window == ()


def test_empty_history_is_valid() -> None:
    assert manager(window=100).select(request()).history_window == ()


def test_history_may_receive_zero_budget() -> None:
    turns = (agent("a b c"), user("q"))
    result = manager(window=10).select(request(fixed=5, knowledge=5, turns=turns))
    assert result.history_window == ()


def test_knowledge_priority_starves_history_before_dropping_knowledge() -> None:
    turns = (agent("h h h h h"), user("q"))
    result = manager(window=20).select(request(knowledge=20, turns=turns))
    assert result.knowledge_sections == (("d.md", 0),)
    assert result.history_window == ()


# --- final invariant -----------------------------------------------------------
def test_selection_never_exceeds_the_window() -> None:
    turns = (agent("a b"), agent("c d"), user("q"))
    tok = WordTokenizer()
    result = manager(window=40, reserve=5, tokenizer=tok).select(
        request(fixed=10, latest=3, knowledge=8, turns=turns)
    )
    total = 5 + 10 + 3 + 8 + sum(len(t.content.split()) for t in result.history_window)
    assert total <= 40


def test_invariant_breach_raises_rather_than_trimming() -> None:
    class Drifting:
        """Reports low during selection, high during the final assertion."""

        def __init__(self) -> None:
            self.calls = 0

        def count_tokens(self, text: str) -> int:  # noqa: ARG002
            self.calls += 1
            return 1 if self.calls <= 4 else 10_000

    with pytest.raises(BudgetInvariantError):
        manager(window=100, tokenizer=Drifting()).select(
            request(fixed=1, knowledge=1, turns=(agent("a"), user("q")))
        )


# --- architecture --------------------------------------------------------------
MODULE = pathlib.Path(__file__).resolve().parents[2] / "runtime" / "budget"


def test_module_five_never_imports_module_four() -> None:
    for path in MODULE.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        assert "runtime.assembler" not in src, f"{path.name} imports Module 4"


def test_module_five_contains_no_rendering_or_markdown_knowledge() -> None:
    for path in MODULE.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for banned in (
            "_SEPARATOR",
            "_compose_knowledge",
            "_render_section",
            "split_sections",
            "normalise_heading",
            "heading_level",
            "section_body",
            "raw_text",
            "ProjectDocument",
        ):
            assert banned not in src, f"{path.name} references {banned}"


def test_module_five_has_no_provider_sdk_or_hard_coded_window() -> None:
    for path in MODULE.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for banned in ("openai", "anthropic", "tiktoken", "gemini", "128000", "8192"):
            assert banned.lower() not in src.lower(), f"{path.name} references {banned}"


def test_module_five_uses_no_character_length_estimation() -> None:
    src = (MODULE / "manager.py").read_text(encoding="utf-8")
    assert "len(text)" not in src
    assert "// 4" not in src and "/ 4" not in src, "no characters-per-token ratio"


def test_module_five_holds_no_module_level_mutable_state() -> None:
    import runtime.budget.manager as m

    mutable = [
        name
        for name, value in vars(m).items()
        if not name.startswith("__") and isinstance(value, (list, dict, set))
    ]
    assert mutable == [], f"module-level mutable state: {mutable}"


def test_manager_satisfies_the_assembler_port_structurally() -> None:
    from runtime.assembler.ports import TokenBudgetPort

    assert isinstance(manager(), TokenBudgetPort)


def test_repeated_invocation_does_not_accumulate_state() -> None:
    mgr = manager(window=100)
    req = request(fixed=3, knowledge=5, turns=(agent("a b"), user("q")))
    assert mgr.select(req) == mgr.select(req) == mgr.select(req)


def test_inputs_are_not_mutated() -> None:
    turns = (agent("a b"), user("q"))
    req = request(fixed=3, latest=1, knowledge=5, turns=turns)
    before = (req.fixed_text, req.latest_message, req.knowledge_text, req.conversation.turns)
    manager(window=100).select(req)
    assert (
        req.fixed_text,
        req.latest_message,
        req.knowledge_text,
        req.conversation.turns,
    ) == before
