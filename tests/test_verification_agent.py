
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

    assert result["workflow_status"] == "verification_failed"
    assert result["verification_result"]["verified"] is False
    assert result["verification_result"]["evidence_found"] is False
    assert result["verification_result"]["citations_valid"] is False
    assert result["requires_qualified_review"] is True
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


def test_verification_detects_matching_triage_output():
    triage = {
        "priority": "urgent_human_review",
        "signals": [
            {"signal": "potentially_serious_reaction_text"}
        ],
    }

    state = {
        "workflow_status": "evidence_completed",
        "triage_result": triage,
        "evidence_result": {
            "retrieval_status": "success",
            "priority": "urgent_human_review",
            "signals": [
                {"signal": "potentially_serious_reaction_text"}
            ],
            "evidence": [
                {
                    "source": "reference.pdf",
                    "page": 3,
                    "text": "Example evidence passage.",
                }
            ],
        },
        "errors": [],
    }

    result = verification_agent(state)

    assert result["verification_result"]["consistency_checked"] is True
    assert result["verification_result"]["consistency_valid"] is True
    assert result["verification_result"]["verified"] is True


def test_verification_detects_triage_priority_mismatch():
    state = {
        "workflow_status": "evidence_completed",
        "triage_result": {
            "priority": "urgent_human_review",
            "signals": [
                {"signal": "reported_hospitalization"}
            ],
        },
        "evidence_result": {
            "retrieval_status": "success",
            "priority": "routine_human_review",
            "signals": [
                {"signal": "reported_hospitalization"}
            ],
            "evidence": [
                {
                    "source": "reference.pdf",
                    "page": 3,
                    "text": "Example evidence passage.",
                }
            ],
        },
        "errors": [],
    }

    result = verification_agent(state)

    assert result["verification_result"]["consistency_valid"] is False
    assert result["verification_result"]["verified"] is False
    assert result["workflow_status"] == "verification_failed"


def test_verification_detects_signal_mismatch():
    state = {
        "workflow_status": "evidence_completed",
        "triage_result": {
            "priority": "urgent_human_review",
            "signals": [
                {"signal": "reported_hospitalization"}
            ],
        },
        "evidence_result": {
            "retrieval_status": "success",
            "priority": "urgent_human_review",
            "signals": [
                {"signal": "reported_death"}
            ],
            "evidence": [
                {
                    "source": "reference.pdf",
                    "page": 3,
                    "text": "Example evidence passage.",
                }
            ],
        },
        "errors": [],
    }

    result = verification_agent(state)

    assert result["verification_result"]["consistency_valid"] is False
    assert result["verification_result"]["verified"] is False