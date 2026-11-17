# Pharmacovigilance Adverse Event Intake and Triage Service

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://python.langchain.com/)
[![Tests](https://img.shields.io/badge/Tests-52%20Passed-brightgreen.svg)]()

## 1. Project Overview

The **Pharmacovigilance Adverse Event Intake and Triage Service** is a clinical safety system designed to receive, validate, process, and prioritize synthetic Individual Case Safety Reports (ICSRs) related to medications.

The system provides an automated intake and preliminary triage pipeline using **FastAPI**, **Redis**, **RQ**, **LangGraph**, and a **Streamlit** healthcare frontend. It retrieves relevant safety information from an indexed corpus of package inserts and regulatory safety notices (such as CDSCO alerts) to assist safety officers in identifying reports requiring qualified human review.

> **Important Regulatory Notice:** This system is intended for demonstration and research using synthetic reports. It does not make final medical decisions, determine drug causality, or submit formal E2B regulatory reports. Qualified human review remains mandatory.

---

## 2. Key Features

- **Adverse Event Intake:** Accepts ICSR reports through REST API endpoints and a Streamlit UI.
- **Input Validation & Quarantine:** Validates fields with Pydantic; rejected reports are quarantined to `data/quarantine/`.
- **Dual Processing Pipelines:**
  - **Synchronous Workflow:** Executes the 4-agent LangGraph workflow immediately in-process.
  - **Asynchronous Queue:** Uses Redis and RQ for background worker execution and run polling.
- **Evidence Retrieval & Scoring:** Retrieves passages from indexed PDF safety notices and package inserts with keyword overlap scoring.
- **Rule-Based Triage:** Flags potential warning terms (SJS, TEN, anaphylaxis) and reported outcomes (hospitalization, death).
- **Seriousness & Expectedness Evaluation:** Distinguishes reported regulatory seriousness criteria from preliminary text signals; guides human expectedness review against official package inserts.
- **Interactive Streamlit Dashboard:** Multi-page clinical frontend featuring live metrics, scenario presets, literature search, and case history.

---

## 3. System Architecture

```text
                           [Client / Streamlit Frontend]
                                         │
                                         ▼
                                [FastAPI API Layer]
                                         │
                                [Pydantic Validation]
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼ (Valid)                                 ▼ (Invalid)
        ┌───────────┴───────────┐                     [Quarantine Storage]
        ▼ (Sync)                ▼ (Async)              (data/quarantine/)
  [/workflow/run]          [/reports]
        │                       │
        │                  [Redis Queue]
        │                       │
        ▼                       ▼
  [LangGraph Multi-Agent] ◄── [RQ Worker]
  ├─ Intake Agent
  ├─ Triage Agent
  ├─ Evidence Agent ──────► [Indexed Medical Corpus]
  └─ Verification Agent     (data/corpus/evidence_index.json)
        │
        ▼
  [Assessment Result] ────► [Redis Run Store] ──► [/runs/{run_id}]
```

### Multi-Agent LangGraph Workflow

| Agent | Responsibility |
|---|---|
| **Intake Agent** | Validates report structure and ensures case integrity before processing. |
| **Triage Agent** | Scans for high-urgency keywords and assigns review priority (`urgent_human_review` vs `routine_human_review`). |
| **Evidence Agent** | Retrieves ranked passages from the indexed medical corpus, preserving overlap scores. |
| **Verification Agent** | Audits citation validity, traceability, and documents structural limitations. |

---

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Backend and frontend programming |
| **FastAPI** | REST API development |
| **Streamlit** | Clinical healthcare frontend |
| **Pydantic v2** | Request validation and data schemas |
| **LangGraph** | Multi-agent workflow orchestration |
| **Redis** | Queue and run-status storage |
| **RQ (Redis Queue)** | Background job processing |
| **PyPDF & Pytesseract** | PDF text extraction and OCR fallback |
| **Pytest** | Automated test suite (52 tests) |
| **Docker Compose** | Multi-container deployment |

---

## 5. Project Structure

```text
pharmacovigilance-triage/
├── app/                                 # FastAPI Backend Service
│   ├── main.py                          # API endpoints, middleware, validation handler
│   ├── schemas.py                       # Pydantic AdverseEventReport schema
│   ├── storage.py                       # Quarantine storage handler
│   ├── queue.py                         # Redis Queue (RQ) configuration
│   ├── run_store.py                     # Redis run status persistence
│   ├── worker.py                        # RQ background worker job
│   ├── retrieval.py                     # Corpus keyword search & scoring
│   ├── triage.py                        # Rule-based safety signal evaluation
│   ├── evidence_triage.py               # Triage combined with scored evidence
│   ├── workflow.py                      # LangGraph multi-agent graph compilation
│   ├── workflow_state.py                # Shared workflow state dictionary
│   ├── intake_agent.py                  # Intake agent node
│   ├── triage_agent.py                  # Triage agent node
│   ├── evidence_agent.py                # Evidence agent node
│   └── verification_agent.py            # Verification agent node
│
├── frontend/                            # Streamlit Web Application
│   ├── app.py                           # Executive Dashboard & KPI Overview
│   ├── api_client.py                    # Centralized HTTP Client for FastAPI
│   ├── config.py                        # Configuration & scenario presets
│   ├── requirements.txt                 # Frontend dependencies
│   ├── README.md                        # Frontend documentation
│   ├── assets/
│   │   └── style.css                    # Healthcare UI theme
│   ├── utils/
│   │   ├── session.py                   # Persistent audit log & state management
│   │   ├── ui_components.py             # UI badges, steppers & citation cards
│   │   └── validators.py                # Client-side form validation
│   ├── pages/
│   │   ├── 1_📥_Submit_Report.py         # Adverse Event Intake form with presets
│   │   ├── 2_📊_Triage_&_Assessments.py  # Safety signals, seriousness & citations
│   │   ├── 3_📋_Report_History.py       # Case audit log & quarantined rejections
│   │   ├── 4_🔍_Evidence_Explorer.py    # Direct literature search across corpus
│   │   └── 5_⚙️_System_Health.py        # Backend diagnostics & latency monitor
│   └── tests/
│       ├── test_frontend.py             # UI, preset & validation unit tests
│       ├── test_live_server_integration.py # Live HTTP integration tests
│       └── test_streamlit_boot.py       # Streamlit headless boot test
│
├── data/
│   ├── corpus/                          # Reference PDFs & evidence_index.json
│   └── quarantine/                      # Quarantined invalid submissions
│
├── tests/                               # Backend Pytest suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── build_index.py                       # Corpus index builder with OCR fallback
└── README.md
```

---

## 6. Local Installation & Execution

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

### Step 2: Start FastAPI Backend (Terminal 1)

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Docs (Swagger):** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/health`
- **Metrics:** `http://127.0.0.1:8000/metrics`

*(Note: Running `python -m uvicorn` avoids Windows Application Control / AppLocker policy restrictions).*

### Step 3: (Optional) Start RQ Worker for Async Queue (Terminal 2)

```bash
python -m rq.cli worker --url redis://localhost:6379/0 pharmacovigilance
```

*(Required only when testing asynchronous queue mode; synchronous multi-agent mode runs directly in-process without RQ).*

### Step 4: Start Streamlit Frontend (Terminal 3)

```bash
python -m streamlit run frontend/app.py --server.port 8501
```

- **Healthcare Dashboard:** `http://localhost:8501`

---

## 7. Running via Docker Compose

To start FastAPI, Redis, and the RQ worker in containers:

```bash
docker compose up --build
```

---

## 8. Automated Testing

Run the complete test suite (52 tests covering backend, live server integration, evidence scoring, form validation, and Streamlit boot):

```bash
python -m pytest tests/ frontend/tests/ -v
```

---

## 9. System Limitations & Architecture Notes

1. **In-Memory Operational Metrics (`/metrics`):**
   The `METRICS` counter (`accepted_reports`, `rejected_reports`, `agent_runs_started`) is maintained in the FastAPI server process memory. It resets when the API process restarts and is local to each server worker process.
2. **Local JSON History (`frontend/data/history.json`):**
   Case submissions in the Streamlit UI are cached locally on disk in `frontend/data/history.json` to persist across browser refreshes. This is intended for single-instance or local evaluation. In distributed production environments, an external database (e.g. PostgreSQL) should be used.
3. **Redis Run Key TTL:**
   Runs stored in Redis (`pharmacovigilance:run:{run_id}`) persist according to Redis configuration. If Redis is restarted without persistence (AOF/RDB), active runs will be cleared.
4. **Clinical Governance:**
   This service is a research prototype using synthetic data. It assists preliminary workflow prioritization and does not diagnose, establish medical causality, or replace qualified medical judgment.
