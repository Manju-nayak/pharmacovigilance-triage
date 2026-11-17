import streamlit as st
import pandas as pd

from frontend.utils.session import (
    init_session_state,
    sync_runs_with_backend,
    load_quarantined_reports,
)
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_kpi_card,
    render_priority_badge,
    render_status_badge,
)
from frontend.config import DEFAULT_BACKEND_URL


st.set_page_config(
    page_title="Pharmacovigilance Triage Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize styles & state
load_css()
init_session_state()
sync_runs_with_backend()

client = st.session_state.api_client

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/caduceus.png",
        width=60,
    )
    st.title("PV Safety Suite")
    st.caption("Adverse Event Intake & Multi-Agent Triage")

    st.markdown("---")
    st.subheader("🔌 Backend Connection")

    backend_input = st.text_input(
        "FastAPI Service URL",
        value=st.session_state.backend_url,
        help="Endpoint for the FastAPI pharmacovigilance backend",
    )
    if backend_input != st.session_state.backend_url:
        st.session_state.backend_url = backend_input
        client.set_base_url(backend_input)
        st.rerun()

    # Backend ping
    health_res = client.get_health()
    if health_res.get("success"):
        v = health_res["data"].get("version", "unknown")
        st.success(f"● Online (API v{v})")
    else:
        st.error(f"● Offline: {health_res.get('error', 'Cannot reach backend')}")
        st.caption("Start backend with: `python -m uvicorn app.main:app --reload`")

    st.markdown("---")
    st.subheader("Navigation Shortcut")
    st.page_link("app.py", label="Dashboard Overview", icon="🏠")
    st.page_link("pages/1_📥_Submit_Report.py", label="Submit Adverse Event", icon="📥")
    st.page_link("pages/2_📊_Triage_&_Assessments.py", label="Triage & Assessments", icon="📊")
    st.page_link("pages/3_📋_Report_History.py", label="Report History & Audit", icon="📋")
    st.page_link("pages/4_🔍_Evidence_Explorer.py", label="Evidence Explorer", icon="🔍")
    st.page_link("pages/5_⚙️_System_Health.py", label="System Diagnostics", icon="⚙️")

    st.markdown("---")
    if st.button("🔄 Sync with Backend Runs", use_container_width=True):
        sync_runs_with_backend()
        st.toast("Synchronized with Redis backend runs", icon="✅")
        st.rerun()


# -----------------------------------------------------------------------------
# MAIN CONTENT: EXECUTIVE DASHBOARD
# -----------------------------------------------------------------------------
st.title("🏥 Pharmacovigilance Adverse Event Intake & Triage")
st.markdown(
    "Automated safety signal prioritization, evidence retrieval, and verification "
    "powered by a **4-Agent LangGraph Workflow** and **FastAPI**."
)

render_regulatory_banner()

# Fetch backend operational metrics
metrics_res = client.get_metrics()
metrics_data = metrics_res.get("data") or {}

history = st.session_state.get("history", [])
quarantined = load_quarantined_reports()

# Compute KPI stats
total_reports = len(history)
urgent_count = sum(1 for item in history if item.get("priority") == "urgent_human_review")
routine_count = sum(1 for item in history if item.get("priority") == "routine_human_review")
agent_runs_started = metrics_data.get("agent_runs_started", total_reports)
rejected_count = metrics_data.get("rejected_reports", len(quarantined))

# Render KPI metric row
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
with kpi_col1:
    render_kpi_card("Total Intake", total_reports, "Processed cases in log", "📁")
with kpi_col2:
    render_kpi_card("Urgent Review", urgent_count, "Flagged safety signals", "🔴")
with kpi_col3:
    render_kpi_card("Routine Review", routine_count, "No urgent signals", "🟢")
with kpi_col4:
    render_kpi_card("Agent Runs", agent_runs_started, "LangGraph executions", "🤖")
with kpi_col5:
    render_kpi_card("Quarantined", rejected_count, "Schema validation failures", "⛔")

st.markdown("---")

# Quick Action Banner
action_col1, action_col2 = st.columns([2, 1])
with action_col1:
    st.subheader("📋 Active Safety Triage Queue")
    st.caption("Real-time view of submitted adverse event reports and their triage priority.")
