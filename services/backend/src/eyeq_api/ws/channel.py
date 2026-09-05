"""WebSocket channel with a MOCK alert generator.

This is the single most important file in Phase A: it lets the Flutter team
build the entire Controller dashboard before a single model is trained.
"""
from __future__ import annotations

import asyncio
import random
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..store import STORE

router = APIRouter()


def _mock_alert(session_id: str) -> dict:
    seat = f"R{random.randint(1,5)}C{random.randint(1,6)}"
    alert = {
        "alert_id": str(uuid.uuid4()),
        "session_id": session_id,
        "seat_id": seat,
        "timestamp": time.time(),
        "cri": round(random.uniform(0.66, 0.95), 3),
        "evidence_clip_ref": f"clips/{uuid.uuid4()}.mp4",
        "contributing": {
            "H": round(random.uniform(0.5, 0.95), 2),
            "O": round(random.uniform(0.4, 0.9), 2),
        },
        # NO history field. See ADR-0001 / test_fr6.py
    }
    STORE.alerts[alert["alert_id"]] = alert
    return alert


@router.websocket("/ws/session/{session_id}")
async def session_channel(ws: WebSocket, session_id: str):
    await ws.accept()
    try:
        while True:
            await asyncio.sleep(random.uniform(4, 10))
            await ws.send_json({"type": "alert.raised",
                                "data": _mock_alert(session_id)})
    except WebSocketDisconnect:
        return
