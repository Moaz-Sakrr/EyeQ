"""Head bbox -> seat_id, via calibrated seat regions.

Replaces face-recognition / cross-frame tracking entirely (FR3). Seating is
fixed and known in advance, so a calibrated region lookup achieves the same
association with no identity-switch risk.

Phase A runs this against a SYNTHETIC layout. Phase B swaps in the real
calibration file produced by the Admin tool (task B2.2).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SeatRegion:
    seat_id: str
    x1: int
    y1: int
    x2: int
    y2: int

    def contains(self, cx: float, cy: float) -> bool:
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2

    def center_dist2(self, cx: float, cy: float) -> float:
        mx, my = (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
        return (cx - mx) ** 2 + (cy - my) ** 2


class SeatResolver:
    def __init__(self, regions: list[SeatRegion]):
        self.regions = regions

    @classmethod
    def from_file(cls, path: str | Path) -> "SeatResolver":
        data = json.loads(Path(path).read_text())
        return cls([SeatRegion(**r) for r in data["regions"]])

    def resolve(self, bbox: tuple[int, int, int, int]) -> str | None:
        """Return seat_id, or None if the head falls outside every region.

        A head on the boundary of two regions goes to the nearer centre —
        deterministic, so the same frame always yields the same mapping.
        """
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        hits = [r for r in self.regions if r.contains(cx, cy)]
        if not hits:
            return None
        if len(hits) == 1:
            return hits[0].seat_id
        return min(hits, key=lambda r: r.center_dist2(cx, cy)).seat_id

    def empty_seats(self, assigned: set[str]) -> set[str]:
        """Seats with no head this frame. An absent student is NOT an anomaly."""
        return {r.seat_id for r in self.regions} - assigned


def synthetic_layout(rows: int = 5, cols: int = 6,
                     w: int = 160, h: int = 120) -> list[SeatRegion]:
    """Grid layout for Phase A testing. NOT the real hall geometry."""
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append(SeatRegion(
                seat_id=f"R{r+1}C{c+1}",
                x1=c * w, y1=r * h, x2=(c + 1) * w, y2=(r + 1) * h,
            ))
    return out
