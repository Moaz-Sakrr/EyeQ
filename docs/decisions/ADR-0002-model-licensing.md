# ADR-0002 — Detector licensing

**Status:** Accepted

## Context
Ultralytics YOLO ships under AGPL-3.0, which restricts closed-source
distribution. Some validation datasets (MPIIFaceGaze, CEW) are CC BY-NC-SA
or otherwise non-commercial.

## Decision
- **RT-DETR (Apache 2.0)** is the product-path detector.
- YOLO may be used for rapid experiments and benchmarking only.
- NC-licensed datasets are used for **validation**, never for fine-tuning
  weights that would ship in a product build.

## Consequences
- `data/README.md` records the licence of every source.
- Any model trained on an NC dataset is tagged `research-only` and must not be
  exported into the deployment image.
