from typing import Any
from app.workflow_state import TriageWorkflowState


def get_signal_names(signals: list) -> set:
    """Extract signal names for comparison."""
    return {
        item.get("signal")
        for item in signals
        if isinstance(item, dict) and item.get("signal")
    }


def verification_agent(state: TriageWorkflowState) -> dict[str, Any]:
    """Validate evidence structure and consistency with triage output."""

    errors = list(state.get("errors", []))
    evidence_result = state.get("evidence_result")
    triage_result = state.get("triage_result")

    if state.get("workflow_status") != "evidence_completed":
        errors.append("Evidence processing was incomplete.")

        return {
            "verification_result": {
                "verified": False,
                "evidence_found": False,
                "citations_valid": False,
                "consistency_checked": False,
                "consistency_valid": False,
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

    # Compare the Triage Agent output with the Evidence Agent output.
    consistency_checked = isinstance(triage_result, dict)
    consistency_valid = None

    if consistency_checked:
        triage_priority = triage_result.get("priority")
        evidence_priority = evidence_result.get("priority")

        triage_signals = triage_result.get("signals", [])
        evidence_signals = evidence_result.get("signals", [])

        priority_matches = (
            triage_priority is not None
            and triage_priority == evidence_priority
        )

        signals_match = (
            isinstance(triage_signals, list)
            and isinstance(evidence_signals, list)
            and get_signal_names(triage_signals)
            == get_signal_names(evidence_signals)
        )

        consistency_valid = priority_matches and signals_match

        if not consistency_valid:
            evidence_errors.append(
                "Evidence result does not match the original triage output."
            )
            errors.append(
                "Consistency check failed between triage and evidence results."
            )

    verified = (
        retrieval_status == "success"
        and evidence_found
        and citations_valid
        and consistency_valid is not False
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
        "consistency_checked": consistency_checked,
        "consistency_valid": consistency_valid,
        "reason": (
            "evidence_verification_checks_passed"
            if verified
            else "evidence_verification_failed"
        ),
        "semantic_support_verified": False,
        "limitations": [
            "Source, page, and text fields were checked.",
            "Triage priority and signal consistency were compared when available.",
            "These checks do not prove that a passage supports a medical claim.",
            "The original source must be checked by a qualified reviewer.",
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