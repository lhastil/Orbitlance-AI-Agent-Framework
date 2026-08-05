"""Rule modules, grouped by the concern each validates.

`default_project_rules()` / `default_core_rules()` are the single place the
standard rule set is assembled. Registration is explicit — a rule that stops
running because someone forgot an import is a silent hole in a fail-closed
validator, so nothing here relies on import side effects.
"""

from __future__ import annotations

from runtime.validation.rule import CoreRule, ProjectRule
from runtime.validation.rules.config import CONFIG_RULES
from runtime.validation.rules.core import CORE_RULES
from runtime.validation.rules.extension_points import EXTENSION_POINT_RULES
from runtime.validation.rules.knowledge import KNOWLEDGE_RULES
from runtime.validation.rules.security import SECURITY_RULES
from runtime.validation.rules.structure import STRUCTURE_RULES


def default_project_rules() -> tuple[ProjectRule, ...]:
    """Every rule that validates a ProjectContext, in reporting order."""
    return (
        *STRUCTURE_RULES,
        *KNOWLEDGE_RULES,
        *CONFIG_RULES,
        *EXTENSION_POINT_RULES,
        *SECURITY_RULES,
    )


def default_core_rules() -> tuple[CoreRule, ...]:
    """Every rule that validates a CoreBundle."""
    return CORE_RULES


__all__ = [
    "default_project_rules",
    "default_core_rules",
    "STRUCTURE_RULES",
    "KNOWLEDGE_RULES",
    "CONFIG_RULES",
    "EXTENSION_POINT_RULES",
    "SECURITY_RULES",
    "CORE_RULES",
]
