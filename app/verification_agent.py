
from typing import Any
from app.workflow_state import TriageWorkflowState


def verification_agent(state: TriageWorkflowState) -> dict[str, Any]:
    """Validate evidence structure and flag cases for qualified review."""

    errors = list(state.get("errors", []))
    evidence_result = state.get("evidence_result")

    if state.get("workflow_status") != "evidence_completed":
        errors.append("Evidence processing was incomplete.")

        return {
            "verification_result": {
                "verified": False,
                "evidence_found": False,
                "citations_valid": False,
                "reason": "evidence_processing_incomplete",
                "semantic_support_verified": False,
                "causality_assessed": False,
                "final_medical_decision": False,
            },
            "workflow_status": "verification_incomplete",
            "errors": errors,
            "requires_qualified_review": True,
            "escalation": "human_review_required",
            "retry_recommended": True,
        }

    if not isinstance(evidence_result, dict):
        evidence_result = {}

    evidence = evidence_result.get("evidence", [])
    retrieval_status = evidence_result.get("retrieval_status", "unknown")
    valid_passages = []
    evidence_errors = []

    if not isinstance(evidence, list):
        evidence_errors.append("Evidence must be a list.")
        evidence = []

    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            evidence_errors.append(
                f"Evidence item {index} is not a dictionary."
            )
            continue

        source = item.get("source")
        page = item.get("page")
        passage = item.get("text")

        source_valid = isinstance(source, str) and bool(source.strip())
        page_valid = (
            isinstance(page, int)
            and not isinstance(page, bool)
            and page > 0
        )
        text_valid = isinstance(passage, str) and bool(passage.strip())

        if source_valid and page_valid and text_valid:
            valid_passages.append(item)
        else:
            evidence_errors.append(
                f"Evidence item {index} has invalid source, page, or text."
            )

    citations_valid = (
        len(evidence) > 0
        and len(valid_passages) == len(evidence)
    )
    evidence_found = len(valid_passages) > 0
    verified = (
        retrieval_status == "success"
        and evidence_found
        and citations_valid
    )

    if not verified:
        errors.extend(evidence_errors)
        errors.append(
            "Evidence verification failed; qualified human review is required."
        )

    result = {
        "verified": verified,
        "evidence_found": evidence_found,
        "citations_valid": citations_valid,
        "retrieval_status": retrieval_status,
        "valid_passage_count": len(valid_passages),
        "invalid_passage_count": len(evidence_errors),
        "reason": (
            "evidence_traceability_checks_passed"
            if verified
            else "evidence_verification_failed"
        ),
        "semantic_support_verified": False,
        "limitations": [
            "Source, page, and text fields were checked.",
            "These checks do not prove that a passage supports a medical claim.",
            "The original source must be checked to confirm citation traceability.",
        ],
        "causality_assessed": False,
        "final_medical_decision": False,
    }

    return {
        "verification_result": result,
        "workflow_status": (
            "verification_completed" if verified else "verification_failed"
        ),
        "errors": errors,
        "requires_qualified_review": True,
        "escalation": "human_review_required",
        "retry_recommended": not verified,
    }
