"""Provider Interface — the provider-neutral boundary (specification §9).

Public surface:

    ProviderInterface        the contract every concrete adapter implements
    ProviderError + family   the normalised failure set (§9.9)
    run_conformance          the shared adapter conformance suite (§9.10)

There is deliberately **no concrete adapter and no provider SDK** in this
package. The framework is multi-provider by design: an adapter lives under
`adapters/<provider>/`, owns its SDK, and is the only place a vendor name
appears. Nothing here — and nothing in Modules 1-5 — knows which provider is
installed.
"""

from runtime.models.provider import (
    ProviderCapabilities,
    ProviderErrorType,
    ProviderMetadata,
    ProviderResponse,
)
from runtime.provider.binding import (
    IdentifiedTokenizer,
    ModelBinding,
    ModelBoundProvider,
    ModelIdentity,
    TokenCounter,
)
from runtime.provider.conformance import (
    ConformanceError,
    ConformanceReport,
    assert_conforms,
    run_conformance,
)
from runtime.provider.errors import (
    ContextWindowExceededError,
    ProviderAuthenticationError,
    ProviderBindingError,
    ProviderCapabilityUnavailableError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from runtime.provider.inspection import (
    PromptInspectable,
    RecordingSerializer,
    SerializedPrompt,
)
from runtime.provider.ports import ProviderInterface

__all__ = [
    "ConformanceError",
    "ConformanceReport",
    "ContextWindowExceededError",
    "IdentifiedTokenizer",
    "ModelBinding",
    "ModelBoundProvider",
    "ModelIdentity",
    "PromptInspectable",
    "ProviderAuthenticationError",
    "ProviderBindingError",
    "ProviderCapabilities",
    "ProviderCapabilityUnavailableError",
    "ProviderError",
    "ProviderErrorType",
    "ProviderInterface",
    "ProviderInvalidRequestError",
    "ProviderMetadata",
    "ProviderRateLimitError",
    "ProviderResponse",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "RecordingSerializer",
    "SerializedPrompt",
    "TokenCounter",
    "assert_conforms",
    "run_conformance",
]
