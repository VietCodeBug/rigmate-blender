"""Giao diện chung (Interface) cho các AI Providers và Quota Providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field
from rigmate.core.quota import QuotaSnapshot, TokenUsage


class ChatMessage(BaseModel):
    """Một tin nhắn trong chuỗi hội thoại."""
    role: str  # user, assistant, system
    content: str
    context_data: Optional[Dict[str, Any]] = None  # Dữ liệu đối tượng gửi kèm theo


class ProviderResponse(BaseModel):
    """Phản hồi tổng hợp từ Provider."""
    text: str
    token_usage: Optional[TokenUsage] = None
    suggested_actions: List[str] = Field(default_factory=list)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAIProvider(ABC):
    """Interface cơ sở cho các nhà cung cấp AI."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Định danh provider (vd: mock, antigravity_cli)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Tên mô hình đang dùng."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
        timeout_seconds: float = 30.0,
    ) -> ProviderResponse:
        """Sinh câu trả lời từ AI."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """Stream từng token về giao diện người dùng."""
        pass


class BaseQuotaProvider(ABC):
    """Interface cơ sở để đọc hạn mức (Quota). Thiết kế mở rộng thêm provider sau này."""

    @abstractmethod
    async def fetch_quota_snapshot(self, account_profile: str = "default") -> QuotaSnapshot:
        """Đọc snapshot hạn mức hiện tại."""
        pass
