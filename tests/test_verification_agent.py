
from app.verification_agent import verification_agent


def test_verification_with_evidence():
    state = {
        "workflow_status": "evidence_completed",
        "evidence_result": {
            "retrieval_status": "success",
            "evidence": [
                {
                    "source": "synthetic_test_document.pdf",
                    "page": 1,
                    "text": "Synthetic evidence passage for testing.",
                }
            ],
        },
        "errors": [],
    }

    result = verification_agent(state)

    assert result["workflow_status"] == "verification_completed"
    assert result["verification_result"]["verified"] is True
    assert result["verification_result"]["evidence_found"] is True
    assert result["verification_result"]["causality_assessed"] is False
    assert result["requires_qualified_review"] is True


def test_verification_without_evidence():
    state = {
        "workflow_status": "evidence_completed",
        "evidence_result": {
            "retrieval_status": "no_results",
            "evidence": [],
        },
        "errors": [],
    }

    result = verification_agent(state)

    assert result["workflow_status"] == "verification_completed"
    assert result["verification_result"]["evidence_found"] is False
    assert len(result["verification_result"]["limitations"]) > 0
    assert result["escalation"] == "human_review_required"


def test_verification_when_evidence_processing_incomplete():
    state = {
        "workflow_status": "evidence_failed",
        "errors": [],
    }

    result = verification_agent(state)

    assert result["workflow_status"] == "verification_incomplete"
    assert result["verification_result"]["verified"] is False
    assert result["requires_qualified_review"] is True
