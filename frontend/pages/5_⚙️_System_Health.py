import time
import streamlit as st

from frontend.api_client import APIClient
from frontend.config import DEFAULT_BACKEND_URL, HISTORY_FILE
from frontend.utils.session import (
    init_session_state,
    save_persistent_history,
)
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_kpi_card,
)

st.set_page_config(
    page_title="System Health & Diagnostics | PV Triage",
    page_icon="⚙️",
    layout="wide",
)

load_css()
init_session_state()
client: APIClient = st.session_state.api_client

st.title("⚙️ System Health & API Diagnostics")
st.markdown(
    "Monitor live FastAPI backend availability, query operational metrics (`/metrics`), "
    "test endpoint latency, and manage backend connections."
)

render_regulatory_banner()

# -----------------------------------------------------------------------------
# BACKEND CONNECTION CONFIGURATION
# -----------------------------------------------------------------------------
st.subheader("🔌 Backend Endpoint Configuration")

cfg_c1, cfg_c2 = st.columns([3, 1])
with cfg_c1:
    new_url = st.text_input(
        "FastAPI Service Base URL:",
        value=st.session_state.backend_url,
        help="Update if running on a custom port or remote container host",
    )
with cfg_c2:
    st.write("")
    st.write("")
    if st.button("Apply URL", type="primary", use_container_width=True):
        st.session_state.backend_url = new_url.strip()
        client.set_base_url(new_url.strip())
        st.toast(f"Updated backend target to {new_url}", icon="🔌")
        st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# LIVE SYSTEM HEALTH & METRICS
# -----------------------------------------------------------------------------
st.subheader("📊 Live Backend Telemetry")

t_start = time.perf_counter()
health_res = client.get_health()
latency_ms = (time.perf_counter() - t_start) * 1000

metrics_res = client.get_metrics()
metrics_data = metrics_res.get("data") or {}

m_c1, m_c2, m_c3, m_c4 = st.columns(4)

with m_c1:
    if health_res.get("success"):
        render_kpi_card("API Status", "ONLINE", f"Latency: {latency_ms:.1f} ms", "🟢")
    else:
        render_kpi_card("API Status", "OFFLINE", "Unreachable", "🔴")

with m_c2:
    v = health_res.get("data", {}).get("version", "N/A") if health_res.get("success") else "N/A"
    render_kpi_card("API Version", v, "FastAPI Service", "🏷️")

with m_c3:
    render_kpi_card(
        "Agent Runs Started",
        metrics_data.get("agent_runs_started", 0),
        "LangGraph invocations",
        "🤖",
    )

with m_c4:
    render_kpi_card(
        "Quarantined Reports",
        metrics_data.get("rejected_reports", 0),
        "Failed schema validation",
        "⛔",
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# ENDPOINT DIAGNOSTICS SUITE
# -----------------------------------------------------------------------------
st.subheader("🧪 Live Endpoint Diagnostic Probe")
st.markdown("Run live HTTP tests against all primary FastAPI endpoints:")

if st.button("▶️ Run Diagnostic Probes", type="primary"):
    endpoints = [
        ("GET /health", lambda: client.get_health()),
        ("GET /metrics", lambda: client.get_metrics()),
        (
            "GET /evidence/search?q=carbamazepine&top_k=2",
            lambda: client.search_evidence("carbamazepine", top_k=2),
        ),
        (
            "POST /triage (synthetic)",
            lambda: client.assess_triage_sync({
                "case_id": "DIAG-001",
                "drug_name": "TestDrug",
                "reaction_description": "Diagnostic probe test.",
                "patient_age": 30,
                "reporter_type": "doctor",
                "outcome": "recovered",
                "event_onset_days": 1,
                "hospitalization": False,
                "death": False,
            }),
        ),
    ]

    for name, call_fn in endpoints:
        t0 = time.perf_counter()
        res = call_fn()
        dt = (time.perf_counter() - t0) * 1000

        if res.get("success"):
            st.success(f"✓ **{name}** — HTTP {res.get('status_code')} ({dt:.1f} ms)")
        else:
            st.error(f"❌ **{name}** — Failed: {res.get('error')} ({dt:.1f} ms)")

st.markdown("---")

# -----------------------------------------------------------------------------
# BACKGROUND QUEUE & WORKER ARCHITECTURE
# -----------------------------------------------------------------------------
st.subheader("📦 Asynchronous Processing Architecture (Redis & RQ)")
st.markdown(
    """
    The background processing pipeline decouples immediate intake ingestion from heavy LangGraph multi-agent execution:

    1. **Client** calls `POST /reports`.
    2. **FastAPI** generates a `run_id`, records initial status in **Redis** (`pharmacovigilance:run:{run_id}`), and enqueues job into RQ queue `pharmacovigilance`.
    3. **RQ Worker** picks up the job, validates report, executes `run_workflow()`, and updates the Redis record to `completed` with full results.
    4. **Streamlit UI** polls `GET /runs/{run_id}` until completed.

    **Running Worker Locally:**
    ```bash
    python -m rq.cli worker --url redis://localhost:6379/0 pharmacovigilance
    ```
    """
)

# -----------------------------------------------------------------------------
# STORAGE & LOG MANAGEMENT
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🗑️ Audit Trail Management")

col_del1, col_del2 = st.columns([3, 1])
with col_del1:
    st.caption(f"Persistent history file location: `{HISTORY_FILE}`")
with col_del2:
    if st.button("Clear Frontend History", type="secondary", use_container_width=True):
        st.session_state.history = []
        st.session_state.active_case = None
        save_persistent_history([])
        st.toast("Audit history cleared.", icon="🗑️")
        st.rerun()
