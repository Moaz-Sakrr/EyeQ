"""Tests for the ONNX head detector and the stub<->real selector.

The post-processing helpers (letterbox / xywh2xyxy / nms) are pure and run in CI.
The model itself is exercised only when an ONNX file is provided via
EYEQ_DETECTOR_WEIGHTS, so CI (no weights) stays green.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/cv-engine/src"))
sys.path.insert(0, str(ROOT / "contracts"))


# --- selector: default must be the stub (no heavy deps, always runs) ---------

def test_factory_defaults_to_stub(monkeypatch):
    monkeypatch.delenv("EYEQ_DETECTOR_WEIGHTS", raising=False)
    from eyeq_cv.detector.factory import build_head_detector
    from eyeq_cv.detector.stub import HeadDetectorStub

    det = build_head_detector()
    assert isinstance(det, HeadDetectorStub)


def test_stub_output_keys_are_the_contract():
    """The real detector must return exactly these keys; pin them via the stub."""
    from eyeq_cv.detector.stub import HeadDetectorStub

    for d in HeadDetectorStub(n_seats=3).infer():
        assert set(d.keys()) == {"bbox", "conf"}
        assert len(d["bbox"]) == 4


# --- post-processing helpers (need numpy + cv2; installed in CI) --------------

def _helpers():
    pytest.importorskip("cv2")
    pytest.importorskip("onnxruntime")
    np = pytest.importorskip("numpy")
    from eyeq_cv.detector import onnx_detector as od
    return np, od


def test_letterbox_pads_to_square_and_ratio_maps_back():
    np, od = _helpers()
    img = np.zeros((240, 480, 3), dtype=np.uint8)  # 2:1 landscape
    padded, r, (pad_x, pad_y) = od.letterbox(img, imgsz=960)

    assert padded.shape[:2] == (960, 960)
    assert r == pytest.approx(2.0)          # min(960/240, 960/480) = 2.0
    assert pad_x == 0 and pad_y == 240      # width fills, height padded


def test_xywh2xyxy():
    np, od = _helpers()
    boxes = np.array([[50.0, 60.0, 20.0, 10.0]])  # cx,cy,w,h
    xyxy = od.xywh2xyxy(boxes)[0]
    assert list(xyxy) == [40.0, 55.0, 60.0, 65.0]


def test_nms_suppresses_overlap_keeps_disjoint():
    np, od = _helpers()
    boxes = np.array([
        [0, 0, 10, 10],       # A (highest score)
        [1, 1, 11, 11],       # near-duplicate of A -> suppressed
        [100, 100, 110, 110],  # disjoint -> kept
    ], dtype=float)
    scores = np.array([0.9, 0.8, 0.7])
    keep = od.nms(boxes, scores, iou_thres=0.5)
    assert keep == [0, 2]


def test_nms_empty_returns_empty():
    np, od = _helpers()
    assert od.nms(np.zeros((0, 4)), np.zeros((0,)), 0.5) == []


# --- real model (only when weights are provided) -----------------------------

@pytest.mark.skipif(not os.environ.get("EYEQ_DETECTOR_WEIGHTS"),
                    reason="EYEQ_DETECTOR_WEIGHTS not set")
def test_onnx_detector_infer_contract():
    np, od = _helpers()
    det = od.HeadDetectorONNX(os.environ["EYEQ_DETECTOR_WEIGHTS"])
    det.warmup()

    h, w = 720, 1280
    frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    out = det.infer(frame)

    assert isinstance(out, list)
    for d in out:
        assert set(d.keys()) == {"bbox", "conf"}
        x1, y1, x2, y2 = d["bbox"]
        assert all(isinstance(v, int) for v in d["bbox"])
        assert 0 <= x1 <= x2 <= w and 0 <= y1 <= y2 <= h
        assert 0.0 <= d["conf"] <= 1.0


@pytest.mark.skipif(not os.environ.get("EYEQ_DETECTOR_WEIGHTS"),
                    reason="EYEQ_DETECTOR_WEIGHTS not set")
def test_infer_none_frame_raises():
    np, od = _helpers()
    det = od.HeadDetectorONNX(os.environ["EYEQ_DETECTOR_WEIGHTS"])
    with pytest.raises(ValueError):
        det.infer(None)
