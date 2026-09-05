# ADR-0001 — Behavioral history is disclosed only after adjudication

**Status:** Accepted

Supersedes the "Proposed — awaiting supervisor confirmation" state of this ADR.
Closes roadmap open question A7.1.

## Context

FR6 in `EyeQ_Requirements_FR_NFR.md` contains an internal contradiction. Its
third clause states that the system "must attach a student's historical risk
profile to an alert payload for Controller reference" — which places the record
in front of the reviewer at decision time. The committee note directly beneath
that clause asks whether the profile should surface **before** clip review (to
speed triage) or **after** an independent review (to avoid biasing the human
reviewer), and records the latter as the working default.

So the conflict is not between two documents. It is inside FR6 itself: the
clause says one thing, the note attached to it says the opposite, and the note
holds the default.

NFR6 (usability) compounds this, listing "historical status" among the fields a
Controller should read at a glance — consistent with the clause, not the note.

Proposal §1.1 identifies "Proctor Bias & Personal Familiarity" as a problem the
platform exists to solve.

## Decision

Behavioral history is withheld from the Controller until an independent
adjudication has been recorded for that alert.

Sequence: evidence clip → independent decision → history disclosed.

## Rationale

- A reviewer shown a prior record before judging the current clip is anchored by
  it. That is the same bias the platform was built to remove, in a form that
  looks objective and is therefore harder to challenge.
- The record is evidence of what happened before, not evidence of what is
  happening now. In a disciplinary context this is the difference between
  judging conduct and judging a person's file.
- Asymmetry of cost: building history-sealed and relaxing it later is a
  one-file change. The reverse means unwinding the constraint from the API, the
  client, the tests, and the diagrams.

## Consequences

- `AlertPayload` carries no history field.
- `routers/alerts.py` does not import `routers/history.py` — a structural
  boundary, verified by test.
- `GET /alerts/{alert_id}/history` returns 403 until an adjudication exists.
- The Controller UI fires the history request only after adjudication returns 200.
- `services/backend/tests/test_fr6.py` fails the build if any of this is broken.
- **FR6 clause 3 and NFR6 should be amended** in the requirements document to
  match. Until then, this ADR is the authority and the discrepancy is known.
- The activity diagram "Cheating Alert-to-Adjudication Flow" already reflects
  this ("Reveal behavioral history — post-decision only") and needs no change.

## Related

- ADR-0003 — history must not enter CRI computation.
