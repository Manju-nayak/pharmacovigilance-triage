
from app.workflow import (
    triage_workflow,
    MAX_EVIDENCE_RETRIES,
    prepare_evidence_retry,
    route_after_verification,
)


def test_complete_workflow_runs_in_order():
    initial_state = {
        "request_id": "test-request-001",
        "report": {
            "case_id": "SYN-WORKFLOW-001",
            "drug_name": "carbamazepine",
            "reaction_description": (
                "Severe skin peeling reported after starting the medicine."
            ),
            "patient_age": 35,
            "reporter_type": "patient",
            "outcome": "recovering",
            "event_onset_days": 7,
            "hospitalization": True,
            "death": False,
        },
        "errors": [],
    }

    result = triage_workflow.invoke(initial_state)

    assert result["workflow_status"] == "verification_completed"
    assert result["case_id"] == "SYN-WORKFLOW-001"
    assert result["triage_result"]["priority"] == "urgent_human_review"
    assert "evidence_result" in result
    assert "verification_result" in result
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"


def test_workflow_handles_missing_report():
    result = triage_workflow.invoke({
        "errors": [],
    })

    assert result["workflow_status"] == "verification_incomplete"
    assert result["verification_result"]["verified"] is False
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"


def test_workflow_does_not_claim_verification_success_without_evidence():
    from unittest.mock import patch

    with patch(
        "app.evidence_triage.search_evidence",
        return_value=[],
    ):
        result = triage_workflow.invoke({
            "request_id": "test-no-evidence",
            "report": {
                "case_id": "SYN-WORKFLOW-002",
                "drug_name": "example-drug",
                "reaction_description": "Mild nausea after use.",
                "patient_age": 35,
                "reporter_type": "patient",
                "outcome": "recovering",
                "event_onset_days": 2,
                "hospitalization": False,
                "death": False,
            },
            "workflow_status": "started",
            "errors": [],
        })

    assert result["verification_result"]["verified"] is False
    assert result["workflow_status"] == "verification_failed"
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"


def test_failed_verification_recommends_one_retry():
    state = {
        "retry_count": 0,
        "retry_recommended": True,
        "triage_result": {"priority": "urgent_human_review"},
    }

    assert route_after_verification(state) == "retry_evidence"


def test_retry_increments_retry_count():
    state = {
        "retry_count": 0,
        "workflow_status": "verification_failed",
    }

    result = prepare_evidence_retry(state)

    assert result["retry_count"] == 1
    assert result["workflow_status"] == "triage_completed"


def test_retry_stops_after_maximum_attempts():
    state = {
        "retry_count": MAX_EVIDENCE_RETRIES,
        "retry_recommended": True,
        "triage_result": {"priority": "urgent_human_review"},
    }

    assert route_after_verification(state) == "end"
