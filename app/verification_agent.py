
from typing import Any

from app.workflow_state import TriageWorkflowState


def verification_agent(
    state: TriageWorkflowState,
) -> dict[str, Any]:
    """Check workflow outputs and record evidence limitations."""

    errors = list(state.get("errors", []))
    evidence_result = state.get("evidence_result")

    if state.get("workflow_status") != "evidence_completed":
        errors.append(
            "Verification could not confirm successful evidence processing."
        )

        return {
            "verification_result": {
                "verified": False,
                "reason": "evidence_processing_incomplete",
                "evidence_found": False,
            },
            "workflow_status": "verification_incomplete",
            "errors": errors,
            "requires_qualified_review": True,
            "escalation": "human_review_required",
        }

    if not isinstance(evidence_result, dict):
        evidence_result = {}

    evidence = evidence_result.get("evidence", [])
    evidence_found = isinstance(evidence, list) and len(evidence) > 0

    retrieval_status = evidence_result.get("retrieval_status", "unknown")

    limitations = []

    if not evidence_found:
        limitations.append("No supporting evidence passages were returned.")

    if retrieval_status != "success":
        limitations.append(
            f"Evidence retrieval status is {retrieval_status}."
        )

    verification_result = {
        "verified": True,
        "evidence_found": evidence_found,
        "retrieval_status": retrieval_status,
        "limitations": limitations,
        "causality_assessed": False,
        "final_medical_decision": False,
    }

    return {
        "verification_result": verification_result,
        "workflow_status": "verification_completed",
        "requires_qualified_review": True,
        "escalation": "human_review_required",
    }
