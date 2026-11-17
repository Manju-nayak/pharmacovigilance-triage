
from app.schemas import AdverseEventReport
from app.evidence_triage import assess_with_evidence


def make_report(**overrides):
    data = {
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
    }
    data.update(overrides)
    return AdverseEventReport(**data)


def test_evidence_triage_returns_safety_signals_and_sources():
    report = make_report()

    result = assess_with_evidence(report)

    assert result["case_id"] == "SYN-EVIDENCE-001"
    assert result["priority"] == "urgent_human_review"
    assert result["signals"]
    assert result["evidence"]
    assert all(item["source"] for item in result["evidence"])
    assert all(item["page"] >= 1 for item in result["evidence"])


def test_evidence_triage_requires_human_review():
    report = make_report()

    result = assess_with_evidence(report)

    assert result["escalation"] == "human_review_required"
    assert result["requires_qualified_review"] is True
    assert result["causality_assessed"] is False
    assert result["final_medical_decision"] is False


def test_evidence_triage_reports_retrieval_status():
    report = make_report()

    result = assess_with_evidence(report)

    assert result["retrieval_status"] in {
        "success",
        "no_results",
        "unavailable",
    }


def test_evidence_triage_preserves_retrieval_scores():
    report = make_report()

    result = assess_with_evidence(report)

    assert result["evidence"], "Expected non-empty evidence list"
    for item in result["evidence"]:
        assert "score" in item
        assert "keyword_overlap_score" in item
        assert isinstance(item["score"], float)
        assert item["score"] > 0
        assert item["keyword_overlap_score"] == item["score"]

