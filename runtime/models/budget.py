"""The Prompt Assembler ↔ Token Budget Manager seam.

These types live in `runtime/models/` rather than inside either module so that
neither has to import the other. The frozen dependency direction is Prompt
Assembler → Token Budget Manager; if the request/selection types lived in the
assembler, the budget manager would have to import back into it.

**Why the request carries rendered text.** An earlier design had the budget
manager estimate what the assembler would render. It could not: the assembler
inserts separators, strips documents, generates a workflow-index sentence, and
emits each Knowledge section's heading marker and original heading text — none
of which the budget manager can see. Estimating meant two components modelling
one artifact, so a formatting change would silently invalidate the budget while
the check still reported success.

Both halves of the prompt therefore cross this seam **already rendered**:

* `fixed_sections` — the assembled non-Knowledge slots.
* `knowledge_candidates` — every Knowledge section, rendered exactly as it will
  appear if selected.

The budget manager counts those literal strings. Any change to the assembler's
rendering changes the measured count automatically, and the budget manager holds
zero formatting knowledge.

`ProjectDocument` is deliberately **absent** from the request. Carrying it would
hand the budget manager `raw_text`, `sections` and `section_body`, i.e. a second
representation of the same Knowledge and a standing invitation to count the
wrong one. Candidates are opaque text plus identity, which makes the earlier
16.7% under-count structurally impossible rather than merely tested against.
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.models.conversation import ConversationContext, Turn
from runtime.models.prompt_bundle import PromptSection

#: One selected Knowledge section: `(document name, ordinal)`.
#:
#: Ordinal, never heading. Headings repeat legitimately — `02_services.md`
#: carries `Category` five times — so heading-based identity cannot address
#: them. This is also the unit a future retrieval layer will rank.
SectionRef = tuple[str, int]


@dataclass(frozen=True, slots=True)
class KnowledgeCandidate:
    """One Knowledge section offered to the budget, already rendered.

    `rendered_text` is the exact string the assembler will place in the
    Knowledge slot if this candidate is selected — not the section body, and not
    a reconstruction of it. The assembler renders once and reuses the same
    string, so what is counted and what ships cannot diverge.
    """

    document_name: str
    ordinal: int
    rendered_text: str

    @property
    def ref(self) -> SectionRef:
        return (self.document_name, self.ordinal)


@dataclass(frozen=True, slots=True)
class BudgetRequest:
    """Everything the budget manager needs, as facts rather than as logic.

    The context-window size and any serialization reserve are **not** here: the
    budget manager queries those through its own provider-capability port, which
    keeps the assembler free of provider knowledge.
    """

    project_id: str
    fixed_sections: tuple[PromptSection, ...]
    latest_message: str
    knowledge_candidates: tuple[KnowledgeCandidate, ...] = ()
    conversation: ConversationContext | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixed_sections", tuple(self.fixed_sections))
        object.__setattr__(
            self, "knowledge_candidates", tuple(self.knowledge_candidates)
        )

    @property
    def fixed_text(self) -> tuple[str, ...]:
        """The exact rendered strings to count. No formatting is implied here."""
        return tuple(section.content for section in self.fixed_sections)

    @property
    def knowledge_text(self) -> tuple[str, ...]:
        """The exact rendered Knowledge strings to count, in candidate order."""
        return tuple(candidate.rendered_text for candidate in self.knowledge_candidates)


@dataclass(frozen=True, slots=True)
class BudgetSelection:
    """What survives the budget, as identities the assembler resolves itself.

    Knowledge is returned as references, not content: the assembler owns
    rendering, so the budget manager never carries prompt text back.
    """

    knowledge_sections: tuple[SectionRef, ...] = ()
    history_window: tuple[Turn, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "knowledge_sections", tuple(self.knowledge_sections))
        object.__setattr__(self, "history_window", tuple(self.history_window))
