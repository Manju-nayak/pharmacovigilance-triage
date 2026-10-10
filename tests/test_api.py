
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
        response = client.post(
            "/reports",
            json=synthetic_report(),
        )

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

    saved = json.loads(
        files[0].read_text(encoding="utf-8")
    )
    assert saved["status"] == "rejected"
    assert saved["body"]["patient_age"] == -5


def test_evidence_search_returns_results():
    with TestClient(app) as client:
        response = client.get(
            "/evidence/search",
            params={
                "q": "carbamazepine serious skin reactions",
                "top_k": 5,
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["result_count"] > 0
    assert len(body["results"]) <= 5
    assert body["request_id"]

    first = body["results"][0]
    assert first["source"]
    assert first["page"] >= 1
    assert first["text"]
    assert "keyword_overlap_score" in first


def test_evidence_search_finds_ocr_notice():
    with TestClient(app) as client:
        response = client.get(
            "/evidence/search",
            params={
                "q": (
                    "carbamazepine life threatening skin reactions"
                ),
                "top_k": 10,
            },
        )

    assert response.status_code == 200

    results = response.json()["results"]

    assert any(
        result["source"] == "carbamazepine_cdsco_safety_notice.pdf"
        and result["extraction_method"] == "ocr"
        for result in results
    )


def test_evidence_search_rejects_short_query():
    with TestClient(app) as client:
        response = client.get(
            "/evidence/search",
            params={"q": "a"},
        )

    assert response.status_code == 422


def test_evidence_search_rejects_invalid_top_k():
    with TestClient(app) as client:
        response = client.get(
            "/evidence/search",
            params={
                "q": "carbamazepine",
                "top_k": 0,
            },
        )

    assert response.status_code == 422

def test_triage_endpoint_flags_skin_peeling():
    report = synthetic_report()
    report["reaction_description"] = (
        "Severe skin peeling reported after starting the medicine."
    )
    report["hospitalization"] = True

    with TestClient(app) as client:
        response = client.post("/triage", json=report)

    assert response.status_code == 200

    body = response.json()
    triage = body["triage"]

    assert body["case_id"] == "SYN-001"
    assert triage["priority"] == "urgent_human_review"
    assert triage["causality_assessed"] is False
    assert triage["requires_qualified_review"] is True

    signal_names = {
        signal["signal"] for signal in triage["signals"]
    }
    assert "reported_hospitalization" in signal_names
    assert "potentially_serious_reaction_text" in signal_names


def test_triage_endpoint_rejects_inconsistent_death_fields():
    report = synthetic_report()
    report["death"] = True
    report["outcome"] = "recovering"

    with TestClient(app) as client:
        response = client.post("/triage", json=report)

    assert response.status_code == 422
    assert response.json()["status"] == "rejected"


def test_triage_endpoint_flags_reported_death():
    report = synthetic_report()
    report["death"] = True
    report["outcome"] = "death"

    with TestClient(app) as client:
        response = client.post("/triage", json=report)

    assert response.status_code == 200

    triage = response.json()["triage"]
    assert triage["priority"] == "urgent_human_review"
    assert triage["causality_assessed"] is False

    signal_names = {
        signal["signal"] for signal in triage["signals"]
    }
    assert "reported_death" in signal_names
