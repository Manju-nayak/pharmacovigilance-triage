# Pharmacovigilance Triage Dashboard (Streamlit Frontend)

This directory contains the Streamlit-based web frontend for the **Pharmacovigilance Adverse Event Intake and Triage Service**.

---

## 1. Architecture Overview

The frontend is completely decoupled from the FastAPI backend, communicating strictly via HTTP REST endpoints.

```text
frontend/
├── app.py                      # Main Executive Healthcare Dashboard & KPIs
├── api_client.py               # Robust HTTP client wrapping all FastAPI endpoints
├── config.py                   # Config (BACKEND_URL, timeouts, clinical scenario presets)
├── requirements.txt            # Frontend Python dependencies
├── assets/
│   └── style.css               # Clinical Healthcare Theme CSS (badges, KPI cards, alerts)
├── utils/
│   ├── session.py              # Persistent audit log (frontend/data/history.json) & state
│   └── ui_components.py        # Reusable UI widgets, badges, steppers, and citation cards
├── pages/
│   ├── 1_📥_Submit_Report.py       # Adverse Event Intake form with presets & validation
│   ├── 2_📊_Triage_&_Assessments.py # Deep dive into Triage, Seriousness, Citations & Agent Verification
│   ├── 3_📋_Report_History.py      # Case audit history, filterable table, JSON inspection, export
│   ├── 4_🔍_Evidence_Explorer.py   # Direct search into indexed CDSCO / package inserts
│   └── 5_⚙️_System_Health.py       # Live API connectivity, health check & metrics monitor
└── tests/
    ├── test_frontend.py                # Unit tests for UI components, presets & schemas
    ├── test_live_server_integration.py # Real HTTP integration tests with live FastAPI server
    └── test_streamlit_boot.py          # Headless boot & health probe test for Streamlit
```

---

## 2. Key Features

1. **Executive Healthcare Dashboard (`app.py`):**
   - Live backend connectivity monitor (`/health`)
   - KPI metrics: Total Ingested Cases, Urgent Priority Flags, Routine Cases, LangGraph Agent Runs (`/metrics`), and Quarantined Ingestion Failures
   - Active Triage Queue with one-click drill-down

2. **Adverse Event Report Intake (`pages/1_📥_Submit_Report.py`):**
   - Strict adherence to backend `AdverseEventReport` Pydantic schema
   - Client-side validation guardrails (e.g. cross-field consistency for Death outcome)
   - 1-click Clinical Scenario presets:
     - *Carbamazepine SJS/TEN (Urgent Review)*
     - *Routine Mild Dermatitis (Routine Review)*
     - *Fatal Reaction Event (Death)*
     - *Pediatric Dyspnea (Urgent Review)*
     - *Malformed Schema Demo (Age < 0, triggers 422 quarantine)*
   - Dual processing workflows:
     - **Synchronous Multi-Agent Workflow (`/workflow/run`):** Immediate 4-agent LangGraph execution
     - **Asynchronous Queue Submission (`/reports`):** Enqueues in Redis RQ with live polling on `/runs/{run_id}`
     - **Rule-Based Triage (`/triage`):** Fast signal evaluation

3. **Triage, Seriousness & Evidence Assessments (`pages/2_📊_Triage_&_Assessments.py`):**
   - Visual 4-node pipeline stepper (`Intake -> Triage -> Evidence -> Verification`)
   - Triggered safety signals with highlighted clinical terms (`reported_death`, `reported_hospitalization`, `potentially_serious_reaction_text`)
   - **Seriousness Classification:** Formal ICH E2A evaluation directly derived from actual backend signals
   - **Expectedness Assessment:** Honest, compliant representation (clarifies that automated expectedness is not computed by backend and points human reviewers to package insert passages)
   - Retrieved evidence citation cards with source filename, page number, extraction method, keyword overlap score, and highlighted excerpt
   - Verification Agent scorecard: citation validity, traceability checks, audit limitations

4. **Report History & Audit Trail (`pages/3_📋_Report_History.py`):**
   - Persistent case storage in `frontend/data/history.json`
   - Real-time status sync with Redis runs (`/runs/{run_id}`)
   - Quarantined Rejections inspection tab (reading `data/quarantine/`)
   - Search & filtering by Priority, Run Status, Drug Name, or Case ID
   - Export to JSON and CSV

5. **Evidence Explorer (`pages/4_🔍_Evidence_Explorer.py`):**
   - Direct query interface into `/evidence/search` across CDSCO safety notices and drug package inserts
   - Configurable `top_k` slider and sample clinical queries

6. **System Health & Telemetry (`pages/5_⚙️_System_Health.py`):**
   - Base URL configuration
   - Live backend diagnostics and endpoint latency measurements
   - Redis & RQ worker status instructions

---

## 3. Running Backend and Frontend Locally

### Prerequisites
- Python 3.11+
- Redis (optional for synchronous workflow, required for asynchronous RQ worker)

### Step 1: Install Dependencies
```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
pip install -r frontend/requirements.txt
```

### Step 2: Start Backend (Terminal 1)
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*(Note: Using `python -m uvicorn` avoids Windows Application Control / AppLocker restrictions on standalone `uvicorn.exe` scripts).*
The FastAPI documentation will be accessible at: `http://127.0.0.1:8000/docs`

### Step 3: (Optional) Start RQ Worker for Async Queue (Terminal 2)
```bash
python -m rq.cli worker --url redis://localhost:6379/0 pharmacovigilance
```

### Step 4: Start Streamlit Frontend (Terminal 3)
```bash
python -m streamlit run frontend/app.py --server.port 8501
```
The Streamlit healthcare dashboard will open at: `http://localhost:8501`

---

## 4. Running Automated Tests

```bash
# Run all tests (backend + frontend integration)
python -m pytest tests/ frontend/tests/ -v
```
