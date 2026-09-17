"""Mô hình dữ liệu cho Thanh năng lượng và Hạn mức AI (AI Quota & Energy Level)."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token tiêu thụ của lượt chat hoặc phiên làm việc hiện tại."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def create(cls, prompt: int = 0, completion: int = 0) -> "TokenUsage":
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
        )


class QuotaSnapshot(BaseModel):
    """
    Thông tin hạn mức AI thực tế hoặc snapshot thủ công.
    Phân biệt rõ:
    - token tiêu thụ (turn/session)
    - quota còn lại
    - ngày hết hạn gói (plan_expiration) tách biệt với chu kỳ reset quota
    """
    provider_name: str = "Unknown"
    model_name: str = "Unknown"
    account_profile: str = "default"  # Hồ sơ tài khoản để tránh lẫn khi đổi user

    # Nguồn dữ liệu: AUTOMATIC (đọc máy), MANUAL (nhập tay), DEMO (mô phỏng)
    source: str = "AUTOMATIC"  # AUTOMATIC, MANUAL, DEMO, UNKNOWN

    # Hạn mức còn lại và đơn vị
    quota_remaining: Optional[float] = None
    quota_total: Optional[float] = None
    quota_unit: str = "requests"  # requests, credits, percentage, tokens

    # Thời điểm
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reset_at: Optional[str] = None         # Thời điểm reset hạn mức hàng ngày/tháng
    plan_expiration: Optional[str] = None  # Thời điểm hết hạn gói tài khoản (trường riêng biệt)

    # Đánh dấu dữ liệu cũ (stale)
    stale_threshold_hours: float = 24.0

    @property
    def is_stale(self) -> bool:
        """Kiểm tra xem snapshot đã cũ so với thời gian hiện tại chưa."""
        try:
            dt = datetime.fromisoformat(self.last_updated.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - dt) > timedelta(hours=self.stale_threshold_hours)
        except Exception:
            return True

    @property
    def percentage(self) -> Optional[float]:
        """
        Tính phần trăm thanh năng lượng:
        Chỉ tính khi có đủ remaining và total (> 0) hoặc quota_unit là 'percentage'.
        Không tự đoán mò khi thiếu dữ liệu.
        """
        if self.quota_remaining is None:
            return None

        if self.quota_unit == "percentage":
            return max(0.0, min(100.0, float(self.quota_remaining)))

        if self.quota_total is not None and self.quota_total > 0:
            pct = (float(self.quota_remaining) / float(self.quota_total)) * 100.0
            return max(0.0, min(100.0, pct))

        return None

    def format_energy_label(self) -> str:
        """Tạo nhãn hiển thị trực quan cho thanh năng lượng UI."""
        source_tag = ""
        if self.source == "DEMO":
            source_tag = " [DEMO]"
        elif self.source == "MANUAL":
            source_tag = " [Nhập thủ công]"
        elif self.source == "UNKNOWN":
            return "Chưa đọc được hạn mức tự động"

        pct = self.percentage
        stale_tag = " (Dữ liệu cũ)" if self.is_stale else ""

        if pct is not None:
            if self.quota_total is not None:
                return f"{pct:.1f}% ({self.quota_remaining:g}/{self.quota_total:g} {self.quota_unit}){source_tag}{stale_tag}"
            else:
                return f"{pct:.1f}%{source_tag}{stale_tag}"
        elif self.quota_remaining is not None:
            return f"{self.quota_remaining:g} {self.quota_unit}{source_tag}{stale_tag}"
        else:
            return f"Không rõ hạn mức{source_tag}"
