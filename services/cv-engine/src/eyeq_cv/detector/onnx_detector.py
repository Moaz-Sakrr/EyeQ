"""Head detector — ONNX runtime (task A2.1).

Runtime replacement for HeadDetectorStub. Same contract: returns xyxy boxes +
confidence, nothing else. The stub is kept, not deleted (see detector/stub.py).

Why onnxruntime and not ultralytics: the shipped cv-engine must not depend on
AGPL ultralytics (ADR-0002). The model is exported to ONNX and run here.

Why the post-processing lives here: YOLOv8 ONNX export does NOT include NMS. The
graph returns raw candidates shaped (1, 5, N) — the 5 rows are
[cx, cy, w, h, head_score] in letterboxed-input pixel coords. Confidence
filtering, NMS, and un-letterboxing back to original frame coordinates are ours
to do. This is the step most commonly missed when swapping the detector stub.

Heavy imports (onnxruntime, cv2, numpy) sit at module top on purpose: this module
is imported lazily by detector/factory.py only when the real detector is
selected, so the stub path never pulls them in.
"""
from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort


def letterbox(img: np.ndarray, imgsz: int = 960,
              color: tuple[int, int, int] = (114, 114, 114)):
    """Resize keeping aspect ratio, pad to a square imgsz.

    Returns (padded_img, ratio, (pad_x, pad_y)) so boxes can be mapped back:
    box_orig = (box_padded - pad) / ratio.
    """
    h, w = img.shape[:2]
    r = min(imgsz / h, imgsz / w)
    new_w, new_h = round(w * r), round(h * r)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    dw, dh = (imgsz - new_w) / 2, (imgsz - new_h) / 2
    top, bottom = round(dh - 0.1), round(dh + 0.1)
    left, right = round(dw - 0.1), round(dw + 0.1)
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                cv2.BORDER_CONSTANT, value=color)
    return padded, r, (left, top)


def xywh2xyxy(boxes: np.ndarray) -> np.ndarray:
    """(cx, cy, w, h) -> (x1, y1, x2, y2). Operates on an (N, 4) array."""
    out = np.empty_like(boxes)
    out[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    out[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    out[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
    out[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
    return out


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> list[int]:
    """Greedy IoU NMS. boxes: (N, 4) xyxy, scores: (N,). Returns kept indices."""
    if boxes.shape[0] == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(x1[i], x1[rest])
        yy1 = np.maximum(y1[i], y1[rest])
        xx2 = np.minimum(x2[i], x2[rest])
        yy2 = np.minimum(y2[i], y2[rest])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        iou = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[np.where(iou <= iou_thres)[0]]
    return keep


class HeadDetectorONNX:
    """Drop-in for HeadDetectorStub. Returns [{"bbox": (x1,y1,x2,y2), "conf": f}].

    conf_thres defaults low because recall matters more than precision here: an
    undetected head produces no SeatObservation at all (a silent gap), while a
    false positive is filtered downstream by seat assignment.
    """
    name = "head_detector"

    def __init__(self, weights_path: str, imgsz: int = 960,
                 conf_thres: float = 0.25, iou_thres: float = 0.5,
                 providers: list[str] | None = None):
        self.imgsz = imgsz
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.session = ort.InferenceSession(
            weights_path, providers=providers or ["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def warmup(self) -> None:
        self.infer(np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8))

    def infer(self, frame, crops=None) -> list[dict]:
        if frame is None:
            raise ValueError(
                "HeadDetectorONNX needs an image frame; the pipeline must supply "
                "one. (The stub ignores the frame; the real model cannot.)")

        padded, r, (pad_x, pad_y) = letterbox(frame, self.imgsz)
        blob = padded[:, :, ::-1].transpose(2, 0, 1)[None]  # BGR->RGB, HWC->CHW
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0

        out = self.session.run([self.output_name], {self.input_name: blob})[0]
        pred = np.squeeze(out, 0)          # (5, N) or (N, 5)
        if pred.shape[0] == 5:             # (5, N) -> (N, 5)
            pred = pred.T

        scores = pred[:, 4]
        mask = scores >= self.conf_thres
        pred, scores = pred[mask], scores[mask]
        if pred.shape[0] == 0:
            return []

        boxes = xywh2xyxy(pred[:, :4])
        keep = nms(boxes, scores, self.iou_thres)
        boxes, scores = boxes[keep], scores[keep]

        # Un-letterbox: undo padding, then the resize ratio.
        boxes[:, [0, 2]] -= pad_x
        boxes[:, [1, 3]] -= pad_y
        boxes /= r
        h0, w0 = frame.shape[:2]
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w0)
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h0)

        return [
            {"bbox": (int(x1), int(y1), int(x2), int(y2)), "conf": round(float(s), 3)}
            for (x1, y1, x2, y2), s in zip(boxes, scores)
        ]
