# CLAUDE.md

Context for Claude Code working in this repository.
Repo: https://github.com/Moaz-Sakrr/EyeQ

Read this before proposing changes. Several constraints here are not
inferable from the code, and one of them (FR6) is the project's central
contribution rather than a detail.

---

## What EyeQ is

A graduation project at Egyptian Russian University: an exam-integrity and
engagement-analytics platform for university lecture halls.

Two modules:

- **CRI — Cheating Risk Index.** Real-time exam integrity monitoring.
- **SFS — Student Focus Score.** Lecture engagement analytics.

Four roles: **Admin**, **Controller**, **Professor**, **AI Vision Engine**.

Team of five: one CV lead (repo owner), a second CV engineer, one backend
(FastAPI), two Flutter.

---

## FR6 — the constraint that shapes the architecture

**Behavioral history is withheld from the Controller until an independent
adjudication has been recorded.**

The platform exists to remove proctor bias (Proposal §1.1, "Proctor Bias &
Personal Familiarity"). Showing a reviewer the student's prior record before
they judge the current clip would reintroduce that bias in a form that looks
objective. So the sequencing is: evidence → independent decision → history.

**Status: decided.** The supervisor-facing open question A7.1 is closed in
favour of post-decision disclosure. `docs/decisions/ADR-0001` records it.

How it is enforced, structurally rather than by convention:

- `AlertPayload` has no history field. Adding one breaks FR6.
- `routers/alerts.py` does not import `routers/history.py`.
- `GET /alerts/{alert_id}/history` returns **403** until an adjudication exists.
- `services/backend/tests/test_fr6.py` fails the build if any of the above breaks.

### Two things FR6 rules out

**1. History must never enter the CRI computation.** Not as a prior, not as a
weight, not as a threshold adjustment. A student with a confirmed incident does
not get a higher baseline risk score.

This is prohibited by two requirements: **NFR10** (Must-have) states that risk
profile enrichment must not alter detection sensitivity for any individual
student, and FR6's own third clause states history is attached for reference
"without altering the underlying CRI computation itself".

The failure mode is a positive feedback loop: higher baseline → more alerts →
more reviews → more confirmations → higher baseline. The system would end up
confirming its own suspicions. See `ADR-0003`.

**2. No face recognition, ever.** Identity comes from seat geometry (FR3), and
NFR10 forbids biometric identification. Do not propose face recognition,
ByteTrack, or cross-frame re-identification — they were deliberately removed.

---

## The integration contract

`contracts/schemas/seat_observation.py` is the join point. Four perception
models write into one `SeatObservation` per seat per frame, keyed by `seat_id`.
The models never see each other; they meet here.

```python
SeatObservation(
    seat_id, frame_ts,
    H,          # head-pose deviation      [0,1] | None
    G,          # gaze deviation           [0,1] | None
    O,          # unauthorized object      [0,1] | None
    B,          # behavior class           [0,1] | None
    visibility, # detection quality        [0,1]
    bbox,       # xyxy, evidence/debug only
)
```

> **Any change under `contracts/` goes in its own PR, reviewed by one person
> from each affected layer, and merged before the code that depends on it.**

### Three invariants in CRI fusion

Encoded in `services/cv-engine/tests/test_fusion.py`. If a change breaks one of
these tests, the change is wrong — not the test.

1. **No single signal raises an alert.** Corroboration across channels is required.
2. **A missing signal is not a clean signal.** When a channel is `None`, its
   weight is redistributed across the channels that are present. It is never
   read as zero risk.
3. **Low visibility is gated, not scored.** Occlusion means *unknown*, so the
   observation is excluded rather than scored as normal behaviour.

Weights (`wH, wG, wO, wT`) are **calibrated** — grid search or logistic
regression on labelled hall footage. Never learned by backpropagation, never
hardcoded in logic. They live in `CRIConfig`.

---

## Seat identity

Two layers, since the third was removed (see below):

1. **Calibration** — hall geometry, mapped once per hall. Seat regions drawn on
   the camera image. Independent of any exam.
2. **`student_id`** — per-session assignment.

**Assignment flow (ADR-0004):** the university's official seating sheet assigns
students to halls. EyeQ imports it, then generates a randomized student→seat
assignment within each hall using a stored `session_salt`. EyeQ exports the
resulting sheet, which is distributed to students the day before the exam.
Physical seats carry permanent stickers with their `seat_id` (`A-5`, etc.),
applied once.

This closes former open question B2.3: EyeQ generates the seat numbering rather
than matching an administrative scheme, so no `roster_seat_no` layer is needed.

Salted randomization prevents students predicting their seat across repeated
exams of the same course — a real vulnerability of any deterministic,
ID-ascending assignment. Note the residual, accepted trade-off: distributing the
sheet a day ahead does not prevent coordination for that specific exam, only
prediction of future ones.

**An empty seat region is an absence, not an anomaly.**

---

## Cameras — read this before assuming anything

- **Not ceiling-mounted.** Wall-mounted and elevated: one on the front wall,
  one on the rear wall behind the tiered seating. Angled, not top-down. Any
  code comment or doc saying "ceiling" is stale and should be corrected.
- **Not yet installed.** The hall's existing CCTV will most likely *not* be
  used — low quality, angled for general security (lost property), not for
  vision analysis. The project needs purpose-installed cameras, which is an
  unresolved procurement and approval question.
- **Count is undecided** (2 vs 4). Do not hardcode a camera count. Signals may
  eventually need per-camera attribution.

Front and rear cameras are **not redundant**: the front sees faces (usable for
head pose, gaze, EAR/MAR), the rear sees the backs of heads (usable for body
posture and objects). They contribute different signals, not the same signal
twice.

**Gaze is the fragile channel.** It needs clear eye pixels, which distance and
camera angle destroy first. Never write code that assumes `G` is present.

---

## Working with stubs

Every perception model currently ships as a stub returning plausible random
values, so the pipeline runs end to end before any model exists.

- **Replace stubs, never delete them.** They are needed for CI, for machines
  without a GPU, and for isolating which model caused a regression.
- A real model must return the **exact same keys** as its stub.
- The gaze stub returns `None` for ~25% of seats **on purpose**, so the
  missing-signal path is exercised continuously rather than discovered late.
  Keep that behaviour reachable in the real implementation.
- Swapping in a trained model is a three-file change: the new inference class,
  one line in `pipeline.py`, and the weights URL in `scripts/download_weights.sh`.

### Current state

| Component | State |
|---|---|
| Head detector | Stub. Trained weights exist (below) but are **not yet wired in**. |
| Head pose | Stub. Target: 6DRepNet, test pretrained weights before retraining. |
| Behavior + objects | Stub. Target: merged single-backbone detector. |
| Gaze | Stub. Target: L2CS-Net, no training needed. |
| CRI engine | Implemented, placeholder weights. |
| Backend | FastAPI running, in-memory store, mock WebSocket alerts, FR6 tests pass. |
| Flutter | Placeholder directory only. |

**Head detector, first trained model** — YOLOv8n on SCUT-HEAD PartA,
`imgsz=960`, 100 epochs: mAP@50 **0.960**, mAP@50-95 **0.466**, precision
**0.941**, recall **0.927**.

Recall matters more than precision here: an undetected head produces no
`SeatObservation` at all — a silent gap. A false positive is filtered
downstream by seat assignment. The low mAP@50-95 is expected for small objects
and is not a defect; seat association needs approximate location, not
pixel-exact boxes.

These figures are measured on SCUT-HEAD's own test split — classroom footage,
but not this hall, and not from cameras that exist yet. The domain gap is
unmeasured. Do not present these numbers as expected in-hall performance.

---

## Licensing — affects what may ship

- **Ultralytics YOLO is AGPL-3.0.** Acceptable for training and experiments.
  The deployed backend must not import `ultralytics` — run exported ONNX via
  `onnxruntime` instead. **RT-DETR (Apache 2.0)** is the product path.
- **SCUT-HEAD is academic-research-use only** per its authors, despite a
  Roboflow mirror mislabelling it CC BY 4.0. Cite the official source.
- **MPIIFaceGaze is CC BY-NC-SA** — validation only, never shipped weights.
- Roboflow Gaze API was deprecated mid-2026. Do not propose it.

**Weights never enter Git.** They live in GitHub Releases, fetched by
`scripts/download_weights.sh`.

### ONNX export note

YOLOv8 ONNX export does **not** include NMS. The exported graph returns raw
candidates `(1, 5, N)`. Backend inference code must implement confidence
filtering, NMS, and coordinate rescaling itself. This is the most commonly
missed step when replacing the detector stub.

---

## Conventions

- Python 3.11. Type hints on public functions. Dataclasses over dicts for
  anything crossing a module boundary.
- New behaviour needs a test in the same PR.
- Branches live three days maximum. Several small PRs over one large one.
- Comments explain *why*, not *what*. Do not narrate the code.
- The binding constraint is **throughput**, not accuracy: four models across
  ~70 seats in real time, on shared GPU. Prefer the change that reduces
  inference cost.

---

## Rules for Claude Code

**Do not resolve open questions in code.** The table below lists decisions that
belong to a supervisor or an administrative office. If a task depends on one,
say so and stop — do not pick an answer and proceed. Implementing a guess here
is worse than not implementing at all, because it looks decided.

**Do not modify `contracts/` as part of another change.** Contract changes are
their own PR, reviewed across layers, merged first. If a task appears to require
a contract change, raise it rather than bundling it.

**Do not delete a stub.** Replace it, preserving its return keys.

**Do not weaken a test to make a change pass.** `test_fr6.py` and
`test_fusion.py` encode architectural constraints, not implementation details.
A change that breaks them is the thing that is wrong.

**Do not add `ultralytics` to backend or deployment dependencies.** Training
code only.

**Do not introduce history into CRI, or any form of per-student risk priors.**
See the FR6 section above; this is prohibited by NFR10.

**Do not hardcode camera count, hall dimensions, or seat counts.** All three are
undecided or hall-specific.

**Flag stale assumptions rather than propagating them.** If you encounter
"ceiling camera" or "existing CCTV" in comments or docs, note it — those are
known-stale and being corrected.

**When a task is blocked on physical-world information** — hall measurements,
camera specs, real footage — say what specifically is needed rather than
substituting a plausible default.

---

## Open questions — do not resolve these in code

| Ref | Question | Owner | Status |
|---|---|---|---|
| B2.4 | Camera count and mounting positions (2 vs 4); procurement and approval for purpose-installed cameras | University / supervisor | Open |
| B2.5 | Does the exam control office accept EyeQ as the source of seat assignment? | Exam control office | Open — assumed yes in ADR-0004 |
| C1.1 | LLM deployment: external API vs internally hosted; exactly what leaves the institution in the prompt | Supervisor / university | Leaning external API — see below |

### C1.1 detail

FR8 (Nice-to-have) sends aggregated engagement trends to an LLM for
natural-language pedagogy guidance. Current intent is an **external API**.

This is in tension with **NFR4** (Must-have), which minimizes the stored
personal-data footprint "by design, not by policy alone". Aggregate
region-level statistics are a much weaker exposure than imagery or identities,
but the boundary should be explicit: the prompt must carry no `seat_id`, no
`student_id`, and no per-student values — region-level aggregates only.

Needs an ADR before implementation.

---

## Where things live

```
contracts/          shared data contract — see the rule above
services/
  cv-engine/        perception models, seat resolver, CRI fusion
  backend/          FastAPI, WebSocket, evidence, RBAC
  frontend/         Flutter client
infra/db/           schema
docs/decisions/     ADRs — why things are the way they are
data/               links only, never files
scripts/            weight download
```

## Running it

```bash
docker compose up --build
curl localhost:8000/health

PYTHONPATH=services/cv-engine/src:contracts pytest services/cv-engine/tests -q
PYTHONPATH=services/backend/src:contracts   pytest services/backend/tests   -q
```
