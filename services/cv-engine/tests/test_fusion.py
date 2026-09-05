import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/cv-engine/src"))
sys.path.insert(0, str(ROOT / "contracts"))

from schemas.seat_observation import SeatObservation
from eyeq_cv.fusion.cri import CRIEngine, CRIConfig


def obs(**kw):
    base = dict(seat_id="R1C1", frame_ts=0.0, visibility=0.9)
    base.update(kw)
    return SeatObservation(**base)


def test_single_signal_does_not_alert():
    """A high object score alone must not raise an alert."""
    e = CRIEngine()
    fired = False
    for i in range(40):
        r = e.update(obs(frame_ts=i, O=0.95, H=0.02, G=0.02))
        fired = fired or r.alert
    assert not fired


def test_corroborated_signals_alert():
    e = CRIEngine()
    fired = any(e.update(obs(frame_ts=i, H=0.9, G=0.9, O=0.85)).alert
                for i in range(40))
    assert fired


def test_low_visibility_is_gated_not_scored():
    """Occlusion must not be read as clean behaviour."""
    e = CRIEngine()
    r = e.update(obs(H=0.95, G=0.95, O=0.95, visibility=0.1))
    assert r.gated and r.cri == 0.0


def test_missing_gaze_redistributes_weight():
    """With G absent, remaining channels must still reach full scale."""
    e = CRIEngine()
    r = e.update(obs(H=1.0, G=None, O=1.0))
    assert r.cri > 0.5, "missing channel must not dilute the score toward zero"


def test_all_signals_missing_is_gated():
    e = CRIEngine()
    r = e.update(obs(H=None, G=None, O=None, B=None))
    assert r.gated


def test_hysteresis_prevents_flicker():
    """Once alerting, a dip above tau_clear must not clear the alert."""
    cfg = CRIConfig()
    e = CRIEngine(cfg)
    for i in range(40):
        e.update(obs(frame_ts=i, H=0.95, G=0.95, O=0.95))
    r = e.update(obs(frame_ts=41, H=0.62, G=0.62, O=0.62))
    assert r.alert
