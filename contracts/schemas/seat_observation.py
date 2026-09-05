"""
EyeQ shared data contract.

Every perception model writes ONE SeatObservation per seat per frame.
The join key is `seat_id`. Models never see each other; they meet here.

RULE: changing this file requires its own PR, reviewed by one person from
each affected layer, merged BEFORE any code that depends on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


CONTRACT_VERSION = "0.1.0"


class Signal(str, Enum):
    """CRI input channels. Keep in sync with fusion weights."""
    HEAD_POSE = "H"
    GAZE = "G"
    OBJECT = "O"
    BEHAVIOR = "B"


@dataclass
class SeatObservation:
    """One seat, one frame, one row.

    A model that cannot fill its column leaves it as None. Fusion then
    redistributes that channel's weight across the channels that ARE
    present, instead of reading a missing signal as a clean one.
    """
    seat_id: str
    frame_ts: float

    H: Optional[float] = None   # head-pose deviation from forward baseline, [0,1]
    G: Optional[float] = None   # gaze deviation toward non-permitted region, [0,1]
    O: Optional[float] = None   # unauthorized-object confidence, [0,1]
    B: Optional[float] = None   # behavior-class confidence, [0,1]

    visibility: float = 1.0     # detection quality, [0,1]. Drives occlusion gating.
    bbox: Optional[tuple[int, int, int, int]] = None  # xyxy, debug/evidence only

    def present_signals(self) -> dict[str, float]:
        return {k: v for k, v in
                (("H", self.H), ("G", self.G), ("O", self.O), ("B", self.B))
                if v is not None}

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CRIResult:
    """Output of the fusion layer for one seat over a rolling window."""
    seat_id: str
    window_end_ts: float
    cri: float                       # [0,1]
    T: float                         # temporal persistence factor, [0,1]
    contributing: dict[str, float] = field(default_factory=dict)
    gated: bool = False              # True when occlusion-gated out
    alert: bool = False


@dataclass
class AlertPayload:
    """Pushed to the Controller over WebSocket.

    FR6 — this payload MUST NOT carry the student's behavioral history.
    History is served by a separate endpoint, and only after the Controller
    has recorded an independent adjudication. Enforced by
    tests/test_fr6.py::test_alert_payload_contains_no_history.
    """
    alert_id: str
    session_id: str
    seat_id: str
    timestamp: float
    cri: float
    evidence_clip_ref: Optional[str] = None
    contributing: dict[str, float] = field(default_factory=dict)
    # NO history / prior_incidents / risk_profile field. See ADR-0001.
