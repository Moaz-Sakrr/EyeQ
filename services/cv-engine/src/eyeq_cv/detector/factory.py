"""Select the head detector at runtime.

Default is the stub, so CI and GPU-less machines stay green and the Docker smoke
run works with no weights present. Set EYEQ_DETECTOR_WEIGHTS to an exported ONNX
file to load the real detector instead. The onnx_detector module (and its heavy
deps) is imported lazily so the stub path never touches onnxruntime / cv2.
"""
from __future__ import annotations

import os


def build_head_detector():
    weights = os.environ.get("EYEQ_DETECTOR_WEIGHTS")
    if weights:
        from .onnx_detector import HeadDetectorONNX
        return HeadDetectorONNX(weights)
    from .stub import HeadDetectorStub
    return HeadDetectorStub()
