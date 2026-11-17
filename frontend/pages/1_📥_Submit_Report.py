from datetime import datetime, timezone
import time
import streamlit as st

from frontend.api_client import APIClient
from frontend.config import SAMPLE_PRESETS
from frontend.utils.session import (
    init_session_state,
    add_or_update_history_record,
)
from frontend.utils.validators import (
    validate_death_outcome_consistency,
    validate_report_form,
)
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_priority_badge,
    render_status_badge,
    render_agent_stepper,
)

st.set_page_config(
    page_title="Submit Adverse Event | PV Triage",
    page_icon="📥",
    layout="wide",
)

load_css()
init_session_state()
client: APIClient = st.session_state.api_client

st.title("📥 Adverse Event Report Intake")
st.markdown(
    "Submit an individual case safety report (ICSR) for automated intake validation, "
    "safety signal triage, literature evidence retrieval, and verification."
)

render_regulatory_banner()

# -----------------------------------------------------------------------------
# CLINICAL PRESET LOADER
# -----------------------------------------------------------------------------
st.subheader("⚡ Quick Load Scenario Presets")
preset_cols = st.columns([3, 1])

with preset_cols[0]:
    preset_choice = st.selectbox(
        "Select a pre-configured clinical scenario:",
        options=["-- Choose a preset or fill form manually --"] + list(SAMPLE_PRESETS.keys()) + ["⚠️ Malformed Schema Demo (Triggers 422 Quarantine)"],
    )

with preset_cols[1]:
    st.write("")
    st.write("")
    if st.button("Load Preset Data", use_container_width=True):
        if preset_choice in SAMPLE_PRESETS:
            st.session_state["form_data"] = SAMPLE_PRESETS[preset_choice].copy()
            st.toast(f"Loaded {preset_choice}", icon="📋")
        elif preset_choice.startswith("⚠️ Malformed"):
            st.session_state["form_data"] = {
                "case_id": "ERR-INVALID-AGE",
                "drug_name": "TestDrug",
                "reaction_description": "Patient took drug and felt unwell.",
                "patient_age": -5,  # Violates ge=0
                "reporter_type": "patient",
                "outcome": "recovered",
                "event_onset_days": 1,
                "hospitalization": False,
                "death": False,
            }
            st.toast("Loaded invalid data for quarantine test", icon="⚠️")

# Retrieve current form state defaults
form_defaults = st.session_state.get(
    "form_data",
    {
        "case_id": f"PV-{int(time.time())}",
        "drug_name": "Carbamazepine",
        "reaction_description": "Patient developed severe rash with skin peeling and mucosal blistering.",
        "patient_age": 45,
        "reporter_type": "doctor",
        "outcome": "not_recovered",
        "event_onset_days": 7,
        "hospitalization": True,
        "death": False,
    },
)

st.markdown("---")

# -----------------------------------------------------------------------------
# INTAKE FORM
# -----------------------------------------------------------------------------
st.subheader("📝 Case Report Details")

