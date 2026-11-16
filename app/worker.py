
import logging

from app.run_store import update_run
from app.schemas import AdverseEventReport
from app.workflow import run_workflow


logger = logging.getLogger(__name__)


def process_report(run_id: str, report_data: dict):
    """
    Process an adverse-event report in the background.

    Updates the Redis run record as processing progresses.
    """

    logger.info("Starting report processing. run_id=%s", run_id)

    try:
        # Mark the job as running.
        update_run(
            run_id,
            status="running",
            error=None,
        )

        # Reconstruct and validate the report.
        report = AdverseEventReport.model_validate(report_data)

        # Execute the existing LangGraph workflow.
        result = run_workflow(report)

        # Save the completed workflow result.
        update_run(
            run_id,
            status="completed",
            result=result,
            error=None,
            requires_qualified_review=True,
            final_medical_decision=False,
        )

        logger.info(
            "Report processing completed. run_id=%s",
            run_id,
        )

        return {
            "run_id": run_id,
            "status": "completed",
        }

    except Exception as exc:
        logger.exception(
            "Report processing failed. run_id=%s",
            run_id,
        )

        update_run(
            run_id,
            status="failed",
            error=str(exc),
            requires_qualified_review=True,
            final_medical_decision=False,
        )

        # Re-raise so RQ also marks the job as failed.
        raise
