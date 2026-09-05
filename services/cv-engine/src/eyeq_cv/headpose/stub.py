"""Head pose — STUB. Replace with 6DRepNet fine-tune (task A2.2). Emits H."""
import random


class HeadPoseStub:
    name = "head_pose"

    def __init__(self, seed: int = 1):
        self._rng = random.Random(seed)

    def warmup(self) -> None:
        pass

    def infer(self, frame=None, crops=None) -> list[dict]:
        n = len(crops) if crops is not None else 0
        return [{"H": round(self._rng.betavariate(2, 8), 3)} for _ in range(n)]
