"""FR6 enforcement tests.

An architectural constraint that is not protected by a test is just a good
intention. These tests are what stop any team member -- including the author,
four months from now -- from breaking FR6 by accident.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/backend/src"))

from eyeq_api.main import app  # noqa: E402
from eyeq_api.ws.channel import _mock_alert  # noqa: E402
from eyeq_api.store import STORE  # noqa: E402

client = TestClient(app)

FORBIDDEN_KEYS = {
    "history", "prior_incidents", "risk_profile",
    "behavioral_history", "past_incidents", "confirmed_incidents",
}


@pytest.fixture(autouse=True)
def clean():
    STORE.alerts.clear()
    STORE.adjudications.clear()
    STORE.history.clear()


def test_alert_payload_contains_no_history():
    alert = _mock_alert("s1")
    assert FORBIDDEN_KEYS.isdisjoint(alert.keys())


def test_alert_list_contains_no_history():
    _mock_alert("s1")
    body = client.get("/sessions/s1/alerts").json()
    for alert in body:
        assert FORBIDDEN_KEYS.isdisjoint(alert.keys())


def test_history_blocked_before_adjudication():
    a = _mock_alert("s1")
    r = client.get(f"/alerts/{a['alert_id']}/history")
    assert r.status_code == 403


def test_history_released_after_adjudication():
    a = _mock_alert("s1")
    client.post(f"/alerts/{a['alert_id']}/adjudicate",
                json={"decision": "confirmed"})
    r = client.get(f"/alerts/{a['alert_id']}/history")
    assert r.status_code == 200
    assert r.json()["confirmed_incidents"] == 1


def test_dismissed_alert_does_not_increment_history():
    a = _mock_alert("s1")
    client.post(f"/alerts/{a['alert_id']}/adjudicate",
                json={"decision": "dismissed"})
    r = client.get(f"/alerts/{a['alert_id']}/history")
    assert r.json()["confirmed_incidents"] == 0


def test_alerts_router_does_not_import_history():
    """Structural guard: the FR6 boundary must stay visible in the imports."""
    src = (ROOT / "services/backend/src/eyeq_api/routers/alerts.py").read_text()
    assert "import history" not in src
    assert "from .history" not in src
