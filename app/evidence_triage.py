
from app.schemas import AdverseEventReport
from app.triage import assess_triage
from app.retrieval import search_evidence


def assess_with_evidence(report: AdverseEventReport) -> dict:
    """
    Combine preliminary safety signals with retrieved evidence.

    Retrieved passages are supporting context only. They do not
    establish causality, diagnosis, or final regulatory seriousness.
    """
    triage = assess_triage(report)

    query = f"{report.drug_name} {report.reaction_description}"

    try:
        evidence = search_evidence(query, top_k=5)
        retrieval_status = "success" if evidence else "no_results"
    except (FileNotFoundError, OSError, ValueError):
        evidence = []
        retrieval_status = "unavailable"

    evidence_items = [
        {
            "source": item["source"],
            "page": item["page"],
            "extraction_method": item["extraction_method"],
            "matched_terms": item["matched_terms"],
            "text": item["text"],
        }
        for item in evidence
    ]

    # Escalate when the preliminary rules detect warning signals.
    # Missing evidence also requires review rather than an
    # unsupported automated conclusion.
    if triage["signals"] or not evidence_items:
        escalation = "human_review_required"
    else:
        escalation = "human_review_required"

    return {
        "case_id": report.case_id,
        "priority": triage["priority"],
        "signals": triage["signals"],
        "retrieval_status": retrieval_status,
        "evidence": evidence_items,
        "escalation": escalation,
        "causality_assessed": False,
        "final_medical_decision": False,
        "requires_qualified_review": True,
        "notice": (
            "Retrieved passages are contextual evidence, not proof "
            "of causality. Verify the original documents and page "
            "references. Qualified human review is required."
        ),
    }
