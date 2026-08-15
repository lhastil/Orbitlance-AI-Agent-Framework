"""The Prompt Assembler ↔ Token Budget Manager seam.

These types live in `runtime/models/` rather than inside either module so that
neither has to import the other. The frozen dependency direction is Prompt
Assembler → Token Budget Manager; if the request/selection types lived in the
assembler, the budget manager would have to import back into it.

**Why the request carries rendered text.** An earlier design had the budget
manager estimate what the assembler would render. It could not: the assembler
inserts separators, strips documents, and generates a workflow-index sentence,
none of which the budget manager can see. Estimating meant two components
modelling one artifact, so a separator change six months later would silently
invalidate the budget while the assertion still reported success.

`BudgetRequest.fixed_sections` therefore carries the **actual rendered
sections**. The budget manager counts exactly what will be sent, and any change
to the assembler's rendering changes the measured count automatically. The
budget manager holds zero knowledge of formatting.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from runtime.models.conversation import ConversationContext, Turn
from runtime.models.project_context import ProjectDocument
from runtime.models.prompt_bundle import PromptSection

#: One selected Knowledge section: `(document name, ordinal)`.
#:
#: Ordinal, never heading. Headings repeat legitimately — `02_services.md`
#: carries `Category` five times — so heading-based identity cannot address
#: them. This is also the unit a future retrieval layer will rank.
SectionRef = tuple[str, int]


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
    knowledge: Mapping[str, ProjectDocument] = field(default_factory=dict)
    conversation: ConversationContext | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixed_sections", tuple(self.fixed_sections))
        object.__setattr__(self, "knowledge", MappingProxyType(dict(self.knowledge)))

    @property
    def fixed_text(self) -> tuple[str, ...]:
        """The exact rendered strings to count. No formatting is implied here."""
        return tuple(section.content for section in self.fixed_sections)


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
