"""Circular in-RAM frame buffer.

Normal operation writes nothing to disk. On an alert, a pre+post window is
serialised as a discrete evidence clip. This is the privacy architecture
implemented, not merely stated as policy.
"""
from __future__ import annotations

from collections import deque
from typing import Any


class CircularFrameBuffer:
    def __init__(self, fps: int = 10, pre_seconds: int = 15,
                 post_seconds: int = 15):
        self.fps = fps
        self.pre = pre_seconds
        self.post = post_seconds
        self._buf: deque[tuple[float, Any]] = deque(maxlen=fps * pre_seconds)
        self._pending: list[tuple[float, Any]] | None = None
        self._need = 0

    def push(self, ts: float, frame: Any) -> list[tuple[float, Any]] | None:
        """Append a frame. Returns a completed clip when one is ready."""
        self._buf.append((ts, frame))
        if self._pending is not None:
            self._pending.append((ts, frame))
            self._need -= 1
            if self._need <= 0:
                clip, self._pending = self._pending, None
                return clip
        return None

    def trigger(self) -> None:
        """Alert fired: capture the pre-roll and start collecting post-roll."""
        if self._pending is None:
            self._pending = list(self._buf)
            self._need = self.fps * self.post
