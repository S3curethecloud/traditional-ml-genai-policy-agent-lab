"""In-memory idempotency and replay-protection store."""

from __future__ import annotations

from dataclasses import dataclass, field

from incident_agent.runtime.contracts import (
    ExecutionRecord,
)


@dataclass
class InMemoryIdempotencyStore:
    """Tutorial replay-protection store."""

    _records: dict[str, ExecutionRecord] = field(
        default_factory=dict
    )

    def get(
        self,
        idempotency_key: str,
    ) -> ExecutionRecord | None:
        """Return a prior record for an idempotency key."""

        return self._records.get(idempotency_key)

    def save(
        self,
        idempotency_key: str,
        record: ExecutionRecord,
    ) -> None:
        """Persist a completed runtime record."""

        self._records[idempotency_key] = record

    def contains(
        self,
        idempotency_key: str,
    ) -> bool:
        """Return whether the key has already been used."""

        return idempotency_key in self._records
