import streamlit as st

from frontend.utils.session import (
    init_session_state,
    sync_runs_with_backend,
)
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_priority_badge,
    render_status_badge,
    render_agent_stepper,
    render_evidence_card,
    highlight_matched_terms,
)

st.set_page_config(
    page_title="Triage & Assessments | PV Triage",
    page_icon="📊",
    layout="wide",
)

load_css()
init_session_state()
sync_runs_with_backend()

st.title("📊 Clinical Triage & Multi-Agent Assessments")
st.markdown(
    "Detailed safety evaluation, seriousness classification, regulatory literature citations, "
    "and agent verification results for ingested adverse event reports."
)

render_regulatory_banner()

history = st.session_state.get("history", [])

if not history:
    st.info(
        "No case reports have been processed yet.\n\n"
        "Please visit the **Submit Adverse Event** page to ingest a report."
    )
    if st.button("➕ Ingest a Report", type="primary"):
        st.switch_page("pages/1_📥_Submit_Report.py")
    st.stop()

# -----------------------------------------------------------------------------
# CASE SELECTOR
# -----------------------------------------------------------------------------
case_options = [
    f"{item.get('case_id')} - {item.get('report_data', {}).get('drug_name', 'Unknown')} ({item.get('priority', 'pending').replace('_', ' ').title()})"
    for item in history
]

active_case_idx = 0
if st.session_state.get("active_case"):
    active_cid = st.session_state.active_case.get("case_id")
    for i, item in enumerate(history):
        if item.get("case_id") == active_cid:
            active_case_idx = i
            break

selected_case_label = st.selectbox(
    "Select Case for Deep-Dive Clinical Assessment:",
    options=case_options,
    index=active_case_idx,
)

# Set selected as active
selected_case_id = selected_case_label.split(" - ")[0]
current_case = next((c for c in history if c.get("case_id") == selected_case_id), history[0])
st.session_state.active_case = current_case

report_data = current_case.get("report_data") or {}
result_data = current_case.get("result") or current_case.get("backend_response") or {}

# Extract agent sub-results
triage_result = result_data.get("triage_result") or result_data.get("triage") or {}
evidence_result = result_data.get("evidence_result") or {}
verification_result = result_data.get("verification_result") or {}
workflow_status = result_data.get("workflow_status") or current_case.get("status", "completed")
errors = result_data.get("errors", [])

st.markdown("---")

# -----------------------------------------------------------------------------
# CASE OVERVIEW & TRIAGE PRIORITY
# -----------------------------------------------------------------------------
header_col1, header_col2, header_col3 = st.columns([2, 1, 1])

with header_col1:
    st.subheader(f"Case `{current_case.get('case_id')}`: {report_data.get('drug_name', 'Unknown')}")
    st.caption(
        f"Reporter: **{report_data.get('reporter_type', '-').capitalize()}** | "
        f"Patient Age: **{report_data.get('patient_age', '-')}** | "
        f"Onset Latency: **{report_data.get('event_onset_days', '-')} days** | "
        f"Outcome: **{report_data.get('outcome', '-').replace('_', ' ').title()}**"
    )

with header_col2:
    st.markdown("**Review Priority:**", unsafe_allow_html=True)
    st.markdown(render_priority_badge(current_case.get("priority")), unsafe_allow_html=True)

with header_col3:
    st.markdown("**Execution Status:**", unsafe_allow_html=True)
    st.markdown(render_status_badge(current_case.get("status")), unsafe_allow_html=True)
    if current_case.get("run_id"):
        st.caption(f"Run ID: `{current_case.get('run_id')[:8]}...`")

# Render reaction narrative
st.markdown("<br>", unsafe_allow_html=True)
matched_terms_all = []
for sig in triage_result.get("signals", []):
    matched_terms_all.extend(sig.get("matched_terms", []))

