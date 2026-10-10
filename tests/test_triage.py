
from app.schemas import AdverseEventReport
from app.triage import assess_triage


def make_report(**overrides):
    data = {
        "case_id": "SYN-TRIAGE-001",
        "drug_name": "ExampleDrug",
        "reaction_description": "Mild nausea reported.",
        "patient_age": 35,
        "reporter_type": "patient",
        "outcome": "recovering",
        "event_onset_days": 2,
        "hospitalization": False,
        "death": False,
    }
    data.update(overrides)
    return AdverseEventReport(**data)


def test_hospitalization_triggers_urgent_review():
    report = make_report(hospitalization=True)

    result = assess_triage(report)

    assert result["priority"] == "urgent_human_review"
    assert any(
        signal["signal"] == "reported_hospitalization"
        for signal in result["signals"]
    )


def test_skin_peeling_triggers_urgent_review():
    report = make_report(
        reaction_description="Severe skin peeling reported."
    )

    result = assess_triage(report)

    assert result["priority"] == "urgent_human_review"
    assert any(
        signal["signal"] == "potentially_serious_reaction_text"
        for signal in result["signals"]
    )


def test_death_triggers_urgent_review():
    report = make_report(
        outcome="death",
        death=True,
    )

    result = assess_triage(report)

    assert result["priority"] == "urgent_human_review"
    assert any(
        signal["signal"] == "reported_death"
        for signal in result["signals"]
    )


def test_no_matching_signal_still_requires_review():
    report = make_report()

    result = assess_triage(report)

    assert result["priority"] == "routine_human_review"
    assert result["signals"] == []
    assert result["requires_qualified_review"] is True


def test_triage_does_not_claim_causality():
    report = make_report(
        reaction_description="Severe skin peeling reported.",
        hospitalization=True,
    )

    result = assess_triage(report)

    assert result["causality_assessed"] is False
    assert result["final_medical_decision"] is False
