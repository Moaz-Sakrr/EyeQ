"""Behavioral history — FR6 gated.

The reviewer must reach an independent decision BEFORE prior conduct is
revealed, so that the judgement is not anchored by the record. This gate is
the mechanism; ADR-0001 is the rationale.
"""
from fastapi import APIRouter, HTTPException

from ..store import STORE

router = APIRouter()


@router.get("/alerts/{alert_id}/history")
def get_history(alert_id: str):
    if alert_id not in STORE.alerts:
        raise HTTPException(404, "unknown alert")

    if not STORE.is_adjudicated(alert_id):
        raise HTTPException(
            403,
            "FR6: behavioral history is unavailable until an adjudication "
            "has been recorded for this alert.",
        )

    seat = STORE.alerts[alert_id]["seat_id"]
    return {"seat_id": seat, "confirmed_incidents": STORE.history.get(seat, 0)}
