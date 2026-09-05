import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/cv-engine/src"))
sys.path.insert(0, str(ROOT / "contracts"))

from eyeq_cv.seat_resolver import SeatResolver, synthetic_layout


def test_resolves_to_seat():
    r = SeatResolver(synthetic_layout())
    assert r.resolve((10, 10, 80, 80)) == "R1C1"


def test_outside_layout_returns_none():
    r = SeatResolver(synthetic_layout())
    assert r.resolve((5000, 5000, 5070, 5070)) is None


def test_empty_seats_are_reported():
    r = SeatResolver(synthetic_layout(rows=2, cols=2))
    empty = r.empty_seats({"R1C1"})
    assert empty == {"R1C2", "R2C1", "R2C2"}
