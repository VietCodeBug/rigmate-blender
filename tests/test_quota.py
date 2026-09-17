"""Tests for Quota management, Energy bar, stale data detection, and token tracking."""

from datetime import datetime, timezone, timedelta
import pytest
from rigmate.core.quota import QuotaSnapshot, TokenUsage
from rigmate.core.i18n import set_locale


def test_quota_percentage_calculation():
    # 1. Both remaining and total available
    snap = QuotaSnapshot(
        source="DEMO",
        quota_remaining=60.0,
        quota_total=100.0,
        quota_unit="credits",
    )
    assert snap.percentage == 60.0
    assert "60.0% (60/100 credits) [DEMO]" in snap.format_energy_label()

    # 2. Percentage directly given
    snap_pct = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=85.5,
        quota_unit="percentage",
    )
    assert snap_pct.percentage == 85.5
    assert "85.5% [Manual Entry]" in snap_pct.format_energy_label()

    # Vietnamese localization test
    set_locale("vi")
    assert "85.5% [Nhập thủ công]" in snap_pct.format_energy_label()
    set_locale("en")


def test_quota_zero_and_edge_cases():
    # Zero quota remaining
    snap_zero = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=0.0,
        quota_total=100.0,
        quota_unit="requests",
    )
    assert snap_zero.percentage == 0.0
    assert "0.0% (0/100 requests)" in snap_zero.format_energy_label()

    # Negative quota -> clamp to 0.0
    snap_neg = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=-5.0,
        quota_total=100.0,
    )
    assert snap_neg.percentage == 0.0

    # Over quota total -> clamp to 100.0
    snap_overflow = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=120.0,
        quota_total=100.0,
    )
    assert snap_overflow.percentage == 100.0


def test_quota_unknown_no_guessing():
    # When no automated API is available, source = UNKNOWN, do not fabricate values
    snap_unknown = QuotaSnapshot(
        source="UNKNOWN",
        quota_remaining=None,
        quota_total=None,
    )
    assert snap_unknown.percentage is None
    assert snap_unknown.format_energy_label() == "Automatic quota data is unavailable"

    # Vietnamese localization test
    set_locale("vi")
    assert snap_unknown.format_energy_label() == "Chưa đọc được hạn mức tự động"
    set_locale("en")


def test_quota_stale_data_detection():
    # Snapshot created 48 hours ago
    past_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    snap_old = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=30.0,
        quota_total=100.0,
        last_updated=past_time,
        stale_threshold_hours=24.0,
    )
    assert snap_old.is_stale is True
    assert "(Stale Data)" in snap_old.format_energy_label()

    # Vietnamese localization test
    set_locale("vi")
    assert "(Dữ liệu cũ)" in snap_old.format_energy_label()
    set_locale("en")

    # Snapshot updated 10 minutes ago
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    snap_recent = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=30.0,
        quota_total=100.0,
        last_updated=recent_time,
    )
    assert snap_recent.is_stale is False
    assert "(Stale Data)" not in snap_recent.format_energy_label()


def test_token_usage_separate_from_quota():
    # Turn tokens are tracked independently from global quota
    token_use = TokenUsage.create(prompt=150, completion=350)
    assert token_use.prompt_tokens == 150
    assert token_use.completion_tokens == 350
    assert token_use.total_tokens == 500

    # Ensure plan expiration date is separated from periodic reset quota cycle
    snap = QuotaSnapshot(
        reset_at="2026-09-18T00:00:00Z",          # Daily quota reset
        plan_expiration="2027-01-01T00:00:00Z",   # Pro subscription expiration next year
    )
    assert snap.reset_at != snap.plan_expiration


def test_quota_pure_helpers():
    from rigmate.core.quota import (
        is_quota_exhausted,
        is_quota_available,
        is_quota_stale,
        calculate_valid_percentage,
    )

    # 1. 20/100 -> 20.0%
    assert calculate_valid_percentage(20.0, 100.0) == 20.0

    # 2. remaining=0 -> exhausted
    snap_zero = QuotaSnapshot(quota_remaining=0.0, quota_total=100.0)
    assert is_quota_exhausted(snap_zero) is True
    assert is_quota_available(snap_zero) is False

    # 3. unknown / no limit -> no fabricated percentage
    assert calculate_valid_percentage(None, 100.0) is None
    assert calculate_valid_percentage(50.0, None) is None
    assert calculate_valid_percentage(50.0, 0.0) is None

    # 4. Positive quota -> available
    snap_pos = QuotaSnapshot(quota_remaining=15.0, quota_total=100.0)
    assert is_quota_available(snap_pos) is True
    assert is_quota_exhausted(snap_pos) is False

    # 5. Unsupported label
    snap_unsup = QuotaSnapshot(source="UNSUPPORTED")
    assert snap_unsup.format_energy_label() == "Quota checking unsupported by provider"

