"""Head detector — STUB.

Replace with RT-DETR / YOLO trained on SCUT-HEAD Part A (task A2.1).
Contract: returns xyxy boxes + confidence. Nothing else.
"""
import random


class HeadDetectorStub:
    name = "head_detector"

    def __init__(self, n_seats: int = 30, seed: int = 0):
        self.n_seats = n_seats
        self._rng = random.Random(seed)

    def warmup(self) -> None:
        pass

    def infer(self, frame=None, crops=None) -> list[dict]:
        out = []
        for i in range(self.n_seats):
            x = (i % 6) * 160 + 40
            y = (i // 6) * 120 + 60
            out.append({
                "bbox": (x, y, x + 70, y + 70),
                "conf": round(self._rng.uniform(0.75, 0.99), 3),
            })
        return out