with action_col2:
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("➕ Ingest Report", type="primary", use_container_width=True):
            st.switch_page("pages/1_📥_Submit_Report.py")
    with btn_col2:
        if st.button("🔍 Search Evidence", use_container_width=True):
            st.switch_page("pages/4_🔍_Evidence_Explorer.py")

if not history:
    st.info(
        "**No adverse event reports ingested yet.**\n\n"
        "Go to the **Submit Adverse Event** page or click **Ingest Report** above to load a clinical preset "
        "and test the multi-agent triage workflow."
    )
else:
    # Build summary table
    table_rows = []
    for item in history:
        report = item.get("report_data") or {}
        case_id = item.get("case_id") or report.get("case_id", "Unknown")
        drug = report.get("drug_name", "Unknown")
        age = report.get("patient_age", "-")
        reporter = report.get("reporter_type", "-").capitalize()
        priority_html = render_priority_badge(item.get("priority"))
        status_html = render_status_badge(item.get("status"))
        submitted_at = item.get("submitted_at", "-")
        mode = "Async Queue" if item.get("submission_mode") == "async_queue" else "Sync Workflow"

        table_rows.append({
            "Case ID": case_id,
            "Drug": drug,
            "Age": age,
            "Reporter": reporter,
            "Priority": priority_html,
            "Run Status": status_html,
            "Mode": mode,
            "Submitted At": submitted_at[:19].replace("T", " ") if "T" in str(submitted_at) else str(submitted_at),
        })

    df = pd.DataFrame(table_rows)
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        # Case quick switcher
        case_options = [f"{item.get('case_id')} - {item.get('report_data', {}).get('drug_name', '')}" for item in history]
        selected_case_str = st.selectbox("Inspect Case Assessment:", options=case_options, index=0)
    with c2:
        st.write("")
        st.write("")
        if st.button("📊 Open Deep Dive Assessment", type="primary", use_container_width=True):
            selected_case_id = selected_case_str.split(" - ")[0]
            for item in history:
                if item.get("case_id") == selected_case_id:
                    st.session_state.active_case = item
                    break
            st.switch_page("pages/2_📊_Triage_&_Assessments.py")

st.markdown("---")

# Architecture Guide
with st.expander("ℹ️ System Architecture & Multi-Agent LangGraph Overview"):
    st.markdown(
        """
        ### Multi-Agent Pharmacovigilance Architecture
        
        The backend orchestrates four specialized agents to intake, triage, contextualize, and verify adverse event reports:

        1. **Intake Agent:** Inspects and confirms syntactic and schema validity of incoming ICSR/synthetic cases.
        2. **Triage Agent:** Scans for high-urgency clinical terms (*Stevens-Johnson Syndrome, Toxic Epidermal Necrolysis, Anaphylaxis, Skin Blistering/Peeling*) and seriousness indicators (*Hospitalization, Death*).
        3. **Evidence Agent:** Queries the indexed medical document corpus (CDSCO notices, Carbamazepine package inserts, MAH clinical rules) and retrieves relevant passages.
        4. **Verification Agent:** Audits evidence structural integrity, citation traceability, and page references before passing to human review.

        ```
        [Client / Streamlit UI]
                 │
                 ▼
        [FastAPI API Layer] ──────► [Pydantic Validation] ──(Invalid)──► [Quarantine Storage]
                 │ (Valid)
                 ├──────────────────────────────┬──────────────────────────────┐
                 ▼ (Sync Workflow)              ▼ (Async Mode)                 ▼
         [/workflow/run]                [/reports]                      [/evidence/search]
                 │                              │                               │
                 │                      [Redis Queue (RQ)]                      ▼
                 │                              │                     [Indexed Medical Corpus]
                 ▼                              ▼
        [LangGraph 4-Agent Pipeline] ◄── [RQ Background Worker]
        (Intake -> Triage -> Evidence -> Verification)
                 │
                 ▼
        [Structured Clinical Result] ──► [Redis Run Status Store] ──► [/runs/{run_id}]
        ```
        """
    )
