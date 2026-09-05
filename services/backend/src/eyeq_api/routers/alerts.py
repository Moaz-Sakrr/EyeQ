"""Alert endpoints.

FR6 BOUNDARY: this module must never import or return behavioral history.
History lives in routers/history.py behind an adjudication gate.
"""
from fastapi import APIRouter, HTTPException

from ..store import STORE, Adjudication
import time

router = APIRouter()


@router.get("/sessions/{session_id}/alerts")
def list_alerts(session_id: str):
    return [a for a in STORE.alerts.values() if a["session_id"] == session_id]


@router.post("/alerts/{alert_id}/adjudicate")
def adjudicate(alert_id: str, body: dict):
    if alert_id not in STORE.alerts:
        raise HTTPException(404, "unknown alert")
    decision = body.get("decision")
    if decision not in ("confirmed", "dismissed"):
        raise HTTPException(422, "decision must be confirmed|dismissed")

    STORE.adjudications[alert_id] = Adjudication(alert_id, decision, time.time())

    # Only a CONFIRMED decision increments history. Dismissals never do.
    if decision == "confirmed":
        seat = STORE.alerts[alert_id]["seat_id"]
        STORE.history[seat] = STORE.history.get(seat, 0) + 1

    return {"alert_id": alert_id, "decision": decision}
