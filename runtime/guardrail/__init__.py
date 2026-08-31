"""Guardrail Engine — specification §8.

Enforces the Core guardrails bundle and a project's Operating Constraints at the
pre-flight and post-response checkpoints. Pure, deterministic, and independent of
provider infrastructure.

    from runtime.guardrail import GuardrailEngine

    engine = GuardrailEngine(core_bundle)
    verdict = engine.check_pre_flight(message, resolved_context)
    if verdict.blocked:
        ...                                  # Runtime Engine decides what to do
    verdict = engine.check_post_response(response, resolved_context)

Read `engine`'s docstring before relying on this: it states exactly which
guardrails are enforced deterministically and which remain prose the model is
asked to follow but this Engine does not check.
"""

from runtime.guardrail.engine import (
    GUARDRAIL_FILES,
    PRICE_PATTERN,
    TRAILING_PUNCTUATION,
    UNENFORCED_CORE_CONDITIONS,
    UNENFORCED_PROJECT_CONSTRAINTS,
    GuardrailEngine,
)
from runtime.models.guardrail import Checkpoint, GuardrailOrigin, GuardrailResult

__all__ = [
    "GUARDRAIL_FILES",
    "PRICE_PATTERN",
    "TRAILING_PUNCTUATION",
    "UNENFORCED_CORE_CONDITIONS",
    "UNENFORCED_PROJECT_CONSTRAINTS",
    "Checkpoint",
    "GuardrailEngine",
    "GuardrailOrigin",
    "GuardrailResult",
]
