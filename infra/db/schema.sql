-- EyeQ schema (Phase A skeleton).
-- Replace with the full schema.sql already drafted; keep the FR6 shape.

CREATE TABLE IF NOT EXISTS halls (
    hall_id      TEXT PRIMARY KEY,
    name         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seat_layouts (
    layout_id    TEXT PRIMARY KEY,
    hall_id      TEXT NOT NULL REFERENCES halls(hall_id),
    calibrated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seat_regions (
    layout_id    TEXT NOT NULL REFERENCES seat_layouts(layout_id),
    seat_id      TEXT NOT NULL,
    x1 INT, y1 INT, x2 INT, y2 INT,
    PRIMARY KEY (layout_id, seat_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    hall_id      TEXT NOT NULL REFERENCES halls(hall_id),
    layout_id    TEXT NOT NULL REFERENCES seat_layouts(layout_id),
    session_salt TEXT NOT NULL,          -- salted seat randomisation
    started_at   TIMESTAMPTZ NOT NULL,
    ended_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id     TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(session_id),
    seat_id      TEXT NOT NULL,
    ts           TIMESTAMPTZ NOT NULL,
    cri          REAL NOT NULL,
    clip_ref     TEXT
);

CREATE TABLE IF NOT EXISTS adjudications (
    alert_id     TEXT PRIMARY KEY REFERENCES alerts(alert_id),
    decision     TEXT NOT NULL CHECK (decision IN ('confirmed','dismissed')),
    decided_by   TEXT NOT NULL,
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- History is DERIVED from confirmed adjudications, never written directly.
-- If an adjudication is later reversed, the count self-corrects.
CREATE OR REPLACE VIEW student_history AS
SELECT a.seat_id, a.session_id, COUNT(*) AS confirmed_incidents
FROM alerts a
JOIN adjudications j ON j.alert_id = a.alert_id
WHERE j.decision = 'confirmed'
GROUP BY a.seat_id, a.session_id;
