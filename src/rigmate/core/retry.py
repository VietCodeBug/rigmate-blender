"""Bounded retry policy and exponential backoff calculator.

IMPORTANT ARCHITECTURAL NOTE:
This utility models pure retry policy and backoff calculations.
It is intended for idempotent read and network probing operations.
MUTATION operations (e.g. mesh changes, file writes, scene edits) must NEVER
blindly retry without idempotency keys and state lookup.
"""

from typing import Optional


class RetryPolicy:
    """
    Deterministic bounded retry policy configuration.
    Enforces maximum attempt bounds and prevents infinite retry loops.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5,
        max_delay_seconds: float = 10.0,
        backoff_factor: float = 2.0,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if max_attempts > 10:
            raise ValueError("max_attempts must be bounded (<= 10)")
        if base_delay_seconds <= 0.0:
            raise ValueError("base_delay_seconds must be positive")
        if max_delay_seconds < base_delay_seconds:
            raise ValueError("max_delay_seconds cannot be smaller than base_delay_seconds")
        if backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")

        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_factor = backoff_factor

    def should_retry(self, attempt_number: int) -> bool:
        """
        Check if attempt_number (1-indexed) is eligible for a retry.
        attempt_number=1 means first try (failed). If max_attempts=3, retry on attempt 1 and 2.
        """
        return attempt_number < self.max_attempts

    def get_delay_seconds(self, attempt_number: int) -> float:
        """
        Compute deterministic exponential backoff delay for the next attempt.
        attempt_number is 1-indexed (the attempt that just failed).
        Delay = min(base_delay * (factor ** (attempt - 1)), max_delay).
        """
        if attempt_number < 1:
            raise ValueError("attempt_number must be >= 1")

        delay = self.base_delay_seconds * (self.backoff_factor ** (attempt_number - 1))
        return min(delay, self.max_delay_seconds)
