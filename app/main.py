
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import AdverseEventReport
from app.storage import quarantine_record
from app.retrieval import search_evidence


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent_runs_started = 0
    app.state.accepted_reports = 0
    app.state.rejected_reports = 0
    yield


app = FastAPI(
    title="Pharmacovigilance Intake and Triage Service",
    version="0.2.0",
    description=(
        "Synthetic adverse-event intake and evidence retrieval API. "
        "Evidence search is informational and does not make "
        "medical or regulatory determinations."
    ),
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
        "version": "0.2.0",
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


@app.get("/evidence/search")
async def evidence_search(
    request: Request,
    q: str = Query(
        ...,
        min_length=2,
        max_length=500,
        description="Keywords to search in the evidence corpus.",
    ),
    top_k: int = Query(5, ge=1, le=10),
):
    try:
        results = search_evidence(q, top_k=top_k)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Evidence index is unavailable.",
        )
    except (OSError, ValueError):
        raise HTTPException(
            status_code=500,
            detail="Evidence search failed.",
        )

    return {
        "request_id": request.state.request_id,
        "query": q,
        "result_count": len(results),
        "results": [
            {
                "source": result["source"],
                "page": result["page"],
                "extraction_method": result["extraction_method"],
                "matched_terms": result["matched_terms"],
                "keyword_overlap_score": round(result["score"], 3),
                "text": result["text"],
            }
            for result in results
        ],
        "notice": (
            "Keyword overlap is not medical confidence or proof "
            "of causality. Verify each passage against its source. "
            "This endpoint does not make medical or regulatory decisions."
        ),
    }
