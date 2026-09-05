"""Behavior + objects — STUB. One backbone, merged classes (task A2.3).
Emits B and O."""
import random


class BehaviorObjectStub:
    name = "behavior_object"
    CLASSES = ("phone", "smartwatch", "turn_head", "bow_head", "lean_over")

    def __init__(self, seed: int = 3):
        self._rng = random.Random(seed)

    def warmup(self) -> None:
        pass

    def infer(self, frame=None, crops=None) -> list[dict]:
        n = len(crops) if crops is not None else 0
        out = []
        for _ in range(n):
            out.append({
                "B": round(self._rng.betavariate(2, 9), 3),
                "O": round(self._rng.betavariate(1.5, 12), 3),
            })
        return out
