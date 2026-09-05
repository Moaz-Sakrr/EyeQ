"""Select the head-pose model at runtime.

Default is the stub, so CI and GPU-less machines stay green. Set
EYEQ_HEADPOSE_WEIGHTS to an exported 6DRepNet ONNX to load the real model. The
onnx_headpose module (and its heavy deps) is imported lazily so the stub path
never touches onnxruntime / cv2.
"""
from __future__ import annotations

import os


def build_head_pose():
    weights = os.environ.get("EYEQ_HEADPOSE_WEIGHTS")
    if weights:
        from .onnx_headpose import HeadPoseONNX
        return HeadPoseONNX(weights)
    from .stub import HeadPoseStub
    return HeadPoseStub()
