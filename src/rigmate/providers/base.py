"""Common interfaces and base abstractions for AI and Quota Providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field
from rigmate.core.quota import QuotaSnapshot, TokenUsage


class ChatMessage(BaseModel):
    """A single turn chat message."""
    role: str  # user, assistant, system
    content: str
    context_data: Optional[Dict[str, Any]] = None  # Optional compact context payload


class ProviderResponse(BaseModel):
    """Standardized response from AI Provider."""
    text: str
    token_usage: Optional[TokenUsage] = None
    suggested_actions: List[str] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAIProvider(ABC):
    """Base interface for AI inference providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider identifier (e.g. mock, antigravity)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model identifier."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
        timeout_seconds: float = 30.0,
    ) -> ProviderResponse:
        """Generate response from AI provider."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens as they arrive."""
        pass


class BaseQuotaProvider(ABC):
    """Base interface for querying account/model quota metrics."""

    @abstractmethod
    async def fetch_quota_snapshot(self, account_profile: str = "default") -> QuotaSnapshot:
        """Fetch current quota snapshot."""
        pass
