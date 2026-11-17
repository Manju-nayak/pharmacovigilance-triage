import json
from datetime import datetime
import pandas as pd
import streamlit as st

from frontend.utils.session import (
    init_session_state,
    sync_runs_with_backend,
    load_quarantined_reports,
)
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_priority_badge,
    render_status_badge,
)

st.set_page_config(
    page_title="Report History & Audit | PV Triage",
    page_icon="📋",
    layout="wide",
)

load_css()
init_session_state()

st.title("📋 Pharmacovigilance Case History & Audit Trail")
st.markdown(
    "Historical register of all ingested adverse event reports, background queue runs, "
    "and quarantined validation failures."
)

render_regulatory_banner()

# -----------------------------------------------------------------------------
# PERSISTENCE & STORAGE EXPLANATION (Requirement 1)
# -----------------------------------------------------------------------------
st.info(
    "**Storage & Persistence Architecture:**\n\n"
    "• **Audit Registry:** Cases are stored persistently in `frontend/data/history.json`, persisting across browser refreshes.\n"
    "• **Backend Redis Runs:** Asynchronous jobs are queried dynamically from the Redis run-status store (`/runs/{run_id}`).\n"
    "• **Quarantine Storage:** Schema-rejected submissions are loaded directly from the backend's `data/quarantine/` directory."
)

col_sync1, col_sync2 = st.columns([3, 1])
with col_sync2:
    if st.button("🔄 Sync with Redis Runs", use_container_width=True):
        sync_runs_with_backend()
        st.toast("Synchronized with backend Redis runs", icon="✅")
        st.rerun()

history = st.session_state.get("history", [])
quarantined = load_quarantined_reports()

# Tabs for Accepted Cases vs Quarantined Records
tab_cases, tab_quarantine = st.tabs([
    f"📁 Ingested Cases ({len(history)})",
    f"⛔ Quarantined Rejections ({len(quarantined)})",
])

# -----------------------------------------------------------------------------
# TAB 1: INGESTED CASES
# -----------------------------------------------------------------------------
with tab_cases:
    if not history:
        st.warning("No cases found in persistent history. Ingest a report to populate the audit log.")
    else:
        # Filter controls
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            search_query = st.text_input("🔍 Search by Case ID or Drug Name:", placeholder="e.g. Carbamazepine")
        with f_col2:
            priority_filter = st.selectbox("Filter by Priority:", ["All", "Urgent Human Review", "Routine Human Review", "Rejected"])
        with f_col3:
            status_filter = st.selectbox("Filter by Run Status:", ["All", "Completed", "Queued", "Running", "Failed", "Rejected"])

        filtered = []
        for item in history:
            report = item.get("report_data") or {}
            cid = str(item.get("case_id", ""))
            drug = str(report.get("drug_name", ""))
            prio = item.get("priority", "")
            stat = item.get("status", "")

            # Search text match
            if search_query:
                q = search_query.lower()
                if q not in cid.lower() and q not in drug.lower():
                    continue

            # Priority match
            if priority_filter != "All":
                prio_key = priority_filter.lower().replace(" ", "_")
                if prio != prio_key:
                    continue

            # Status match
            if status_filter != "All":
                if stat.lower() != status_filter.lower():
                    continue

            filtered.append(item)

        st.caption(f"Showing **{len(filtered)}** of **{len(history)}** total cases.")

        # Display table
        rows = []
        for item in filtered:
            rep = item.get("report_data") or {}
            rows.append({
                "Case ID": item.get("case_id"),
                "Drug Name": rep.get("drug_name", "-"),
                "Patient Age": rep.get("patient_age", "-"),
                "Reporter": rep.get("reporter_type", "-").capitalize(),
                "Priority": render_priority_badge(item.get("priority")),
                "Status": render_status_badge(item.get("status")),
                "Run ID": item.get("run_id") or "Synchronous",
                "Submitted At": item.get("submitted_at", "-")[:19].replace("T", " ") if "T" in str(item.get("submitted_at", "")) else str(item.get("submitted_at", "")),
            })

        df = pd.DataFrame(rows)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Deep-dive inspector for selected case
        st.subheader("🔍 Case Inspector & Drill-Down")
        case_ids = [item.get("case_id") for item in filtered]
        selected_cid = st.selectbox("Select Case ID to Inspect:", options=case_ids)

        selected_record = next((x for x in history if x.get("case_id") == selected_cid), None)
        if selected_record:
            d_col1, d_col2 = st.columns([2, 1])
            with d_col1:
                st.markdown(f"#### Case Details: `{selected_cid}`")
                st.json(selected_record.get("report_data", {}))
            with d_col2:
                st.markdown("#### Actions")
                if st.button("📊 Open Deep Dive Assessment", type="primary", use_container_width=True):
                    st.session_state.active_case = selected_record
                    st.switch_page("pages/2_📊_Triage_&_Assessments.py")

                if selected_record.get("run_id"):
                    st.caption(f"Run ID: `{selected_record.get('run_id')}`")
                    client = st.session_state.api_client
                    if st.button("Query Live Redis Status", use_container_width=True):
                        live_res = client.get_run_status(selected_record["run_id"])
                        st.json(live_res)

        # Export Buttons
        st.markdown("---")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            st.download_button(
                "📥 Export History as JSON",
                data=json.dumps(history, indent=2, default=str),
                file_name=f"pharmacovigilance_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with exp_col2:
            st.download_button(
                "📥 Export Summary as CSV",
                data=pd.DataFrame([
                    {
                        "case_id": x.get("case_id"),
                        "run_id": x.get("run_id"),
                        "status": x.get("status"),
                        "priority": x.get("priority"),
                        "submitted_at": x.get("submitted_at"),
                        **(x.get("report_data") or {})
                    }
                    for x in history
                ]).to_csv(index=False),
                file_name=f"pharmacovigilance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

# -----------------------------------------------------------------------------
# TAB 2: QUARANTINED REJECTIONS
# -----------------------------------------------------------------------------
with tab_quarantine:
    st.subheader("⛔ Quarantined Ingestion Failures")
    st.markdown(
        "Adverse event reports that violated Pydantic schema constraints (e.g. negative age, "
        "missing required fields, or contradictory death outcome status) are automatically intercepted "
        "by the backend validation handler and quarantined to `data/quarantine/`."
    )

    if not quarantined:
        st.success("✓ No quarantined reports on disk. All submitted cases have met schema constraints.")
    else:
        for q in quarantined:
            with st.expander(f"⚠️ Quarantine ID: {q.get('quarantine_id', 'unknown')} | Request ID: {q.get('request_id', '-')} | Received: {q.get('received_at', '-')[:19]}"):
                q_c1, q_c2 = st.columns(2)
                with q_c1:
                    st.markdown("**Submitted Payload (Raw):**")
                    st.json(q.get("body", {}))
                with q_c2:
                    st.markdown("**Validation Errors (Caught by FastAPI):**")
                    st.json(q.get("errors", []))
