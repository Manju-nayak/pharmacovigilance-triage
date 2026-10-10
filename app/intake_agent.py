
from typing import Any

from app.workflow_state import TriageWorkflowState


def intake_agent(
    state: TriageWorkflowState,
) -> dict[str, Any]:
    """Prepare a validated case report for the triage workflow."""

    report = state.get("report")

    if not isinstance(report, dict) or not report:
        return {
            "workflow_status": "intake_failed",
            "errors": state.get("errors", [])
            + ["A validated case report is required."],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    case_id = report.get("case_id")

    if not case_id:
        return {
            "workflow_status": "intake_failed",
            "errors": state.get("errors", [])
            + ["The case report is missing its case ID."],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    return {
        "case_id": case_id,
        "workflow_status": "intake_completed",
        "requires_qualified_review": True,
        "escalation": "human_review_required",
    }
