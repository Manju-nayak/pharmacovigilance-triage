
from typing import Any

from app.schemas import AdverseEventReport
from app.triage import assess_triage
from app.workflow_state import TriageWorkflowState


def triage_agent(
    state: TriageWorkflowState,
) -> dict[str, Any]:
    """Run rule-based triage on a validated case report."""

    report_data = state.get("report")

    if (
        state.get("workflow_status") != "intake_completed"
        or not isinstance(report_data, dict)
    ):
        return {
            "workflow_status": "triage_skipped",
            "errors": state.get("errors", [])
            + ["Triage requires successfully completed intake."],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    try:
        report = AdverseEventReport.model_validate(report_data)
        triage_result = assess_triage(report)
    except (TypeError, ValueError, KeyError) as exc:
        return {
            "workflow_status": "triage_failed",
            "errors": state.get("errors", [])
            + [f"Triage could not process the report: {type(exc).__name__}"],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    return {
        "triage_result": triage_result,
        "workflow_status": "triage_completed",
        "requires_qualified_review": True,
        "escalation": "human_review_required",
    }
