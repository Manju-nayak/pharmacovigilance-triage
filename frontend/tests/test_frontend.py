import json
import py_compile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AdverseEventReport
from frontend.config import SAMPLE_PRESETS, FRONTEND_DIR
from frontend.utils.ui_components import (
    render_priority_badge,
    render_status_badge,
    highlight_matched_terms,
)
from frontend.utils.session import (
    save_persistent_history,
    load_persistent_history,
    load_quarantined_reports,
)


def test_frontend_files_compile():
    """Ensure all Streamlit page scripts compile without Python syntax errors."""
    page_files = [
        FRONTEND_DIR / "app.py",
        FRONTEND_DIR / "config.py",
        FRONTEND_DIR / "api_client.py",
        FRONTEND_DIR / "utils" / "session.py",
        FRONTEND_DIR / "utils" / "ui_components.py",
        FRONTEND_DIR / "pages" / "1_📥_Submit_Report.py",
        FRONTEND_DIR / "pages" / "2_📊_Triage_&_Assessments.py",
        FRONTEND_DIR / "pages" / "3_📋_Report_History.py",
        FRONTEND_DIR / "pages" / "4_🔍_Evidence_Explorer.py",
        FRONTEND_DIR / "pages" / "5_⚙️_System_Health.py",
    ]

    for pf in page_files:
        assert pf.exists(), f"Expected file {pf} does not exist"
        compiled = py_compile.compile(str(pf), doraise=True)
        assert compiled is not None, f"Failed to compile {pf}"


def test_sample_presets_adhere_to_backend_schema():
    """Verify every scenario preset in frontend/config.py strictly satisfies AdverseEventReport schema."""
    for name, data in SAMPLE_PRESETS.items():
        validated = AdverseEventReport.model_validate(data)
        assert validated.case_id == data["case_id"]
        assert validated.drug_name == data["drug_name"]
        # Verify death consistency rule
        if validated.death:
            assert validated.outcome.value == "death"
        if validated.outcome.value == "death":
            assert validated.death is True


def test_ui_components_render():
    """Verify UI badge and highlighter helpers."""
    p_urgent = render_priority_badge("urgent_human_review")
    assert "badge-urgent" in p_urgent
    assert "URGENT HUMAN REVIEW" in p_urgent

    p_routine = render_priority_badge("routine_human_review")
    assert "badge-routine" in p_routine
    assert "ROUTINE HUMAN REVIEW" in p_routine

    s_completed = render_status_badge("completed")
    assert "badge-completed" in s_completed

    s_failed = render_status_badge("failed")
    assert "badge-failed" in s_failed

    highlighted = highlight_matched_terms(
        "Patient developed severe skin peeling and blistering.",
        ["skin peeling", "blistering"],
    )
    assert '<span class="highlight-danger">skin peeling</span>' in highlighted


def test_persistence_helpers(tmp_path, monkeypatch):
    """Test saving and loading persistent history."""
    test_hist_file = tmp_path / "test_history.json"
    monkeypatch.setattr("frontend.utils.session.HISTORY_FILE", test_hist_file)
    monkeypatch.setattr("frontend.utils.session.DATA_DIR", tmp_path)

    sample_record = [{
        "case_id": "TEST-001",
        "status": "completed",
        "priority": "urgent_human_review",
    }]

    save_persistent_history(sample_record)
    loaded = load_persistent_history()
    assert len(loaded) == 1
    assert loaded[0]["case_id"] == "TEST-001"


def test_api_integration_endpoints():
    """Test live API endpoints using TestClient."""
    with TestClient(app) as tc:
        # 1. Health
        h_res = tc.get("/health")
        assert h_res.status_code == 200
        assert h_res.json()["status"] == "ok"

        # 2. Metrics
        m_res = tc.get("/metrics")
        assert m_res.status_code == 200
        assert "accepted_reports" in m_res.json()

        # 3. Synchronous Workflow
        preset = SAMPLE_PRESETS["Preset 1: Carbamazepine SJS/TEN (Urgent Review)"]
        wf_res = tc.post("/workflow/run", json=preset)
        assert wf_res.status_code == 200
        wf_data = wf_res.json()
        assert wf_data["workflow_status"] == "verification_completed"
        assert wf_data["triage_result"]["priority"] == "urgent_human_review"
        assert len(wf_data["triage_result"]["signals"]) > 0
        assert len(wf_data["evidence_result"]["evidence"]) > 0
        assert wf_data["verification_result"]["verified"] is True

        # 4. Asynchronous Queue
        rep_res = tc.post("/reports", json=preset)
        assert rep_res.status_code == 202
        run_id = rep_res.json()["run_id"]
        assert run_id is not None

        # 5. Get Run Status
        run_res = tc.get(f"/runs/{run_id}")
        assert run_res.status_code == 200
        assert run_res.json()["status"] in ("queued", "running", "completed")

        # 6. Evidence Search
        ev_res = tc.get("/evidence/search", params={"q": "carbamazepine", "top_k": 3})
        assert ev_res.status_code == 200
        assert len(ev_res.json()["results"]) > 0

        # 7. Fast Triage
        tri_res = tc.post("/triage", json=preset)
        assert tri_res.status_code == 200
        assert tri_res.json()["triage"]["priority"] == "urgent_human_review"
