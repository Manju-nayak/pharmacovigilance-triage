import subprocess
import sys
import time
import requests

from frontend.api_client import APIClient
from frontend.config import SAMPLE_PRESETS


def test_live_server_full_integration():
    """
    Launch a live uvicorn backend server on port 8008,
    execute real HTTP requests using APIClient, and verify all responses.
    """
    port = 8008
    base_url = f"http://127.0.0.1:{port}"

    # Start uvicorn as a subprocess
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    client = APIClient(base_url=base_url, timeout=10)

    try:
        # Wait for server to start
        server_ready = False
        for _ in range(20):
            try:
                r = requests.get(f"{base_url}/health", timeout=1)
                if r.status_code == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        assert server_ready, "Uvicorn server failed to start within 10 seconds"

        # 1. Test GET /health
        health = client.get_health()
        assert health["success"] is True
        assert health["data"]["status"] == "ok"
        assert health["data"]["version"] == "0.6.0"

        # 2. Test GET /metrics
        metrics = client.get_metrics()
        assert metrics["success"] is True
        assert "agent_runs_started" in metrics["data"]

        # 3. Test Synchronous Multi-Agent Workflow POST /workflow/run
        preset = SAMPLE_PRESETS["Preset 1: Carbamazepine SJS/TEN (Urgent Review)"]
        wf = client.run_workflow_sync(preset)
        assert wf["success"] is True
        wf_data = wf["data"]
        assert wf_data["workflow_status"] == "verification_completed"
        assert wf_data["triage_result"]["priority"] == "urgent_human_review"
        assert len(wf_data["evidence_result"]["evidence"]) > 0
        assert wf_data["verification_result"]["verified"] is True
        assert wf_data["requires_qualified_review"] is True

        # 4. Test Asynchronous Report Ingestion POST /reports
        async_res = client.submit_report_async(preset)
        assert async_res["success"] is True
        assert async_res["status_code"] == 202
        run_id = async_res["data"]["run_id"]
        assert run_id is not None
        assert async_res["data"]["status"] == "queued"

        # 5. Test Run Status Polling GET /runs/{run_id}
        run_status = client.get_run_status(run_id)
        assert run_status["success"] is True
        assert run_status["data"]["status"] in ("queued", "running", "completed")

        # 6. Test Evidence Search GET /evidence/search
        ev = client.search_evidence("carbamazepine", top_k=3)
        assert ev["success"] is True
        assert ev["data"]["result_count"] > 0
        assert len(ev["data"]["results"]) <= 3

        # 7. Test Fast Triage POST /triage
        triage = client.assess_triage_sync(preset)
        assert triage["success"] is True
        assert triage["data"]["triage"]["priority"] == "urgent_human_review"

        # 8. Test Schema Rejection & Quarantine Handling
        invalid_report = preset.copy()
        invalid_report["patient_age"] = -10  # Invalid age
        rej = client.submit_report_async(invalid_report)
        assert rej["success"] is False
        assert rej["status_code"] == 422
        assert "patient_age" in rej["error"]

    finally:
        proc.terminate()
        proc.wait(timeout=5)
