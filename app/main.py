
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.evidence_triage import assess_with_evidence
from app.retrieval import search_evidence
from app.schemas import AdverseEventReport
from app.storage import quarantine_record
from app.triage import assess_triage
from app.workflow import run_workflow


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

METRICS = {
    "agent_runs_started": 0,
    "accepted_reports": 0,
    "rejected_reports": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Pharmacovigilance triage API starting")
    yield
    logger.info("Pharmacovigilance triage API shutting down")


app = FastAPI(
    title="Pharmacovigilance Adverse Event Intake and Triage Service",
    version="0.5.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    request_id = getattr(
        request.state,
        "request_id",
        str(uuid.uuid4()),
    )

    # Preserve invalid requests in quarantine for investigation.
    try:
        raw_body = await request.body()

        try:
            body = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {
                "unparsed_body": raw_body.decode(
                    "utf-8", errors="replace"
                )
            }

        safe_errors = jsonable_encoder(
            exc.errors(),
            custom_encoder={ValueError: str},
        )

        quarantine_record(
            body=body,
            errors=safe_errors,
            request_id=request_id,
        )

    except Exception:
        # Return the original validation response even if quarantine
        # storage fails.
        logger.exception(
            "Failed to save invalid request to quarantine. "
            "request_id=%s",
            request_id,
        )

    METRICS["rejected_reports"] += 1

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "status": "rejected",
                "detail": exc.errors(),
                "request_id": request_id,
                "message": (
                    "The submitted report failed schema validation "
                    "and was rejected."
                ),
            },
            custom_encoder={ValueError: str},
        ),
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
    }


@app.get("/metrics")
async def metrics():
    return METRICS.copy()


@app.post("/reports", status_code=202)
async def submit_report(report: AdverseEventReport):
    METRICS["accepted_reports"] += 1

    return {
        "case_id": report.case_id,
        "status": "accepted",
        "assessment_status": "not_started",
        "message": (
            "Report passed schema validation. "
            "This endpoint does not make a final medical or regulatory decision."
        ),
    }


@app.get("/evidence/search")
async def evidence_search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=500),
    top_k: int = Query(5, ge=1, le=10),
):
    request_id = getattr(
        request.state,
        "request_id",
        str(uuid.uuid4()),
    )

    try:
        results = search_evidence(q, top_k=top_k)

        return {
            "request_id": request_id,
            "query": q,
            "result_count": len(results),
            "results": results,
        }

    except (FileNotFoundError, OSError, ValueError):
        logger.exception(
            "Evidence search failed. request_id=%s",
            request_id,
        )

        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "query": q,
                "result_count": 0,
                "results": [],
                "message": (
                    "Evidence retrieval is temporarily unavailable."
                ),
            },
        )


@app.post("/triage")
async def triage_report(report: AdverseEventReport):
    result = assess_triage(report)

    return {
        "case_id": report.case_id,
        "triage": result,
        **result,
    }


@app.post("/triage/with-evidence")
async def triage_with_evidence(report: AdverseEventReport):
    request_id = str(uuid.uuid4())
    result = assess_with_evidence(report)

    return {
        "request_id": request_id,
        "case_id": report.case_id,
        **result,
    }


@app.post("/workflow/run")
async def run_agent_workflow(report: AdverseEventReport):
    request_id = str(uuid.uuid4())
    METRICS["agent_runs_started"] += 1

    try:
        result = run_workflow(report)

        return {
            "request_id": request_id,
            "case_id": report.case_id,
            "workflow_status": result.get("workflow_status", "unknown"),
            "triage_result": result.get("triage_result"),
            "evidence_result": result.get("evidence_result"),
            "verification_result": result.get("verification_result"),
            "errors": result.get("errors", []),
            "escalation": result.get("escalation"),
            "requires_qualified_review": True,
            "causality_assessed": False,
            "final_medical_decision": False,
        }

    except Exception:
        logger.exception(
            "Agent workflow failed. request_id=%s",
            request_id,
        )

        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "case_id": report.case_id,
                "workflow_status": "failed",
                "message": (
                    "The workflow could not complete. "
                    "Qualified human review is required."
                ),
                "requires_qualified_review": True,
                "final_medical_decision": False,
            },
        )
