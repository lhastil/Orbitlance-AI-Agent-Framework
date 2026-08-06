"""Which `config.md` headings the Loader recognises, and what to call them.

This is *recognition* vocabulary -- how a heading in a document maps to a
canonical name. It is not a policy about which sections a project must have;
that is the Validation Layer's knowledge and stays there. The two are different
facts about the same framework, so keeping them in different modules is a split
of concerns, not a duplication of one.

Resolution is an exact lookup on the normalised heading. There is deliberately
no prefix, substring or fuzzy matching: an earlier revision of the Validation
Layer matched prefixes in both directions and a heading of "Knowledge" silently
satisfied "Knowledge Status", binding the wrong body to five downstream checks.

Every alias below is a spelling that actually occurs in the frozen framework --
`core/templates/config.md` writes the plural playbook form, the projects write
the singular. Adding one is a deliberate edit, never a heuristic side effect.
"""

from __future__ import annotations

from typing import Final

# Canonical section names produced by the Loader.
ACTIVE_INDUSTRY_PLAYBOOK: Final[str] = "Active Industry Playbook"
KNOWLEDGE_STATUS: Final[str] = "Knowledge Status"
BRANDING_STATUS: Final[str] = "Branding Status"
INTEGRATIONS_STATUS: Final[str] = "Integrations Status"
LLM_PROVIDER: Final[str] = "LLM Provider"
ENABLED_WORKFLOWS: Final[str] = "Enabled Workflows"
OPERATING_CONSTRAINTS: Final[str] = "Operating Constraints"

#: Normalised heading -> canonical section name.
SECTION_ALIASES: Final[dict[str, str]] = {
    "active industry playbook": ACTIVE_INDUSTRY_PLAYBOOK,
    "active industry playbook(s)": ACTIVE_INDUSTRY_PLAYBOOK,
    "knowledge status": KNOWLEDGE_STATUS,
    "branding status": BRANDING_STATUS,
    "integrations status": INTEGRATIONS_STATUS,
    "llm provider": LLM_PROVIDER,
    "enabled workflows": ENABLED_WORKFLOWS,
    "operating constraints": OPERATING_CONSTRAINTS,
}

# Labels inside the LLM Provider section.
PRIMARY_LABEL: Final[str] = "primary"
MODEL_LABEL: Final[str] = "model"
SECONDARY_LABEL: Final[str] = "secondary"


def canonical_section(normalised_heading: str) -> str | None:
    """Canonical name for a recognised heading, or None if unrecognised.

    An unrecognised heading is dropped rather than passed through: it carries
    no contract, and admitting it would let an arbitrary heading masquerade as
    configuration.
    """
    return SECTION_ALIASES.get(normalised_heading)
