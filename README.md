# Pharmacovigilance Adverse Event Intake and Triage Service

## 1. Project Overview

The **Pharmacovigilance Adverse Event Intake and Triage Service** is a backend system designed to receive, validate, process, and prioritize synthetic adverse event reports related to medications.

The system provides an automated intake and preliminary triage pipeline using FastAPI, Redis, RQ, and LangGraph. It retrieves relevant safety information from reference documents and assists in identifying reports that require qualified human review.

The project focuses on improving the organization and preliminary assessment of adverse event reports while maintaining human oversight.

> **Important:** This system is intended for demonstration and research using synthetic reports. It does not make final medical decisions, establish drug causality, or submit regulatory reports.

## 2. Key Features

- **Adverse Event Intake:** Accepts adverse event reports through REST API endpoints.
- **Input Validation:** Validates report fields using Pydantic.
- **Invalid Report Quarantine:** Stores rejected reports separately for inspection.
- **Asynchronous Processing:** Uses Redis and RQ to process accepted reports in the background.
- **Run Status Tracking:** Provides run IDs to track report-processing status.
- **Evidence Retrieval:** Retrieves relevant information from indexed PDF reference documents.
- **Automated Triage:** Identifies potential seriousness signals using rule-based logic.
- **Evidence-Based Assessment:** Combines triage results with retrieved reference information.
- **Multi-Agent Workflow:** Uses LangGraph to coordinate intake, triage, evidence retrieval, and verification agents.
- **Human Review:** Flags reports requiring qualified human review.
- **Monitoring:** Provides health-check and metrics endpoints.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Backend programming |
| FastAPI | REST API development |
| Pydantic | Request validation and data schemas |
| Redis | Queue and run-status storage |
| RQ (Redis Queue) | Background job processing |
| LangGraph | Multi-agent workflow orchestration |
| PyPDF | PDF text extraction |
| Pytest | Automated testing |
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| Swagger UI | API documentation and testing |

## 4. System Architecture

The application consists of three main services:

1. **API Service (FastAPI):** Receives reports, validates requests, manages API endpoints, and submits background jobs.
2. **Redis Service:** Stores queued jobs and report-processing status.
3. **Worker Service (RQ):** Retrieves queued jobs and executes the report-processing workflow.

### Report Processing Flow

```text
             Client
               |
               v
        FastAPI Application
               |
               v
       Input Validation
               |
         +-----+-----+
         |           |
      Invalid       Valid
         |           |
         v           v
     Quarantine   Create Run ID
                     |
                     v
                Redis Queue
                     |
                     v
                RQ Worker
                     |
                     v
              LangGraph Workflow
                     |
          +----------+----------+
          |          |          |
          v          v          v
        Intake     Triage     Evidence
        Agent      Agent      Agent
                                |
                                v
                         Verification Agent
                                |
                                v
                         Processing Result
                                |
                                v
                         Run Status Update
```

## 5. Multi-Agent Workflow

The LangGraph workflow consists of four agents:

| Agent | Responsibility |
|---|---|
| Intake Agent | Checks whether the report is available and valid for processing. |
| Triage Agent | Identifies potential seriousness signals and assigns review priority. |
| Evidence Agent | Retrieves relevant safety information from the evidence index. |
| Verification Agent | Checks evidence availability and required evidence structure. |

The agents work together through a shared workflow state managed by LangGraph.

The workflow does not establish medical causality or make final medical decisions.

## 6. Project Structure

```text
pharmacovigilance-triage/
│
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── storage.py
│   ├── queue.py
│   ├── run_store.py
│   ├── worker.py
│   ├── retrieval.py
│   ├── triage.py
│   ├── evidence_triage.py
│   ├── workflow.py
│   ├── workflow_state.py
│   ├── intake_agent.py
│   ├── triage_agent.py
│   ├── evidence_agent.py
│   └── verification_agent.py
│
├── data/
│   ├── corpus/
│   │   ├── Reference PDF documents
│   │   └── evidence_index.json
│   └── quarantine/
│
├── tests/
│   ├── test_api.py
│   ├── test_evidence_agent.py
│   ├── test_evidence_triage.py
│   ├── test_intake_agent.py
│   ├── test_retrieval.py
│   ├── test_triage.py
│   ├── test_triage_agent.py
│   ├── test_verification_agent.py
│   └── test_workflow.py
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── build_index.py
├── extract_corpus.py
└── README.md
```

## 7. Installation and Execution

### Prerequisites

- Git
- Docker Desktop
- Docker Compose

### Step 1: Clone the Repository

```bash
git clone https://github.com/Manju-nayak/pharmacovigilance-triage.git
```

### Step 2: Navigate to the Project

```bash
cd pharmacovigilance-triage
```

### Step 3: Build and Start the Services

```bash
docker compose up --build
```

This