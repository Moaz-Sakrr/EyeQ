"""Base protocol every perception model implements.

Swapping a stub for a trained model = changing one line in the registry.
Nothing downstream knows or cares which one is loaded.
"""
from __future__ import annotations

from typing import Protocol, Sequence, Any


class PerceptionModel(Protocol):
    name: str

    def warmup(self) -> None: ...

    def infer(self, frame: Any, crops: Sequence[Any] | None = None) -> list[dict]:
        """Return one dict per detection/seat. Keys are model-specific and are
        merged into SeatObservation by the pipeline."""
        ...
