"""Wires perception models -> SeatObservation -> CRI.

Every model here is a stub today. Task A2.6 replaces them one at a time,
each in its own PR. The pipeline itself does not change.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3].parent / "contracts"))
from schemas.seat_observation import SeatObservation  # noqa: E402

from .detector.stub import HeadDetectorStub
from .headpose.stub import HeadPoseStub
from .gaze.stub import GazeStub
from .behavior.stub import BehaviorObjectStub
from .seat_resolver import SeatResolver, synthetic_layout
from .fusion.cri import CRIEngine, CRIConfig


class Pipeline:
    def __init__(self, resolver: SeatResolver | None = None,
                 cfg: CRIConfig | None = None):
        self.detector = HeadDetectorStub()
        self.headpose = HeadPoseStub()
        self.gaze = GazeStub()
        self.behavior = BehaviorObjectStub()
        self.resolver = resolver or SeatResolver(synthetic_layout())
        self.cri = CRIEngine(cfg)

    def process_frame(self, frame=None, ts: float | None = None):
        ts = ts if ts is not None else time.time()

        dets = self.detector.infer(frame)
        crops = [d["bbox"] for d in dets]

        hp = self.headpose.infer(frame, crops)
        gz = self.gaze.infer(frame, crops)
        bo = self.behavior.infer(frame, crops)

        results, assigned = [], set()
        for i, det in enumerate(dets):
            seat_id = self.resolver.resolve(det["bbox"])
            if seat_id is None:
                continue
            assigned.add(seat_id)
            obs = SeatObservation(
                seat_id=seat_id,
                frame_ts=ts,
                H=hp[i].get("H"),
                G=gz[i].get("G"),
                O=bo[i].get("O"),
                B=bo[i].get("B"),
                visibility=det["conf"],
                bbox=det["bbox"],
            )
            results.append(self.cri.update(obs))

        # Empty seats are absences, not anomalies (FR3).
        _ = self.resolver.empty_seats(assigned)
        return results
