
from app.intake_agent import intake_agent


def test_valid_report_completes_intake():
    state = {
        "report": {
            "case_id": "SYN-INTAKE-001",
            "drug_name": "ExampleDrug",
            "reaction_description": "Synthetic example reaction.",
        },
        "errors": [],
    }

    result = intake_agent(state)

    assert result["case_id"] == "SYN-INTAKE-001"
    assert result["workflow_status"] == "intake_completed"
    assert result["requires_qualified_review"] is True


def test_missing_report_fails_intake():
    result = intake_agent({"errors": []})

    assert result["workflow_status"] == "intake_failed"
    assert result["requires_qualified_review"] is True
    assert result["escalation"] == "human_review_required"


def test_missing_case_id_fails_intake():
    state = {
        "report": {"drug_name": "ExampleDrug"},
        "errors": [],
    }

    result = intake_agent(state)

    assert result["workflow_status"] == "intake_failed"
    assert any("case ID" in error for error in result["errors"])
