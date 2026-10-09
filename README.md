
# Pharmacovigilance Adverse Event Intake and Triage Service

**Course:** ML System Design & AgentOps  
**Mini Project:** 14  
**Phase:** 1 — Project Foundation

## 1. Project Overview

This project builds a service for accepting and validating synthetic
adverse-event reports about medicines.

The planned system will retrieve evidence from official drug-safety
documents, support seriousness and expectedness assessments, verify
citations, and recommend an appropriate reporting route.

The current Phase 1 implementation handles request validation and
quarantines invalid requests. It does not yet perform medical
assessments or submit regulatory reports.

## 2. Technology Stack

- Python
- FastAPI
- Pydantic
- Uvicorn
- Pytest
- HTTPX

## 3. Project Structure

```text
pharmacovigilance-triage/
├── app/
│   ├── schemas.py
│   ├── storage.py
│   └── main.py
├── tests/
│   └── test_api.py
├── data/
│   └── quarantine/
├── requirements.txt
├── .gitignore
└── README.md
```

## 4. Setup on Windows

Open a terminal in the project directory.

Create a virtual environment:

```powershell
py -3.14 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## 5. Run the API

```powershell
python -m uvicorn app.main:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

## 6. Available Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Check service health |
| GET | /metrics | View development counters |
| POST | /reports | Validate a synthetic report |

## 7. Run Automated Tests

```powershell
python -m pytest -v
```

## 8. Data Safety

Use synthetic case reports only. Do not enter real patient or
case data.

The service does not submit regulatory reports. Any future
pharmacovigilance assessment must be reviewed by a qualified person.
