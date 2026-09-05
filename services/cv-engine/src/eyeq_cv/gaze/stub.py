"""Gaze — STUB. Replace with L2CS-Net (task A2.4). Emits G.

This is the fragile channel: gaze needs clear eye pixels, which is the first
thing lost to distance and ceiling angle. The stub returns None for a fraction
of seats ON PURPOSE, so the fusion layer's missing-signal path is exercised
from day one rather than discovered in week 14.
"""
import random


class GazeStub:
    name = "gaze"

    def __init__(self, seed: int = 2, dropout: float = 0.25):
        self._rng = random.Random(seed)
        self.dropout = dropout

    def warmup(self) -> None:
        pass

    def infer(self, frame=None, crops=None) -> list[dict]:
        n = len(crops) if crops is not None else 0
        out = []
        for _ in range(n):
            if self._rng.random() < self.dropout:
                out.append({"G": None})
            else:
                out.append({"G": round(self._rng.betavariate(2, 6), 3)})
        return out
