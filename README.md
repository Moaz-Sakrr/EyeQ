# EyeQ

Exam-integrity and engagement analytics for university lecture halls.
Two modules: **CRI** (Cheating Risk Index) and **SFS** (Student Focus Score).

---

## Why one repo

Most changes here cross layers at once. Adding a field to the alert payload
touches CV, backend, and Flutter together — that is one atomic PR in a
monorepo, and three drifting PRs in three repos, one of which gets forgotten.

---

## Layout

```
contracts/          the shared data contract — read the rule below
services/
  cv-engine/        perception models + seat resolver + CRI fusion
  backend/          FastAPI, WebSocket, evidence, RBAC
  frontend/         Flutter client
infra/db/           schema
docs/decisions/     ADRs — why things are the way they are
data/               links only. never files.
```

---

## Run it

```bash
docker compose up --build
curl localhost:8000/health
# mock alerts stream on ws://localhost:8000/ws/session/demo
```

Tests:

```bash
PYTHONPATH=services/cv-engine/src:contracts pytest services/cv-engine/tests -q
PYTHONPATH=services/backend/src:contracts   pytest services/backend/tests   -q
```

---

## Cameras

Wall-mounted and elevated — one on the front wall, one on the rear wall behind
the tiered seating. Angled, **not** ceiling-mounted and not top-down.

The two views are not redundant. The front camera sees faces, and is the source
for head pose, gaze, and EAR/MAR. The rear camera sees the backs of heads, and
is the source for posture and object signals. They contribute different
channels, not the same channel twice.

Two open items: the cameras are **not yet installed**, and the count is
undecided (2 vs 4). The hall's existing CCTV will most likely not be used — it
is angled for general security rather than vision analysis, at insufficient
quality. Nothing in this repo should hardcode a camera count or hall geometry.

---

## The stub strategy

Every perception model ships as a stub returning plausible random values.
The pipeline therefore runs end-to-end from day one, and backend and Flutter
work is unblocked before a single model is trained. Task A2.6 replaces the
stubs one at a time, each in its own PR. **Do not delete a stub — swap it.**

The gaze stub returns `None` for a fraction of seats on purpose, so the
missing-signal path in fusion is exercised continuously rather than discovered
late.

---

## Contract rule

> Any change under `contracts/` goes in its own PR, reviewed by one person from
> each affected layer, and merged **before** the code that depends on it.

Two minutes of process; saves the afternoon spent hunting a silently renamed
field.

---

## FR6

Behavioral history is withheld from the reviewer until an independent decision
is recorded. This is a structural boundary, not a note:

- `routers/alerts.py` does not import history.
- `routers/history.py` returns 403 until an adjudication exists.
- `services/backend/tests/test_fr6.py` fails the build if either is broken.

History also never enters the CRI computation — no per-student risk priors, in
any form. See `docs/decisions/ADR-0001` and `ADR-0003`.

---

## Seat assignment

EyeQ imports the university's hall-assignment sheet, generates a randomized
student→seat assignment per hall using a stored `session_salt`, and exports a
sheet distributed the day before the exam. Physical seats carry permanent
`seat_id` stickers. See `docs/decisions/ADR-0004`.

---

## Branching

`main` is protected: PR + one approval. Branches live **three days maximum** —
longer ones produce the merge conflicts that sink student projects. Small PRs,
daily.

**Done** = code + test + contract updated if changed + CI green + reviewed.

---

## Ownership

| Area | Owner |
|---|---|
| `cv-engine/detector`, `fusion`, `seat_resolver` | CV lead |
| `cv-engine/headpose`, `gaze` | CV #2 |
| `backend/`, `infra/db` | Backend |
| `frontend/features/controller` | Flutter #1 |
| `frontend/features/professor`, `admin` | Flutter #2 |

Weekly: 15-minute standup Monday; **integration session Thursday** — everyone
runs `docker compose up` and confirms the system still works end to end. That
session is what catches a broken contract in a day instead of a fortnight.

---

## Open questions blocking design

| Ref | Question | Owner |
|---|---|---|
| B2.4 | Camera count, mounting positions, procurement approval | University / supervisor |
| B2.5 | Does the exam control office accept EyeQ as the source of seat assignment? | Exam control office |
| C1.1 | LLM deployment — external API vs internally hosted | Supervisor / university |

Closed: **A7.1** (FR6 — see ADR-0001), **B2.3** (`roster_seat_no` — see ADR-0004).
