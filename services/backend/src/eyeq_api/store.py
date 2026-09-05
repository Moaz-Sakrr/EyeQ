"""In-memory store. Phase A only — replaced by PostgreSQL + Alembic.

Kept deliberately dumb so the FR6 access rule is visible in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Adjudication:
    alert_id: str
    decision: str          # "confirmed" | "dismissed"
    decided_at: float


@dataclass
class Store:
    alerts: dict[str, dict] = field(default_factory=dict)
    adjudications: dict[str, Adjudication] = field(default_factory=dict)
    history: dict[str, int] = field(default_factory=dict)  # seat_id -> confirmed count

    def is_adjudicated(self, alert_id: str) -> bool:
        return alert_id in self.adjudications


STORE = Store()
