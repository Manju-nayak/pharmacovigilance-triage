
import json

from fastapi.testclient import TestClient

from app.main import app


def synthetic_report():
    return {
        "case_id": "SYN-001",
        "drug_name": "ExampleDrug",
        "reaction_description": (
            "Synthetic example of a reported skin reaction."
        ),
        "patient_age": 35,
        "reporter_type": "patient",
        "outcome": "recovering",
        "event_onset_days": 7,
        "hospitalization": True,
        "death": False,
    }


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_valid_report_is_accepted():
    with TestClient(app) as client:
        response = client.post("/reports", json=synthetic_report())

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["assessment_status"] == "not_started"


def test_invalid_age_is_quarantined(tmp_path, monkeypatch):
    monkeypatch.setenv("QUARANTINE_DIR", str(tmp_path))

    report = synthetic_report()
    report["patient_age"] = -5

    with TestClient(app) as client:
        response = client.post("/reports", json=report)
        metrics = client.get("/metrics").json()

    assert response.status_code == 422
    assert response.json()["status"] == "rejected"
    assert metrics["agent_runs_started"] == 0

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1

    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert saved["status"] == "rejected"
    assert saved["body"]["patient_age"] == -5
    