with st.form("adverse_event_intake_form"):
    col1, col2 = st.columns(2)

    with col1:
        case_id = st.text_input(
            "Case ID *",
            value=form_defaults.get("case_id", ""),
            help="Alphanumeric, underscore, or hyphen only. 3-50 characters.",
        )
        drug_name = st.text_input(
            "Suspect Drug Name *",
            value=form_defaults.get("drug_name", ""),
            help="Name of the suspect medication (2-150 characters).",
        )
        patient_age = st.number_input(
            "Patient Age (Years) *",
            min_value=-10,  # Allows entering negative if testing quarantine
            max_value=120,
            value=int(form_defaults.get("patient_age", 45)),
            help="Valid clinical range is 0 to 120 years.",
        )
        reporter_type_opts = ["patient", "doctor", "pharmacist", "literature"]
        default_reporter = form_defaults.get("reporter_type", "doctor")
        reporter_idx = reporter_type_opts.index(default_reporter) if default_reporter in reporter_type_opts else 1
        reporter_type = st.selectbox(
            "Reporter Type *",
            options=reporter_type_opts,
            index=reporter_idx,
            format_func=lambda x: x.capitalize(),
        )

    with col2:
        event_onset_days = st.number_input(
            "Event Onset Latency (Days) *",
            min_value=0,
            max_value=36500,
            value=int(form_defaults.get("event_onset_days", 7)),
            help="Days elapsed between drug initiation and adverse event onset.",
        )
        outcome_opts = ["recovered", "recovering", "not_recovered", "death", "unknown"]
        default_outcome = form_defaults.get("outcome", "not_recovered")
        outcome_idx = outcome_opts.index(default_outcome) if default_outcome in outcome_opts else 2
        outcome = st.selectbox(
            "Patient Outcome *",
            options=outcome_opts,
            index=outcome_idx,
            format_func=lambda x: x.replace("_", " ").capitalize(),
        )

        st.markdown("<label style='font-size:0.875rem; font-weight:600;'>Seriousness Criteria:</label>", unsafe_allow_html=True)
        hosp_col, death_col = st.columns(2)
        with hosp_col:
            hospitalization = st.checkbox(
                "Hospitalization Required",
                value=bool(form_defaults.get("hospitalization", False)),
                help="Did the adverse event require inpatient hospitalization?",
            )
        with death_col:
            death = st.checkbox(
                "Resulted in Death",
                value=bool(form_defaults.get("death", False)),
                help="Did the adverse event result in patient death?",
            )

    reaction_description = st.text_area(
        "Reaction / Event Description *",
        value=form_defaults.get("reaction_description", ""),
        height=130,
        help="Detailed clinical narrative describing signs, symptoms, progression, and clinical actions (5-3000 chars).",
    )

    # Submission mode selection
    st.markdown("---")
    mode_col1, mode_col2 = st.columns([2, 1])
    with mode_col1:
        submission_mode = st.radio(
            "Processing Workflow Mode:",
            options=[
                "Synchronous Multi-Agent Workflow (Immediate LangGraph Execution)",
                "Asynchronous Background Queue (Redis + RQ Worker Polling)",
                "Fast Rule-Based Triage Only (No Evidence Retrieval)",
            ],
            index=0,
            help=(
                "Synchronous executes the LangGraph workflow directly in-process. "
                "Asynchronous enqueues into Redis and polls /runs/{run_id} until complete."
            ),
        )
    with mode_col2:
        st.caption("**Backend Target:**")
        st.code(st.session_state.backend_url, language="text")

    submit_button = st.form_submit_button(
        "🚀 Ingest & Process Report",
        type="primary",
        use_container_width=True,
    )

