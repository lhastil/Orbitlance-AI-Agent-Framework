"""Gemini adapter — the first concrete provider implementation.

`google` / `gemini-3.6-flash`. This subtree is the **only** place in the
repository where a vendor name, a provider SDK import, or a provider's role
vocabulary may appear. Nothing above `ProviderInterface` imports it, and the
framework selects no default provider: the existence of this adapter activates
Gemini for exactly nothing.

The SDK is an optional extra (`pip install .[gemini]`). Importing this package
requires it; importing anything else in the framework does not.
"""

from runtime.provider.adapters.gemini.adapter import (
    GEMINI_IDENTITY,
    MODEL_ID,
    PROVIDER_ID,
    GeminiAdapter,
)
from runtime.provider.adapters.gemini.count_request import (
    build_count_body,
    count_request_tokens,
)
from runtime.provider.adapters.gemini.serializer import GeminiSerializer
from runtime.provider.adapters.gemini.tokenizer import GeminiTokenizer

__all__ = [
    "GEMINI_IDENTITY",
    "MODEL_ID",
    "PROVIDER_ID",
    "GeminiAdapter",
    "GeminiSerializer",
    "GeminiTokenizer",
    "build_count_body",
    "count_request_tokens",
]
