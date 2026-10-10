
from app.schemas import AdverseEventReport


URGENT_REVIEW_TERMS = [
    "stevens-johnson syndrome",
    "stevens johnson syndrome",
    "toxic epidermal necrolysis",
    "skin peeling",
    "skin blistering",
    "severe skin reaction",
    "difficulty breathing",
    "anaphylaxis",
]


def assess_triage(report: AdverseEventReport) -> dict:
    """
    Identify reported safety signals that need human review.

    This function does not diagnose, determine causality,
    or make a final regulatory seriousness classification.
    """
    signals = []
    reaction_text = report.reaction_description.lower()

    if report.death:
        signals.append({
            "signal": "reported_death",
            "reason": "The report indicates that the patient died.",
        })

    if report.hospitalization:
        signals.append({
            "signal": "reported_hospitalization",
            "reason": "The report indicates hospitalization.",
        })

    matched_terms = [
        term
        for term in URGENT_REVIEW_TERMS
        if term in reaction_text
    ]

    if matched_terms:
        signals.append({
            "signal": "potentially_serious_reaction_text",
            "reason": (
                "The reaction description contains terms "
                "associated with potentially serious reactions."
            ),
            "matched_terms": matched_terms,
        })

    if signals:
        priority = "urgent_human_review"
    else:
        priority = "routine_human_review"

    return {
        "priority": priority,
        "signals": signals,
        "causality_assessed": False,
        "final_medical_decision": False,
        "requires_qualified_review": True,
    }
 