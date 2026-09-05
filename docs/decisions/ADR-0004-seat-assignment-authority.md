# ADR-0004 — EyeQ generates seat assignment; seats are physically labelled

**Status:** Accepted (pending administrative confirmation — see Consequences)

Closes roadmap open question B2.3.

## Context

Associating a detected head with a student requires a stable mapping from
physical seat to student identity. The original design assumed three layers:
hall calibration → `roster_seat_no` (the exam control office's administrative
numbering) → `student_id`. The middle layer existed to match whatever numbering
scheme the office already used, which meant that scheme had to be discovered and
mirrored exactly. A mismatch would attribute an alert to the wrong student —
the most damaging failure the system can produce.

Separately, the university's existing process distributes an official sheet
before each exam assigning students to **halls**, not to individual seats. Seat
choice within a hall is effectively free.

## Decision

EyeQ generates the seat assignment rather than mirroring an external scheme.

1. The official hall-assignment sheet is imported into EyeQ.
2. For each hall, EyeQ assigns students to calibrated seat positions using
   salted per-session randomization, with the `session_salt` stored.
3. EyeQ exports a new sheet listing each student with their `seat_id` (`A-5`).
4. That sheet is distributed to students the day before the exam, through the
   existing distribution channel.
5. Physical seats carry permanent stickers showing their `seat_id`, applied once
   per hall.

The `roster_seat_no` layer is removed. Identity is two layers: calibration →
`student_id`.

## Rationale

- Generating the numbering removes the need to discover and match an
  administrative scheme, eliminating a whole class of misattribution risk.
- Randomized within-hall assignment is a genuine improvement over the status
  quo, not merely a technical requirement: it prevents students coordinating
  adjacent seating in advance, and prevents prediction of seat position across
  repeated exams of the same course. Deterministic ID-ascending assignment has
  exactly this vulnerability.
- Stickers are a one-time cost per hall and impose no per-exam operational
  burden, unlike name cards placed before each session.
- Day-before distribution reuses an existing process; it introduces no new
  operational dependency on EyeQ being available on exam day.

## Accepted trade-off

Distributing the sheet a day in advance means students know their seat before
the exam. Randomization therefore prevents **prediction** across future exams
but does not prevent **coordination** for the specific exam. This is accepted as
a deliberate choice, not an oversight; closing it fully would require
distribution on exam morning, which is an administrative decision rather than a
technical one.

## Consequences

- **Requires administrative confirmation** that the exam control office accepts
  EyeQ as the source of seat assignment. This is a delegation of authority, not
  a technical decision. Tracked as open question B2.5. If refused, this ADR is
  reversed and `roster_seat_no` returns.
- The seating-sheet import path must handle Arabic names and committee
  structure, and must include a manual Admin review step confirming counts and
  names before assignment is generated.
- The system must validate that calibrated seat count ≥ student count for the
  hall, and fail clearly rather than assigning to non-existent seats.
- `session_salt` must be persisted so assignments are reproducible if disputed.
- The exported sheet must be generated ahead of the exam and exported as a file,
  so exam-day operation does not depend on EyeQ being available.
- The student↔seat table is the most sensitive data in the system: Admin access
  only. Professors have no access to individual identity under FR9.
- A late change (a student moved between halls, a seat added) requires a
  regeneration path that records the amendment rather than silently replacing
  the original.
- **Seat occupancy must be verified at session start.** A student sitting in the
  wrong seat breaks the identity chain silently. The "Verify Seat Occupancy" use
  case covers this and is now load-bearing rather than optional — without it the
  assignment is an assumption rather than a fact.
