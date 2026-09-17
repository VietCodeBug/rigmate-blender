"""Unit tests for canonical UTC time helpers."""

from datetime import datetime, timezone, timedelta
import pytest
from rigmate.core.time_utils import (
    utc_now,
    to_utc_iso,
    parse_utc_iso,
)


def test_time_utils_utc_now():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_time_utils_to_utc_iso_roundtrip():
    now = utc_now()
    iso_str = to_utc_iso(now)
    assert iso_str.endswith("Z")

    parsed = parse_utc_iso(iso_str)
    assert parsed.tzinfo == timezone.utc
    assert abs((parsed - now).total_seconds()) < 1e-4


def test_time_utils_timezone_conversion():
    # Construct +07:00 (e.g. Vietnam timezone)
    tz_vn = timezone(timedelta(hours=7))
    dt_vn = datetime(2026, 9, 17, 14, 30, 0, tzinfo=tz_vn)

    iso_str = to_utc_iso(dt_vn)
    assert iso_str == "2026-09-17T07:30:00Z"

    parsed = parse_utc_iso(iso_str)
    assert parsed.hour == 7


def test_time_utils_naive_datetime_rejected():
    naive = datetime(2026, 9, 17, 14, 30, 0)
    with pytest.raises(ValueError, match="Naive datetime rejected"):
        to_utc_iso(naive)


def test_time_utils_malformed_string_rejected():
    with pytest.raises(ValueError, match="Malformed ISO timestamp string"):
        parse_utc_iso("not-a-timestamp")
