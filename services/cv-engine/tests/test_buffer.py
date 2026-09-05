import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services/cv-engine/src"))
from eyeq_cv.buffer.circular import CircularFrameBuffer


def test_clip_contains_pre_and_post_roll():
    b = CircularFrameBuffer(fps=2, pre_seconds=2, post_seconds=2)
    for i in range(10):
        b.push(float(i), f"f{i}")
    b.trigger()
    clip = None
    for i in range(10, 20):
        clip = b.push(float(i), f"f{i}") or clip
    assert clip is not None
    assert len(clip) == 4 + 4  # pre-roll + post-roll
