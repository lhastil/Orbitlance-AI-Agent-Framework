"""Stable validation issue codes.

Codes are part of the module's public contract: CI pipelines, dashboards and
suppression lists will reference them, so a code's meaning must never change
once published. Retire a code rather than repurposing it.

Prefixes group by concern:
    STRUCT  project/core structural layout
    KNOW    knowledge extension point
    CONF    config extension point
    BRAND   branding extension point
    INTEG   integrations extension point
    SEC     security (secrets, credential leakage)
    CORE    core bundle integrity
"""

from __future__ import annotations

from typing import Final

# --- Structure -------------------------------------------------------------
STRUCT_PROJECT_ROOT_MISSING: Final[str] = "STRUCT001"
STRUCT_PROJECT_ID_INVALID: Final[str] = "STRUCT002"
STRUCT_KNOWLEDGE_DIR_MISSING: Final[str] = "STRUCT003"
STRUCT_BRANDING_DIR_MISSING: Final[str] = "STRUCT004"
STRUCT_INTEGRATIONS_DIR_MISSING: Final[str] = "STRUCT005"
STRUCT_CONFIG_FILE_MISSING: Final[str] = "STRUCT006"

# --- Knowledge -------------------------------------------------------------
KNOW_DOCUMENT_MISSING: Final[str] = "KNOW001"
KNOW_DOCUMENT_EMPTY: Final[str] = "KNOW002"
KNOW_SECTION_MISSING: Final[str] = "KNOW003"
KNOW_SECTION_PLACEHOLDER: Final[str] = "KNOW004"
KNOW_TEMPLATE_UNAVAILABLE: Final[str] = "KNOW005"

# --- Config ----------------------------------------------------------------
CONF_SECTION_MISSING: Final[str] = "CONF001"
CONF_PLAYBOOK_UNKNOWN: Final[str] = "CONF002"
CONF_WORKFLOW_UNKNOWN: Final[str] = "CONF003"
CONF_PROVIDER_NOT_DECLARED: Final[str] = "CONF004"
CONF_PROVIDER_NOT_REGISTERED: Final[str] = "CONF005"
CONF_CONSTRAINT_RELAXES_CORE: Final[str] = "CONF006"
CONF_NO_WORKFLOWS_ENABLED: Final[str] = "CONF007"

# --- Branding --------------------------------------------------------------
BRAND_ABSENT: Final[str] = "BRAND001"
BRAND_EMPTY: Final[str] = "BRAND002"

# --- Integrations ----------------------------------------------------------
INTEG_ABSENT: Final[str] = "INTEG001"
INTEG_CONTRACT_UNCONFIGURED: Final[str] = "INTEG002"

# --- Security --------------------------------------------------------------
SEC_SECRET_DETECTED: Final[str] = "SEC001"

# --- Core ------------------------------------------------------------------
CORE_PROMPT_MISSING: Final[str] = "CORE001"
CORE_GUARDRAIL_MISSING: Final[str] = "CORE002"
CORE_WORKFLOW_MISSING: Final[str] = "CORE003"
CORE_TOOL_CONTRACT_MISSING: Final[str] = "CORE004"
CORE_PLAYBOOK_CONTENT_LEAKED: Final[str] = "CORE005"
CORE_CLIENT_SPECIFIC_CONTENT: Final[str] = "CORE006"

# --- Engine ----------------------------------------------------------------
# Raised when a rule itself raises. The spec forbids the validator crashing on
# malformed input, so an internal failure becomes a reported issue instead.
ENGINE_RULE_CRASHED: Final[str] = "ENGINE001"