# -----------------------------------------------------------------------------
# FORM SUBMISSION HANDLER
# -----------------------------------------------------------------------------
if submit_button:
    # Build payload
    payload = {
        "case_id": case_id.strip(),
        "drug_name": drug_name.strip(),
        "reaction_description": reaction_description.strip(),
        "patient_age": int(patient_age),
        "reporter_type": reporter_type,
        "outcome": outcome,
        "event_onset_days": int(event_onset_days),
        "hospitalization": bool(hospitalization),
        "death": bool(death),
    }

    # Strict client-side validation: prevent submission when death/outcome are inconsistent
    is_consistent, consistency_err = validate_death_outcome_consistency(death, outcome)
    if not is_consistent:
        st.error(f"⛔ Form Validation Error: {consistency_err}")
        st.warning(
            "⚠️ Submission blocked: Inconsistent mortality and outcome data violates "
            "Pydantic schema constraints. Please correct the fields above to proceed."
        )
        st.stop()

    # Basic field requirements
    if not payload["case_id"] or len(payload["case_id"]) < 3:
        st.error("⛔ Form Validation Error: Case ID must be at least 3 characters.")
        st.stop()
    if not payload["drug_name"] or len(payload["drug_name"]) < 2:
        st.error("⛔ Form Validation Error: Suspect drug name must be at least 2 characters.")
        st.stop()
    if not payload["reaction_description"] or len(payload["reaction_description"]) < 5:
        st.error("⛔ Form Validation Error: Reaction description must be at least 5 characters.")
        st.stop()

    submitted_at = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # Mode 1: Synchronous Multi-Agent Workflow (POST /workflow/run)
    # -------------------------------------------------------------------------
    if "Synchronous" in submission_mode:
        with st.spinner("🤖 Orchestrating LangGraph Multi-Agent Pipeline (Intake → Triage → Evidence → Verification)..."):
            res = client.run_workflow_sync(payload)

        if not res["success"]:
            # Check if 422 rejected & quarantined
            if res["status_code"] == 422:
                st.error("⛔ Report Rejected by Schema Validation Handler")
                st.markdown(
                    f"**Quarantined Record:** The backend rejected this report and saved it to `data/quarantine/`.\n\n"
                    f"**Details:**\n```\n{res['error']}\n```"
                )
                record = {
                    "case_id": payload["case_id"],
                    "run_id": None,
                    "submission_mode": "sync_workflow",
                    "submitted_at": submitted_at,
                    "report_data": payload,
                    "status": "rejected",
                    "priority": "rejected",
                    "error": res["error"],
                    "backend_response": res,
                }
                add_or_update_history_record(record)
            else:
                st.error(f"❌ Workflow Error (HTTP {res['status_code']}): {res['error']}")
        else:
            data = res["data"]
            triage_res = data.get("triage_result") or {}
            verification_res = data.get("verification_result") or {}
            workflow_status = data.get("workflow_status", "completed")

            record = {
                "case_id": payload["case_id"],
                "run_id": None,
                "submission_mode": "sync_workflow",
                "submitted_at": submitted_at,
                "report_data": payload,
                "status": "completed",
                "priority": triage_res.get("priority", "routine_human_review"),
                "verified": verification_res.get("verified", False),
                "result": data,
                "backend_response": data,
            }
            add_or_update_history_record(record)
            st.session_state.active_case = record

            st.success(f"✓ Case {payload['case_id']} successfully processed by LangGraph workflow!")
            render_agent_stepper(workflow_status, data.get("errors"))

            # Quick summary card
            res_c1, res_c2, res_c3 = st.columns(3)
            with res_c1:
                st.markdown(f"**Triage Priority:**<br>{render_priority_badge(record['priority'])}", unsafe_allow_html=True)
            with res_c2:
                signals = triage_res.get("signals", [])
                st.metric("Detected Signals", f"{len(signals)} signals")
            with res_c3:
                evidence_items = (data.get("evidence_result") or {}).get("evidence", [])
                st.metric("Retrieved Citations", f"{len(evidence_items)} passages")

            if st.button("🔍 Open Full Triage & Evidence Assessment", type="primary", use_container_width=True):
                st.switch_page("pages/2_📊_Triage_&_Assessments.py")

    # -------------------------------------------------------------------------
    # Mode 2: Asynchronous Background Queue (POST /reports + Polling)
    # -------------------------------------------------------------------------
    elif "Asynchronous" in submission_mode:
        with st.spinner("📤 Enqueuing report in Redis queue (/reports)..."):
            res = client.submit_report_async(payload)

        if not res["success"]:
            if res["status_code"] == 422:
                st.error("⛔ Report Rejected by Schema Validation Handler")
                st.markdown(f"**Validation Errors:**\n```\n{res['error']}\n```")
                record = {
                    "case_id": payload["case_id"],
                    "run_id": None,
                    "submission_mode": "async_queue",
                    "submitted_at": submitted_at,
                    "report_data": payload,
                    "status": "rejected",
                    "priority": "rejected",
                    "error": res["error"],
                }
                add_or_update_history_record(record)
            else:
                st.error(f"❌ Submission Failed (HTTP {res['status_code']}): {res['error']}")
        else:
            accept_data = res["data"]
            run_id = accept_data.get("run_id")
            st.info(f"Report accepted with Run ID: `{run_id}`. Enqueued in Redis.")

            # Record initial queued state
            record = {
                "case_id": payload["case_id"],
                "run_id": run_id,
                "submission_mode": "async_queue",
                "submitted_at": submitted_at,
                "report_data": payload,
                "status": "queued",
                "priority": "unknown",
            }
            add_or_update_history_record(record)

            # Polling widget
            status_container = st.empty()
            progress_bar = st.progress(10)

            run_result = None
            max_attempts = 15
            for attempt in range(max_attempts):
                status_container.markdown(
                    f"**Polling Status:** Attempt {attempt + 1}/{max_attempts} for Run `{run_id}`..."
                )
                progress_bar.progress(int(((attempt + 1) / max_attempts) * 100))

                poll_res = client.get_run_status(run_id)
                if poll_res["success"] and poll_res["data"]:
                    run_info = poll_res["data"]
                    curr_status = run_info.get("status")

                    if curr_status == "completed":
                        run_result = run_info
                        status_container.success(f"✅ Processing completed successfully for Run `{run_id}`!")
                        progress_bar.progress(100)
                        break
                    elif curr_status == "failed":
                        status_container.error(f"❌ Processing failed: {run_info.get('error')}")
                        record["status"] = "failed"
                        record["error"] = run_info.get("error")
                        add_or_update_history_record(record)
                        break
                    else:
                        status_container.info(f"⏳ Current Run Status: **{curr_status.upper()}**")

                time.sleep(1.0)

            if run_result and run_result.get("result"):
                final_result = run_result["result"]
                triage_res = final_result.get("triage_result") or {}
                verification_res = final_result.get("verification_result") or {}

                record["status"] = "completed"
                record["priority"] = triage_res.get("priority", "routine_human_review")
                record["verified"] = verification_res.get("verified", False)
                record["result"] = final_result
                record["backend_response"] = run_result
                add_or_update_history_record(record)
                st.session_state.active_case = record

                st.markdown(
                    f"**Triage Priority:** {render_priority_badge(record['priority'])}",
                    unsafe_allow_html=True,
                )
                if st.button("📊 Inspect Full Assessment Results", type="primary", use_container_width=True):
                    st.switch_page("pages/2_📊_Triage_&_Assessments.py")
            elif not run_result:
                st.warning(
                    f"Run `{run_id}` is still in state `{record['status']}`.\n\n"
                    "If the RQ worker (`python -m rq.cli worker --url redis://localhost:6379/0 pharmacovigilance`) is not running, "
                    "the job remains safely stored in Redis. You can inspect its status at any time from "
                    "the **Report History** or **System Diagnostics** page."
                )

    # -------------------------------------------------------------------------
    # Mode 3: Rule-Based Triage Only (POST /triage)
    # -------------------------------------------------------------------------
    else:
        with st.spinner("Evaluating rule-based triage (/triage)..."):
            res = client.assess_triage_sync(payload)

        if not res["success"]:
            st.error(f"❌ Triage Error: {res['error']}")
        else:
            triage_data = res["data"]
            triage_block = triage_data.get("triage") or triage_data
            priority = triage_block.get("priority", "routine_human_review")

            record = {
                "case_id": payload["case_id"],
                "run_id": None,
                "submission_mode": "triage_only",
                "submitted_at": submitted_at,
                "report_data": payload,
                "status": "completed",
                "priority": priority,
                "result": {"triage_result": triage_block},
                "backend_response": triage_data,
            }
            add_or_update_history_record(record)
            st.session_state.active_case = record

            st.success(f"✓ Fast triage completed for {payload['case_id']}!")
            st.markdown(f"**Assigned Priority:** {render_priority_badge(priority)}", unsafe_allow_html=True)
            signals = triage_block.get("signals", [])
            st.info(f"Detected {len(signals)} safety signals.")
            if st.button("📊 View Triage Breakdown", type="primary", use_container_width=True):
                st.switch_page("pages/2_📊_Triage_&_Assessments.py")
