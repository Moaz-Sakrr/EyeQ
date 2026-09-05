"""Head pose — 6DRepNet via ONNX runtime (task A2.2). SCAFFOLD.

Runtime replacement for HeadPoseStub. Same contract: one {"H": float | None}
per crop, index-aligned to the crops it is given. The stub is kept, not deleted.

Why onnxruntime and not the 6DRepNet PyTorch repo: the shipped cv-engine runs
exported ONNX only (ADR-0002 spirit — no heavy training deps in the service).

--- What is still open (scaffold, not finished wiring) -----------------------
1. WEIGHTS: no ONNX yet. Set EYEQ_HEADPOSE_WEIGHTS to an exported 6DRepNet ONNX
   to activate this path; otherwise the stub is used. See scripts/download_weights.sh.
2. OUTPUT LAYOUT: 6DRepNet's head emits a 6D rotation representation (ortho6d).
   The exact tensor shape/order of the *exported* graph must be confirmed against
   the real file — infer() guards for both (M,6) ortho6d and (M,3) euler-degrees,
   and will raise on anything else so a mismatch fails loudly rather than silently.
3. BASELINE: "forward" is camera-angle dependent, and the cameras are not yet
   installed. HeadPoseConfig.{yaw0,pitch0,max_angle} are DOCUMENTED PLACEHOLDERS,
   to be calibrated against real hall geometry (mirrors CRIConfig's placeholders).
   This is a physical-world follow-up, not a value to guess in code.

Heavy imports (onnxruntime, cv2, numpy) sit at module top on purpose: this module
is imported lazily by headpose/factory.py only when the real model is selected.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
import onnxruntime as ort

# ImageNet normalization — 6DRepNet expects RGB crops normalized this way.
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class HeadPoseConfig:
    """Placeholders. `max_angle` is the yaw/pitch magnitude (degrees) that maps to
    H=1.0; (yaw0, pitch0) is the 'looking forward' baseline. Calibrate per hall."""
    imgsz: int = 224
    yaw0: float = 0.0
    pitch0: float = 0.0
    max_angle: float = 45.0


def deviation(yaw_deg: float, pitch_deg: float, cfg: HeadPoseConfig) -> float:
    """Collapse yaw+pitch into H in [0,1]. Roll is intentionally ignored (weak,
    noisy cheating signal). Pure function — unit-tested without the model."""
    d = math.hypot(yaw_deg - cfg.yaw0, pitch_deg - cfg.pitch0)
    return round(min(d / cfg.max_angle, 1.0), 3)


def rotation_6d_to_matrix(v: np.ndarray) -> np.ndarray:
    """ortho6d (M,6) -> rotation matrices (M,3,3) via Gram-Schmidt.

    Mirrors 6DRepNet's compute_rotation_matrix_from_ortho6d.
    """
    x_raw, y_raw = v[:, 0:3], v[:, 3:6]
    x = x_raw / (np.linalg.norm(x_raw, axis=1, keepdims=True) + 1e-8)
    z = np.cross(x, y_raw)
    z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-8)
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=-1)  # columns are the basis vectors


def matrix_to_euler_deg(R: np.ndarray):
    """Rotation matrices (M,3,3) -> (pitch, yaw, roll) arrays in degrees.

    Matches 6DRepNet's compute_euler_angles_from_rotation_matrices convention.
    """
    sy = np.sqrt(R[:, 0, 0] ** 2 + R[:, 1, 0] ** 2)
    singular = sy < 1e-6
    pitch = np.where(singular, np.arctan2(-R[:, 1, 2], R[:, 1, 1]),
                     np.arctan2(R[:, 2, 1], R[:, 2, 2]))
    yaw = np.arctan2(-R[:, 2, 0], sy)
    roll = np.where(singular, 0.0, np.arctan2(R[:, 1, 0], R[:, 0, 0]))
    return np.degrees(pitch), np.degrees(yaw), np.degrees(roll)


def _clip_box(box, w: int, h: int):
    x1, y1, x2, y2 = box
    return (max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2)))


def _preprocess(crop: np.ndarray, imgsz: int) -> np.ndarray:
    resized = cv2.resize(crop, (imgsz, imgsz), interpolation=cv2.INTER_LINEAR)
    rgb = resized[:, :, ::-1].astype(np.float32) / 255.0
    normed = (rgb - _MEAN) / _STD
    return normed.transpose(2, 0, 1)  # HWC -> CHW


class HeadPoseONNX:
    """Drop-in for HeadPoseStub. Returns [{"H": float | None}], one per crop.

    A crop that is empty/degenerate yields {"H": None} — the missing-signal path,
    which fusion redistributes rather than reading as clean-forward.
    """
    name = "head_pose"

    def __init__(self, weights_path: str, cfg: HeadPoseConfig | None = None,
                 providers: list[str] | None = None):
        self.cfg = cfg or HeadPoseConfig()
        self.session = ort.InferenceSession(
            weights_path, providers=providers or ["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def warmup(self) -> None:
        dummy = np.zeros((self.cfg.imgsz, self.cfg.imgsz, 3), dtype=np.uint8)
        self.infer(dummy, crops=[(0, 0, self.cfg.imgsz, self.cfg.imgsz)])

    def infer(self, frame, crops=None) -> list[dict]:
        if crops is None or len(crops) == 0:
            return []
        if frame is None:
            raise ValueError("HeadPoseONNX needs an image frame to crop from.")

        h0, w0 = frame.shape[:2]
        results: list[dict] = [{"H": None} for _ in crops]

        blobs, idx_valid = [], []
        for i, box in enumerate(crops):
            x1, y1, x2, y2 = _clip_box(box, w0, h0)
            if x2 <= x1 or y2 <= y1:
                continue  # degenerate crop -> H stays None
            blobs.append(_preprocess(frame[y1:y2, x1:x2], self.cfg.imgsz))
            idx_valid.append(i)

        if not blobs:
            return results

        batch = np.ascontiguousarray(np.stack(blobs), dtype=np.float32)
        out = self.session.run([self.output_name], {self.input_name: batch})[0]
        out = np.asarray(out)

        if out.shape[-1] == 6:          # ortho6d
            pitch, yaw, _roll = matrix_to_euler_deg(rotation_6d_to_matrix(out))
        elif out.shape[-1] == 3:        # already euler degrees [pitch, yaw, roll]
            pitch, yaw = out[:, 0], out[:, 1]
        else:
            raise ValueError(
                f"Unexpected head-pose output shape {out.shape}; expected (M,6) "
                f"ortho6d or (M,3) euler. Confirm the exported graph.")

        for k, i in enumerate(idx_valid):
            results[i] = {"H": deviation(float(yaw[k]), float(pitch[k]), self.cfg)}
        return results
