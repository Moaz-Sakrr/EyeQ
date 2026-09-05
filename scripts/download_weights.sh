#!/usr/bin/env bash
# Fetch model weights. Weights are NOT tracked in git.
set -euo pipefail
DEST="${1:-weights}"
mkdir -p "$DEST"
echo "Weights directory: $DEST"

# --- Head detector (task A2.1) ---------------------------------------------
# The cv-engine loads the real detector when EYEQ_DETECTOR_WEIGHTS points at an
# exported ONNX file; otherwise it falls back to the stub. Export is done via
# ultralytics (training-only dependency), NOT in the shipped service.
#
#   EYEQ_DETECTOR_WEIGHTS="$DEST/head_detector.onnx"
#
# TODO(A2.1): once the ONNX is uploaded to a GitHub Release, fetch it here, e.g.:
#   curl -fSL -o "$DEST/head_detector.onnx" \
#     "https://github.com/Moaz-Sakrr/EyeQ/releases/download/<tag>/head_detector.onnx"
echo "TODO: add head-detector ONNX release URL once uploaded (A2.1)."

# --- Head pose (task A2.2) --------------------------------------------------
# 6DRepNet exported to ONNX (ortho6d output). Loaded when EYEQ_HEADPOSE_WEIGHTS
# is set; otherwise the stub is used. Test the pretrained weights before any
# retraining (see CLAUDE.md A2.2).
#
#   EYEQ_HEADPOSE_WEIGHTS="$DEST/head_pose_6drepnet.onnx"
#
# TODO(A2.2): export 6DRepNet -> ONNX, confirm output layout ((M,6) ortho6d),
# upload to a GitHub Release, and fetch it here.
echo "TODO: add head-pose (6DRepNet) ONNX release URL once uploaded (A2.2)."
