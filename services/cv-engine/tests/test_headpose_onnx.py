"""Tests for the 6DRepNet head-pose scaffold and the stub<->real selector.

The angle math (deviation, ortho6d->euler) is pure and runs in CI. The model
itself is exercised only when EYEQ_HEADPOSE_WEIGHTS points at an ONNX file, so CI
(no weights) stays green.
"""
import math
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/cv-engine/src"))
sys.path.insert(0, str(ROOT / "contracts"))


# --- selector: default must be the stub (no heavy deps, always runs) ---------

def test_factory_defaults_to_stub(monkeypatch):
    monkeypatch.delenv("EYEQ_HEADPOSE_WEIGHTS", raising=False)
    from eyeq_cv.headpose.factory import build_head_pose
    from eyeq_cv.headpose.stub import HeadPoseStub

    assert isinstance(build_head_pose(), HeadPoseStub)


def test_stub_output_keys_are_the_contract():
    """The real model must return exactly this key per crop; pin it via the stub."""
    from eyeq_cv.headpose.stub import HeadPoseStub

    out = HeadPoseStub().infer(crops=[(0, 0, 10, 10), (5, 5, 20, 20)])
    assert len(out) == 2
    for d in out:
        assert set(d.keys()) == {"H"}


# --- angle math (needs numpy/cv2/onnxruntime; installed in CI) ---------------

def _mod():
    pytest.importorskip("cv2")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("numpy")
    from eyeq_cv.headpose import onnx_headpose as hp
    return hp


def test_deviation_forward_is_zero():
    hp = _mod()
    cfg = hp.HeadPoseConfig()
    assert hp.deviation(0.0, 0.0, cfg) == 0.0


def test_deviation_saturates_at_max_angle():
    hp = _mod()
    cfg = hp.HeadPoseConfig(max_angle=45.0)
    assert hp.deviation(45.0, 0.0, cfg) == 1.0     # exactly at cap
    assert hp.deviation(90.0, 90.0, cfg) == 1.0    # clamped, not >1


def test_deviation_respects_baseline_offset():
    hp = _mod()
    # Baseline at yaw0=30: a head at yaw=30 reads as forward (H=0).
    cfg = hp.HeadPoseConfig(yaw0=30.0, pitch0=0.0, max_angle=45.0)
    assert hp.deviation(30.0, 0.0, cfg) == 0.0
    expected = round(min(math.hypot(0.0, 20.0) / 45.0, 1.0), 3)
    assert hp.deviation(30.0, 20.0, cfg) == expected


def test_identity_rotation_gives_zero_euler():
    hp = _mod()
    np = pytest.importorskip("numpy")
    ortho6d = np.array([[1, 0, 0, 0, 1, 0]], dtype=float)  # identity basis
    pitch, yaw, roll = hp.matrix_to_euler_deg(hp.rotation_6d_to_matrix(ortho6d))
    assert abs(pitch[0]) < 1e-6 and abs(yaw[0]) < 1e-6 and abs(roll[0]) < 1e-6


# --- real model (only when weights are provided) -----------------------------

@pytest.mark.skipif(not os.environ.get("EYEQ_HEADPOSE_WEIGHTS"),
                    reason="EYEQ_HEADPOSE_WEIGHTS not set")
def test_onnx_headpose_infer_contract():
    hp = _mod()
    np = pytest.importorskip("numpy")
    model = hp.HeadPoseONNX(os.environ["EYEQ_HEADPOSE_WEIGHTS"])
    model.warmup()

    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    crops = [(100, 100, 180, 180), (400, 300, 470, 380)]
    out = model.infer(frame, crops)

    assert len(out) == len(crops)
    for d in out:
        assert set(d.keys()) == {"H"}
        if d["H"] is not None:
            assert 0.0 <= d["H"] <= 1.0


@pytest.mark.skipif(not os.environ.get("EYEQ_HEADPOSE_WEIGHTS"),
                    reason="EYEQ_HEADPOSE_WEIGHTS not set")
def test_degenerate_crop_is_none_not_zero():
    hp = _mod()
    np = pytest.importorskip("numpy")
    model = hp.HeadPoseONNX(os.environ["EYEQ_HEADPOSE_WEIGHTS"])
    frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    # Second box is out-of-frame / zero-area -> must be None, not a clean score.
    out = model.infer(frame, [(10, 10, 60, 60), (500, 500, 400, 400)])
    assert out[1]["H"] is None
