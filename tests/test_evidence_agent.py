
from app.evidence_agent import evidence_agent


def test_evidence_agent_retrieves_evidence():
    state = {
        "report": {
            "case_id": "SYN-EVIDENCE-001",
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
        "workflow_status": "triage_completed",
        "errors": [],
    }

    result = evidence_agent(state)

    assert result["workflow_status"] == "evidence_completed"
    assert "evidence_result" in result
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"
    assert result["evidence_result"]["causality_assessed"] is False


def test_evidence_agent_skips_before_triage():
    state = {
        "report": {"case_id": "SYN-EVIDENCE-002"},
        "workflow_status": "intake_completed",
        "errors": [],
    }

    result = evidence_agent(state)

    assert result["workflow_status"] == "evidence_skipped"
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"


def test_evidence_agent_handles_missing_report():
    result = evidence_agent({
        "workflow_status": "triage_completed",
        "errors": [],
    })

    assert result["workflow_status"] == "evidence_skipped"
    assert result["requires_qualified_review"] is True