narrative_html = highlight_matched_terms(
    report_data.get("reaction_description", "No narrative provided."),
    matched_terms_all,
)
st.markdown(
    f"""
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
        <span style="font-size:0.8rem; font-weight:700; color:#64748b; text-transform:uppercase;">Clinical Narrative:</span>
        <div style="font-size:0.95rem; color:#1e293b; margin-top:4px; line-height:1.5;">
            {narrative_html}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Multi-Agent Workflow Stepper
if current_case.get("submission_mode") in ("sync_workflow", "async_queue"):
    st.markdown("#### 🤖 Multi-Agent Workflow Progression")
    render_agent_stepper(workflow_status, errors)

st.markdown("---")

# -----------------------------------------------------------------------------
# TABS: DETAILED ASSESSMENTS
# -----------------------------------------------------------------------------
tab_triage, tab_evidence, tab_verification, tab_raw = st.tabs([
    "🚨 Triage & Seriousness Signals",
    "📚 Evidence & Literature Citations",
    "🛡️ Agent Verification & Audit",
    "🔍 Raw Backend JSON",
])

# -----------------------------------------------------------------------------
# TAB 1: TRIAGE & SERIOUSNESS
# -----------------------------------------------------------------------------
with tab_triage:
    st.subheader("🚨 Safety Signal Triage & Seriousness Criteria")

    signals = triage_result.get("signals", [])

    sig_col1, sig_col2 = st.columns([1, 1])

    with sig_col1:
        st.markdown("#### Identified Safety Signals")
        if not signals:
            st.success("✓ No urgent safety signals detected. Case categorized as **Routine Human Review**.")
        else:
            for s in signals:
                signal_type = s.get("signal", "unknown_signal")
                reason = s.get("reason", "No reason specified.")
                terms = s.get("matched_terms", [])

                if signal_type == "reported_death":
                    st.error(f"**💀 Signal: Reported Death**\n\n{reason}")
                elif signal_type == "reported_hospitalization":
                    st.warning(f"**🏥 Signal: Hospitalization Required**\n\n{reason}")
                elif signal_type == "potentially_serious_reaction_text":
                    terms_str = ", ".join([f"`{t}`" for t in terms])
                    st.error(
                        f"**⚠️ Signal: Potentially Serious Clinical Condition**\n\n"
                        f"{reason}\n\n"
                        f"**Matched Warning Terms:** {terms_str}"
                    )
                else:
                    st.info(f"**Signal: {signal_type}**\n\n{reason}")

    with sig_col2:
        st.markdown("#### Regulatory Seriousness & Expectedness")

        # Actual Seriousness Breakdown (Strictly derived from backend)
        is_hosp = bool(report_data.get("hospitalization"))
        is_death = bool(report_data.get("death"))
        has_serious_text = any(s.get("signal") == "potentially_serious_reaction_text" for s in signals)
        is_serious = is_hosp or is_death or has_serious_text

        st.markdown(
            f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:14px; margin-bottom:12px;">
                <strong>Seriousness Classification (ICH E2A Criteria):</strong><br>
                • <strong>Regulatory Seriousness:</strong> {'<span style="color:#dc2626; font-weight:700;">SERIOUS</span>' if is_serious else '<span style="color:#059669; font-weight:700;">NON-SERIOUS</span>'}<br>
                • Resulted in Death: <strong>{'Yes (Fatal Event)' if is_death else 'No'}</strong><br>
                • Caused/Prolonged Hospitalization: <strong>{'Yes' if is_hosp else 'No'}</strong><br>
                • Important Medical Event / Warning Terms: <strong>{'Yes (Matched high-risk terms)' if has_serious_text else 'None'}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Honest Expectedness Assessment (Requirement 2: Do not fabricate)
        st.markdown(
            """
            <div style="background:#eff6ff; border-left:4px solid #3b82f6; border-radius:0 8px 8px 0; padding:12px 14px; font-size:0.875rem; color:#1e3a8a;">
                <strong>📋 Expectedness Assessment:</strong><br>
                <em>Automated expectedness verdict is not generated by the backend model.</em><br>
                In compliance with pharmacovigilance standards (e.g. CDSCO MAH Guidance / ICH E2A),
                classifying a reaction as <strong>Expected</strong> vs. <strong>Unexpected</strong>
                mandates comparing the reported event against the Reference Safety Information (RSI) / approved Package Insert.
                Please inspect the official retrieved package insert passages in the <strong>Evidence Citations</strong> tab.
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# TAB 2: EVIDENCE & CITATIONS
# -----------------------------------------------------------------------------
with tab_evidence:
    st.subheader("📚 Supporting Medical Evidence & Package Insert Citations")

    evidence_items = evidence_result.get("evidence", [])
    retrieval_status = evidence_result.get("retrieval_status", "unknown")

    ev_info_c1, ev_info_c2 = st.columns([2, 1])
    with ev_info_c1:
        st.caption(
            "Passages retrieved from indexed reference documents "
            "(Carbamazepine CDSCO safety notice, Tegretol package inserts, MAH clinical rules)."
        )
    with ev_info_c2:
        st.markdown(f"**Retrieval Status:** `{retrieval_status.upper()}` | **Found:** `{len(evidence_items)} passages`")

    notice = evidence_result.get("notice")
    if notice:
        st.info(f"**Medical Auditor Notice:** {notice}")

    if not evidence_items:
        st.warning("No evidence passages retrieved for this case query, or evidence agent was skipped.")
    else:
        for idx, item in enumerate(evidence_items, start=1):
            render_evidence_card(item, idx)

# -----------------------------------------------------------------------------
# TAB 3: VERIFICATION & AUDIT
# -----------------------------------------------------------------------------
with tab_verification:
    st.subheader("🛡️ Multi-Agent Verification & Audit Trail")

    if not verification_result:
        st.info("Verification agent result not available for this execution mode.")
    else:
        is_verified = verification_result.get("verified", False)
        citations_valid = verification_result.get("citations_valid", False)
        evidence_found = verification_result.get("evidence_found", False)
        valid_count = verification_result.get("valid_passage_count", 0)
        invalid_count = verification_result.get("invalid_passage_count", 0)
        reason = verification_result.get("reason", "unknown")

        ver_c1, ver_c2, ver_c3 = st.columns(3)
        with ver_c1:
            st.metric("Traceability Verification", "PASSED" if is_verified else "FLAGGED / INCOMPLETE")
        with ver_c2:
            st.metric("Citations Valid", "YES" if citations_valid else "NO")
        with ver_c3:
            st.metric("Valid / Invalid Passages", f"{valid_count} / {invalid_count}")

        st.markdown(f"**Verification Outcome Reason:** `{reason}`")

        # Disclaimers & Audit Limitations from backend
        limitations = verification_result.get("limitations", [])
        if limitations:
            st.markdown("#### Inherent System Limitations (As Reported by Verification Agent)")
            for lim in limitations:
                st.markdown(f"- ℹ️ {lim}")

        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:12px; font-size:0.85rem; color:#475569;">
                <strong>Regulatory Verification Checklist:</strong><br>
                • Semantic Support Verified: <code>{verification_result.get('semantic_support_verified', False)}</code> (Keyword overlap does not prove medical claim)<br>
                • Causality Assessed: <code>{verification_result.get('causality_assessed', False)}</code> (Causality assessment remains human-exclusive)<br>
                • Final Medical Decision: <code>{verification_result.get('final_medical_decision', False)}</code><br>
                • Requires Qualified Review: <code>{result_data.get('requires_qualified_review', True)}</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# TAB 4: RAW JSON
# -----------------------------------------------------------------------------
with tab_raw:
    st.subheader("🔍 Complete Backend Response JSON")
    st.caption("Verbatim response received from FastAPI endpoints for transparency and debugging.")
    st.json(result_data)
