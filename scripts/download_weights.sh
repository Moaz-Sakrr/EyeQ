#!/usr/bin/env bash
# Fetch model weights. Weights are NOT tracked in git.
set -euo pipefail
DEST="${1:-weights}"
mkdir -p "$DEST"
echo "Weights directory: $DEST"
echo "TODO: add release URLs once A2.1 produces the first trained detector."
