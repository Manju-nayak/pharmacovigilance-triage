from typing import Any

from app.evidence_triage import assess_with_evidence
from app.schemas import AdverseEventReport
from app.workflow_state import TriageWorkflowState


def evidence_agent(state: TriageWorkflowState) -> dict[str, Any]:
    """Retrieve evidence for a triaged adverse-event report."""

    report_data = state.get("report")
    errors = list(state.get("errors", []))

    if (
        state.get("workflow_status") != "triage_completed"
        or not isinstance(report_data, dict)
    ):
        return {
            "workflow_status": "evidence_skipped",
            "errors": errors + [
                "Evidence retrieval requires completed triage."
            ],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    try:
        report = AdverseEventReport.model_validate(report_data)
        retry_count = state.get("retry_count", 0)

        evidence_result = assess_with_evidence(
            report,
            retry_count=retry_count,
        )

    except (TypeError, ValueError, KeyError, OSError) as exc:
        return {
            "workflow_status": "evidence_failed",
            "errors": errors + [
                f"Evidence processing failed: {type(exc).__name__}"
            ],
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    return {
        "evidence_result": evidence_result,
        "workflow_status": "evidence_completed",
        "errors": errors,
        "requires_qualified_review": True,
        "escalation": "human_review_required",
    }