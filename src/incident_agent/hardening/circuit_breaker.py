"""Deterministic circuit breaker for external dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from incident_agent.hardening.contracts import (
    CircuitState,
    HardeningError,
    HardeningErrorCode,
)


@dataclass
class CircuitBreaker:
    """Failure-threshold circuit breaker."""

    failure_threshold: int
    recovery_seconds: float
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at_epoch_seconds: float | None = None

    def allow_request(
        self,
        now_epoch_seconds: float,
    ) -> tuple[bool, HardeningError | None]:
        """Determine whether a dependency call may proceed."""

        if self.state is CircuitState.CLOSED:
            return True, None

        if self.state is CircuitState.HALF_OPEN:
            return True, None

        assert self.opened_at_epoch_seconds is not None

        if (
            now_epoch_seconds
            - self.opened_at_epoch_seconds
            >= self.recovery_seconds
        ):
            self.state = CircuitState.HALF_OPEN
            return True, None

        return (
            False,
            HardeningError(
                code=HardeningErrorCode.CIRCUIT_OPEN,
                message=(
                    "Dependency circuit is open."
                ),
            ),
        )

    def record_success(self) -> None:
        """Close the circuit after a successful call."""

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.opened_at_epoch_seconds = None

    def record_failure(
        self,
        now_epoch_seconds: float,
    ) -> None:
        """Record a dependency failure."""

        self.consecutive_failures += 1

        if (
            self.consecutive_failures
            >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN
            self.opened_at_epoch_seconds = (
                now_epoch_seconds
            )
