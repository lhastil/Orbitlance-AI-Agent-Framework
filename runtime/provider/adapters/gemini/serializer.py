"""PromptBundle -> Gemini request. The only place Gemini's shape is known.

Three contracts govern this translation, and every one of them is about content
identity rather than formatting:

**P-1.** History comes from `prompt_bundle.conversation_history_window` and
nowhere else. This module is never given the raw `history` argument, so it
cannot serialize it even by mistake — the correct behaviour is structural, not
a rule someone has to remember.

**§9 (static content).** `PromptSection.sources` and `is_from_playbook` are
framework audit metadata, not prompt content, and never reach the payload. Each
section's text is carried as its own `Part`, in `ASSEMBLY_ORDER`, so the exact
strings the Token Budget Manager counted are the exact strings Gemini receives.
Nothing is joined, wrapped, prefixed or rephrased: a join would introduce
characters nothing counted, which is the defect Module 4 v1.7 existed to close.

**§10 (latest message).** `prompt_bundle.latest_message` is authoritative and
appears exactly once, as the final user turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from runtime.models.conversation import TurnRole
from runtime.models.prompt_bundle import PromptBundle
from runtime.provider.inspection import SerializedPrompt

if TYPE_CHECKING:  # pragma: no cover - typing only
    from google.genai import types

#: Gemini's role vocabulary. Confined to this module by design: no module above
#: `ProviderInterface` may learn that "model" is what this vendor calls an agent.
_ROLE_USER = "user"
_ROLE_AGENT = "model"

_ROLES: dict[TurnRole, str] = {
    TurnRole.USER: _ROLE_USER,
    TurnRole.AGENT: _ROLE_AGENT,
}


@dataclass(frozen=True, slots=True)
class GeminiRequest:
    """A serialized request, plus the neutral record of what went into it.

    `system_instruction` and `contents` are Gemini SDK objects and never leave
    the adapter. `neutral` is the provider-agnostic `SerializedPrompt` the
    conformance suite reads — the same strings, described in framework terms.
    Keeping both on one object is what makes them provably the same content.
    """

    system_instruction: Any
    contents: list[Any]
    neutral: SerializedPrompt


class GeminiSerializer:
    """Translates a `PromptBundle` into Gemini's native request representation."""

    def __init__(self, sdk_types: Any = None) -> None:
        """`sdk_types` is the `google.genai.types` module, injectable for tests."""
        if sdk_types is None:
            from google.genai import types as sdk_types  # noqa: PLC0415
        self._types = sdk_types

    def serialize(self, prompt_bundle: PromptBundle) -> GeminiRequest:
        """Build the request. Reads only the bundle — never a raw history."""
        static_texts = tuple(
            section.content for section in prompt_bundle.static_sections
        )
        history_texts = tuple(
            turn.content for turn in prompt_bundle.conversation_history_window
        )
        latest = prompt_bundle.latest_message

        # Each section is its own Part: no separator is introduced, so what was
        # counted is exactly what ships.
        system_instruction = self._content(
            role=None, texts=static_texts) if static_texts else None

        contents: list[Any] = [
            self._content(role=_ROLES[turn.role], texts=(turn.content,))
            for turn in prompt_bundle.conversation_history_window
        ]
        # P-2/§10: the latest message is authoritative and appears exactly once.
        contents.append(self._content(role=_ROLE_USER, texts=(latest,)))

        return GeminiRequest(
            system_instruction=system_instruction,
            contents=contents,
            neutral=SerializedPrompt(
                static_texts=static_texts,
                history_texts=history_texts,
                latest_message=latest,
            ),
        )

    def _content(self, *, role: str | None, texts: tuple[str, ...]) -> types.Content:
        parts = [self._types.Part(text=text) for text in texts]
        if role is None:
            return self._types.Content(parts=parts)
        return self._types.Content(role=role, parts=parts)
