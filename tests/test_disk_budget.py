"""Unit tests for disk budget calculation logic."""

import pytest
from rigmate.storage.disk_budget import (
    calculate_disk_budget,
    check_path_disk_budget,
)


def test_disk_budget_enough_space():
    # 50 MB required, 500 MB available, 100 MB safety margin -> allowed
    res = calculate_disk_budget(
        required_bytes=50 * 1024 * 1024,
        available_bytes=500 * 1024 * 1024,
        safety_margin_bytes=100 * 1024 * 1024,
    )
    assert res.allowed is True
    assert res.shortfall == 0
    assert res.required_total == 150 * 1024 * 1024


def test_disk_budget_insufficient_space_and_shortfall():
    # 100 MB required, 120 MB available, 50 MB safety margin -> total 150 MB, shortfall 30 MB
    res = calculate_disk_budget(
        required_bytes=100 * 1024 * 1024,
        available_bytes=120 * 1024 * 1024,
        safety_margin_bytes=50 * 1024 * 1024,
    )
    assert res.allowed is False
    assert res.shortfall == 30 * 1024 * 1024


def test_disk_budget_exact_boundary():
    # Exactly equal -> allowed
    res = calculate_disk_budget(
        required_bytes=50,
        available_bytes=100,
        safety_margin_bytes=50,
    )
    assert res.allowed is True
    assert res.shortfall == 0


def test_disk_budget_negative_inputs_rejected():
    with pytest.raises(ValueError, match="must be non-negative"):
        calculate_disk_budget(required_bytes=-10, available_bytes=100)


def test_disk_budget_check_path(tmp_path):
    res = check_path_disk_budget(tmp_path, required_bytes=1024)
    assert res.available > 0
    assert isinstance(res.allowed, bool)
