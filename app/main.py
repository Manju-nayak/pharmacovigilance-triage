
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import AdverseEventReport
from app.storage import quarantine_record


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent_runs_started = 0
    app.state.accepted_reports = 0
    app.state.rejected_reports = 0
    yield


app = FastAPI(
    title="Pharmacovigilance Intake and Triage Service",
    version="0.1.0",
    description="Phase 1 intake API. Synthetic cases only.",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
):
    request_id = request.state.request_id

    errors = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    try:
        rejected = quarantine_record(
            body=exc.body,
            errors=errors,
            request_id=request_id,
        )
    except (OSError, TypeError, ValueError):
        request.app.state.rejected_reports += 1
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "status": "quarantine_failed",
                "detail": "Rejected request could not be saved.",
            },
        )

    request.app.state.rejected_reports += 1

    return JSONResponse(
        status_code=422,
        content={
            "request_id": request_id,
            "status": "rejected",
            "detail": "Validation failed. No agent run started.",
            "quarantine_id": rejected["quarantine_id"],
            "errors": errors,
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "pharmacovigilance-intake",
        "version": "0.1.0",
    }


@app.get("/metrics")
async def metrics(request: Request):
    return {
        "accepted_reports": request.app.state.accepted_reports,
        "rejected_reports": request.app.state.rejected_reports,
        "agent_runs_started": request.app.state.agent_runs_started,
    }


@app.post("/reports", status_code=202)
async def submit_report(
    report: AdverseEventReport,
    request: Request,
):
    request.app.state.accepted_reports += 1

    return {
        "request_id": request.state.request_id,
        "case_id": report.case_id,
        "status": "accepted",
        "assessment_status": "not_started",
        "message": (
            "Synthetic report passed validation. "
            "No medical determination has been made."
        ),
    }
