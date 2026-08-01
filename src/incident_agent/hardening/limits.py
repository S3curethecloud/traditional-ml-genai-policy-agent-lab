"""Rate and concurrency controls for workflow admission."""

from __future__ import annotations

from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterator

from incident_agent.hardening.contracts import (
    HardeningError,
    HardeningErrorCode,
)


@dataclass
class SlidingWindowRateLimiter:
    """Deterministic per-subject sliding-window limiter."""

    maximum_requests: int
    window_seconds: float
    _requests: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(deque)
    )

    def allow(
        self,
        subject: str,
        now_epoch_seconds: float,
    ) -> tuple[bool, HardeningError | None]:
        """Evaluate one request against the rate limit."""

        history = self._requests[subject]
        cutoff = now_epoch_seconds - self.window_seconds

        while history and history[0] <= cutoff:
            history.popleft()

        if len(history) >= self.maximum_requests:
            return (
                False,
                HardeningError(
                    code=(
                        HardeningErrorCode
                        .RATE_LIMIT_EXCEEDED
                    ),
                    message=(
                        "Request rate limit exceeded."
                    ),
                ),
            )

        history.append(now_epoch_seconds)

        return True, None


@dataclass
class ConcurrencyLimiter:
    """Thread-safe workflow concurrency limiter."""

    maximum_concurrent: int
    _active: int = 0
    _lock: Lock = field(default_factory=Lock)

    @property
    def active(self) -> int:
        """Return the current active count."""

        with self._lock:
            return self._active

    def acquire(
        self,
    ) -> tuple[bool, HardeningError | None]:
        """Acquire one workflow slot."""

        with self._lock:
            if self._active >= self.maximum_concurrent:
                return (
                    False,
                    HardeningError(
                        code=(
                            HardeningErrorCode
                            .CONCURRENCY_LIMIT_EXCEEDED
                        ),
                        message=(
                            "Maximum workflow concurrency "
                            "has been reached."
                        ),
                    ),
                )

            self._active += 1

        return True, None

    def release(self) -> None:
        """Release one workflow slot."""

        with self._lock:
            if self._active <= 0:
                raise RuntimeError(
                    "Concurrency limiter underflow"
                )

            self._active -= 1

    @contextmanager
    def slot(self) -> Iterator[None]:
        """Acquire and release a workflow slot."""

        allowed, error = self.acquire()

        if not allowed:
            assert error is not None
            raise RuntimeError(error.code.value)

        try:
            yield
        finally:
            self.release()
