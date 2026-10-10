
from app.triage_agent import triage_agent


def test_urgent_report_is_flagged():
    state = {
        "report": {
            "case_id": "SYN-TRIAGE-001",
            "drug_name": "ExampleDrug",
            "reaction_description": "Severe skin peeling reported.",
            "patient_age": 35,
            "reporter_type": "patient",
            "outcome": "recovering",
            "event_onset_days": 7,
            "hospitalization": True,
            "death": False,
        },
        "workflow_status": "intake_completed",
        "errors": [],
    }

    result = triage_agent(state)

    assert result["workflow_status"] == "triage_completed"
    assert result["triage_result"]["priority"] == "urgent_human_review"
    assert result["requires_qualified_review"] is True


def test_triage_skips_when_intake_not_completed():
    state = {
        "report": {"case_id": "SYN-TRIAGE-002"},
        "workflow_status": "intake_failed",
        "errors": [],
    }

    result = triage_agent(state)

    assert result["workflow_status"] == "triage_skipped"
    assert result["escalation"] == "human_review_required"


def test_triage_handles_missing_report():
    result = triage_agent({
        "workflow_status": "intake_completed",
        "errors": [],
    })

    assert result["workflow_status"] == "triage_skipped"
    assert result["requires_qualified_review"] is True
