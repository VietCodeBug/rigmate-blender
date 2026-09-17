"""Data models for AI Quota tracking and Energy Level visualization."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from rigmate.core.i18n import t


class TokenUsage(BaseModel):
    """Token consumption for a single turn or session."""
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
    AI Quota snapshot data.
    Clearly distinguishes:
    - Token usage (turn/session)
    - Quota remaining
    - Plan expiration (separate from quota reset frequency)
    """
    provider_name: str = "Unknown"
    model_name: str = "Unknown"
    account_profile: str = "default"  # Profile identifier to avoid cross-user contamination

    # Data source: AUTOMATIC (machine-read), MANUAL (user input), DEMO (simulated), UNKNOWN
    source: str = "AUTOMATIC"

    # Remaining and total quota
    quota_remaining: Optional[float] = None
    quota_total: Optional[float] = None
    quota_unit: str = "requests"  # requests, credits, percentage, tokens

    # Timestamps
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reset_at: Optional[str] = None         # Periodic reset timestamp (e.g. daily/monthly)
    plan_expiration: Optional[str] = None  # Account subscription expiration timestamp

    # Stale data detection
    stale_threshold_hours: float = 24.0

    @property
    def is_stale(self) -> bool:
        """Check if snapshot is older than stale threshold."""
        try:
            dt = datetime.fromisoformat(self.last_updated.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - dt) > timedelta(hours=self.stale_threshold_hours)
        except Exception:
            return True

    @property
    def percentage(self) -> Optional[float]:
        """
        Calculate energy percentage:
        Only computed when remaining and total (>0) exist or unit is 'percentage'.
        Does not speculate without basis.
        """
        if self.quota_remaining is None:
            return None

        if self.quota_unit == "percentage":
            return max(0.0, min(100.0, float(self.quota_remaining)))

        if self.quota_total is not None and self.quota_total > 0:
            pct = (float(self.quota_remaining) / float(self.quota_total)) * 100.0
            return max(0.0, min(100.0, pct))

        return None

    def format_energy_label(self, locale: Optional[str] = None) -> str:
        """Format display label for UI energy bar with localization support."""
        source_tag = ""
        if self.source == "DEMO":
            source_tag = f" {t('quota.tag_demo', locale=locale)}"
        elif self.source == "MANUAL":
            source_tag = f" {t('quota.tag_manual', locale=locale)}"
        elif self.source == "UNKNOWN":
            return t("quota.auto_unavailable", locale=locale)
        elif self.source == "UNSUPPORTED":
            return t("quota.unsupported", locale=locale)

        pct = self.percentage
        stale_tag = f" {t('quota.tag_stale', locale=locale)}" if self.is_stale else ""

        if pct is not None:
            if self.quota_total is not None:
                return f"{pct:.1f}% ({self.quota_remaining:g}/{self.quota_total:g} {self.quota_unit}){source_tag}{stale_tag}"
            else:
                return f"{pct:.1f}%{source_tag}{stale_tag}"
        elif self.quota_remaining is not None:
            return f"{self.quota_remaining:g} {self.quota_unit}{source_tag}{stale_tag}"
        else:
            return f"{t('quota.unknown', locale=locale)}{source_tag}"


def is_quota_exhausted(snapshot: QuotaSnapshot) -> bool:
    """Return True if quota is definitively known and remaining balance is <= 0."""
    return snapshot.quota_remaining is not None and snapshot.quota_remaining <= 0.0


def is_quota_available(snapshot: QuotaSnapshot) -> bool:
    """Return True if quota has a valid positive balance."""
    return snapshot.quota_remaining is not None and snapshot.quota_remaining > 0.0


def is_quota_stale(snapshot: QuotaSnapshot) -> bool:
    """Return True if quota snapshot is stale according to threshold."""
    return snapshot.is_stale


def calculate_valid_percentage(remaining: Optional[float], total: Optional[float]) -> Optional[float]:
    """
    Pure calculation helper: compute percentage only when mathematically sound.
    Never fabricates a percentage without both remaining and total (>0).
    """
    if remaining is None or total is None or total <= 0:
        return None
    pct = (float(remaining) / float(total)) * 100.0
    return max(0.0, min(100.0, pct))

