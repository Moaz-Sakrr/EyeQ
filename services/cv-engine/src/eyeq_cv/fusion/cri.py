"""Cheating Risk Index — weighted fusion over a rolling window.

Three properties this module must never lose:

1. No single signal raises an alert on its own.
2. A MISSING signal is not a CLEAN signal. Its weight is redistributed
   across the channels that are present (A3.3).
3. A LOW-VISIBILITY observation is gated out entirely, not scored as normal
   behaviour (A3.4).

Weights are calibrated (grid search / logistic regression on labelled hall
footage, task B4), never learned by backpropagation.
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4].parent / "contracts"))
from schemas.seat_observation import SeatObservation, CRIResult  # noqa: E402


@dataclass
class CRIConfig:
    """Phase A placeholder values. Replaced by B4 calibration output.

    These live in config, never hardcoded in logic — so recalibrating is a
    config change, not a code change.
    """
    wH: float = 0.30
    wG: float = 0.25
    wO: float = 0.30
    wT: float = 0.15
    tau_raise: float = 0.65        # alert on
    tau_clear: float = 0.50        # alert off — hysteresis gap prevents flicker
    window_frames: int = 30
    min_visibility: float = 0.35
    persistence_ratio: float = 0.60  # fraction of window that must be elevated


class CRIEngine:
    def __init__(self, cfg: CRIConfig | None = None):
        self.cfg = cfg or CRIConfig()
        self._hist: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.cfg.window_frames))
        self._alerting: set[str] = set()

    # ---- signal fusion -------------------------------------------------
    def _instant_score(self, obs: SeatObservation) -> float | None:
        """Weighted score for one frame, with missing-channel redistribution."""
        weights = {"H": self.cfg.wH, "G": self.cfg.wG, "O": self.cfg.wO}
        present = obs.present_signals()
        # B is folded into O's channel: both come from the same backbone.
        if "B" in present:
            present["O"] = max(present.get("O", 0.0), present.pop("B") * 0.8)

        active = {k: w for k, w in weights.items() if k in present}
        if not active:
            return None
        total = sum(active.values())
        return sum(present[k] * (w / total) for k, w in active.items())

    # ---- rolling window ------------------------------------------------
    def update(self, obs: SeatObservation) -> CRIResult:
        cfg = self.cfg

        if obs.visibility < cfg.min_visibility:
            # Occlusion gate: we do not know, so we do not score.
            return CRIResult(obs.seat_id, obs.frame_ts, 0.0, 0.0, {}, gated=True)

        inst = self._instant_score(obs)
        if inst is None:
            return CRIResult(obs.seat_id, obs.frame_ts, 0.0, 0.0, {}, gated=True)

        buf = self._hist[obs.seat_id]
        buf.append(inst)

        elevated = sum(1 for v in buf if v >= cfg.tau_clear)
        T = elevated / len(buf) if buf else 0.0

        base = sum(buf) / len(buf)
        cri = (1 - cfg.wT) * base + cfg.wT * T

        alert = self._hysteresis(obs.seat_id, cri, T)

        return CRIResult(
            seat_id=obs.seat_id,
            window_end_ts=obs.frame_ts,
            cri=round(cri, 4),
            T=round(T, 4),
            contributing=obs.present_signals(),
            gated=False,
            alert=alert,
        )

    def _hysteresis(self, seat_id: str, cri: float, T: float) -> bool:
        cfg = self.cfg
        buf = self._hist[seat_id]
        warm = len(buf) >= max(5, cfg.window_frames // 3)

        if seat_id in self._alerting:
            if cri < cfg.tau_clear:
                self._alerting.discard(seat_id)
            return seat_id in self._alerting

        if warm and cri >= cfg.tau_raise and T >= cfg.persistence_ratio:
            self._alerting.add(seat_id)
            return True
        return False

    def reset(self, seat_id: str | None = None) -> None:
        if seat_id is None:
            self._hist.clear()
            self._alerting.clear()
        else:
            self._hist.pop(seat_id, None)
            self._alerting.discard(seat_id)
