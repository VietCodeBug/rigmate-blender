"""Unit tests for bounded retry policy and backoff calculations."""

import pytest
from rigmate.core.retry import RetryPolicy


def test_retry_policy_boundaries():
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0, max_delay_seconds=10.0, backoff_factor=2.0)

    # Attempt 1 (first attempt failed) -> eligible to retry
    assert policy.should_retry(attempt_number=1) is True
    # Attempt 2 -> eligible to retry
    assert policy.should_retry(attempt_number=2) is True
    # Attempt 3 (reached max_attempts=3) -> do not retry further
    assert policy.should_retry(attempt_number=3) is False
    assert policy.should_retry(attempt_number=4) is False


def test_retry_policy_exponential_backoff_calculation():
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=0.5, max_delay_seconds=3.0, backoff_factor=2.0)

    # Delay for attempt 1: 0.5 * (2^0) = 0.5
    assert policy.get_delay_seconds(1) == 0.5
    # Delay for attempt 2: 0.5 * (2^1) = 1.0
    assert policy.get_delay_seconds(2) == 1.0
    # Delay for attempt 3: 0.5 * (2^2) = 2.0
    assert policy.get_delay_seconds(3) == 2.0
    # Delay for attempt 4: 0.5 * (2^3) = 4.0 -> clamped to max_delay_seconds (3.0)
    assert policy.get_delay_seconds(4) == 3.0


def test_retry_policy_validation_constraints():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        RetryPolicy(max_attempts=0)

    with pytest.raises(ValueError, match="max_attempts must be bounded"):
        RetryPolicy(max_attempts=11)

    with pytest.raises(ValueError, match="base_delay_seconds must be positive"):
        RetryPolicy(base_delay_seconds=0)

    with pytest.raises(ValueError, match="max_delay_seconds cannot be smaller"):
        RetryPolicy(base_delay_seconds=5.0, max_delay_seconds=2.0)
