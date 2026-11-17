import time
from typing import Any, Dict, Optional, Tuple
import requests

from frontend.config import DEFAULT_BACKEND_URL, DEFAULT_TIMEOUT


class APIClient:
    """
    Centralized HTTP client for communicating with the
    Pharmacovigilance Adverse Event Intake and Triage FastAPI backend.
    """

    def __init__(self, base_url: str = DEFAULT_BACKEND_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def set_base_url(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # -------------------------------------------------------------------------
    # Helper: Generic request handler with error wrapping
    # -------------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )

            # Try parsing JSON body
            try:
                body = response.json()
            except Exception:
                body = {"raw_text": response.text}

            return {
                "success": response.status_code in (200, 201, 202),
                "status_code": response.status_code,
                "data": body if response.status_code in (200, 201, 202) else None,
                "error": None if response.status_code in (200, 201, 202) else self._extract_error(response, body),
                "headers": dict(response.headers),
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "status_code": 0,
                "data": None,
                "error": f"Cannot connect to backend at {self.base_url}. Ensure FastAPI is running.",
                "headers": {},
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status_code": 408,
                "data": None,
                "error": f"Request to {path} timed out after {self.timeout}s.",
                "headers": {},
            }
        except Exception as exc:
            return {
                "success": False,
                "status_code": 500,
                "data": None,
                "error": f"Unexpected request failure: {str(exc)}",
                "headers": {},
            }

    @staticmethod
    def _extract_error(response: requests.Response, body: Any) -> str:
        """Extract a readable error message from response body."""
        if isinstance(body, dict):
            # Check for Pydantic validation error format
            if "detail" in body:
                detail = body["detail"]
                if isinstance(detail, list):
                    # List of field validation errors
                    err_msgs = []
                    for item in detail:
                        loc = " -> ".join(str(x) for x in item.get("loc", []))
                        msg = item.get("msg", "Validation error")
                        err_msgs.append(f"• [{loc}]: {msg}")
                    return "\n".join(err_msgs)
                return str(detail)
            if "message" in body:
                return str(body["message"])
            if "error" in body:
                return str(body["error"])
        return f"HTTP {response.status_code}: {response.reason}"

    # -------------------------------------------------------------------------
    # Health & Metrics
    # -------------------------------------------------------------------------
    def get_health(self) -> Dict[str, Any]:
        """Check GET /health."""
        return self._request("GET", "/health")

    def get_metrics(self) -> Dict[str, Any]:
        """Check GET /metrics."""
        return self._request("GET", "/metrics")

    # -------------------------------------------------------------------------
    # Asynchronous Submission & Run Polling
    # -------------------------------------------------------------------------
    def submit_report_async(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit adverse event report via POST /reports (Status: 202 Accepted).
        Enqueues background RQ job and returns run_id.
        """
        return self._request("POST", "/reports", json_data=report_data)

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Poll run status via GET /runs/{run_id}.
        """
        return self._request("GET", f"/runs/{run_id}")

    def poll_run(
        self,
        run_id: str,
        max_attempts: int = 15,
        interval_sec: float = 1.0,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Synchronously poll run until completed, failed, or timed out.
        Returns (result_dict, status_str).
        """
        for _ in range(max_attempts):
            res = self.get_run_status(run_id)
            if not res["success"]:
                return None, f"Polling error: {res.get('error', 'unknown error')}"

            run_data = res["data"]
            status = run_data.get("status")
            if status == "completed":
                return run_data, "completed"
            if status == "failed":
                return run_data, f"failed: {run_data.get('error')}"

            time.sleep(interval_sec)

        return None, "timeout"

    # -------------------------------------------------------------------------
    # Synchronous Workflow & Triage
    # -------------------------------------------------------------------------
    def run_workflow_sync(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full 4-agent LangGraph workflow via POST /workflow/run.
        Returns immediate assessment results.
        """
        return self._request("POST", "/workflow/run", json_data=report_data)

    def assess_triage_sync(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast rule-based triage via POST /triage.
        """
        return self._request("POST", "/triage", json_data=report_data)

    def assess_triage_with_evidence_sync(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triage + evidence retrieval via POST /triage/with-evidence.
        """
        return self._request("POST", "/triage/with-evidence", json_data=report_data)

    # -------------------------------------------------------------------------
    # Evidence Search
    # -------------------------------------------------------------------------
    def search_evidence(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Direct search in reference document corpus via GET /evidence/search.
        """
        return self._request("GET", "/evidence/search", params={"q": query, "top_k": top_k})
