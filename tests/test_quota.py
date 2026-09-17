"""Kiểm thử kỹ lưỡng hệ thống Quota, Thanh năng lượng, dữ liệu cũ và phân biệt token."""

from datetime import datetime, timezone, timedelta
import pytest
from rigmate.core.quota import QuotaSnapshot, TokenUsage


def test_quota_percentage_calculation():
    # 1. Đủ cả remaining và total
    snap = QuotaSnapshot(
        source="DEMO",
        quota_remaining=60.0,
        quota_total=100.0,
        quota_unit="credits",
    )
    assert snap.percentage == 60.0
    assert "60.0% (60/100 credits) [DEMO]" in snap.format_energy_label()

    # 2. Đơn vị là percentage trực tiếp
    snap_pct = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=85.5,
        quota_unit="percentage",
    )
    assert snap_pct.percentage == 85.5
    assert "85.5% [Nhập thủ công]" in snap_pct.format_energy_label()


def test_quota_zero_and_edge_cases():
    # Quota = 0 (hết sạch)
    snap_zero = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=0.0,
        quota_total=100.0,
        quota_unit="requests",
    )
    assert snap_zero.percentage == 0.0
    assert "0.0% (0/100 requests)" in snap_zero.format_energy_label()

    # Quota âm (dữ liệu bất thường hoặc quá hạn) -> clamp ở 0.0
    snap_neg = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=-5.0,
        quota_total=100.0,
    )
    assert snap_neg.percentage == 0.0

    # Quota vượt quá tổng (dữ liệu bất thường) -> clamp ở 100.0
    snap_overflow = QuotaSnapshot(
        source="AUTOMATIC",
        quota_remaining=120.0,
        quota_total=100.0,
    )
    assert snap_overflow.percentage == 100.0


def test_quota_unknown_no_guessing():
    # Khi không có API máy đọc, source = UNKNOWN, không tự suy đoán
    snap_unknown = QuotaSnapshot(
        source="UNKNOWN",
        quota_remaining=None,
        quota_total=None,
    )
    assert snap_unknown.percentage is None
    assert snap_unknown.format_energy_label() == "Chưa đọc được hạn mức tự động"


def test_quota_stale_data_detection():
    # Snapshot được tạo từ 48 giờ trước
    past_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    snap_old = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=30.0,
        quota_total=100.0,
        last_updated=past_time,
        stale_threshold_hours=24.0,
    )
    assert snap_old.is_stale is True
    assert "(Dữ liệu cũ)" in snap_old.format_energy_label()

    # Snapshot mới cập nhật 10 phút trước
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    snap_recent = QuotaSnapshot(
        source="MANUAL",
        quota_remaining=30.0,
        quota_total=100.0,
        last_updated=recent_time,
    )
    assert snap_recent.is_stale is False
    assert "(Dữ liệu cũ)" not in snap_recent.format_energy_label()


def test_token_usage_separate_from_quota():
    # Token tiêu thụ của lượt chat là độc lập với quota còn lại
    token_use = TokenUsage.create(prompt=150, completion=350)
    assert token_use.prompt_tokens == 150
    assert token_use.completion_tokens == 350
    assert token_use.total_tokens == 500

    # Đảm bảo trường ngày hết hạn gói (plan_expiration) tách biệt với chu kỳ reset quota
    snap = QuotaSnapshot(
        reset_at="2026-09-18T00:00:00Z",          # Reset quota hàng ngày
        plan_expiration="2027-01-01T00:00:00Z",   # Hết hạn gói Pro năm sau
    )
    assert snap.reset_at != snap.plan_expiration
