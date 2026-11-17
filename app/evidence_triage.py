from app.schemas import AdverseEventReport
from app.triage import assess_triage
from app.retrieval import search_evidence


REACTION_SEARCH_TERMS = {
    "skin peeling": ["desquamation", "exfoliation"],
    "peeling skin": ["desquamation", "exfoliation"],
    "skin rash": ["rash", "cutaneous reaction"],
    "difficulty breathing": ["dyspnea", "breathing difficulty"],
}


def build_evidence_query(
    report: AdverseEventReport,
    retry_count: int = 0,
) -> str:
    """Build a broader search query when an evidence retry is needed."""

    reaction = report.reaction_description
    query_parts = [report.drug_name, reaction]

    if retry_count > 0:
        normalized_reaction = reaction.lower()
        expanded_terms = []

        for phrase, synonyms in REACTION_SEARCH_TERMS.items():
            if phrase in normalized_reaction:
                expanded_terms.extend(synonyms)

        if expanded_terms:
            query_parts.extend(expanded_terms)
        else:
            query_parts.extend(["adverse reaction", "drug safety"])

    return " ".join(query_parts)


def assess_with_evidence(
    report: AdverseEventReport,
    retry_count: int = 0,
) -> dict:
    """Combine triage output with retrieved evidence."""

    triage = assess_triage(report)
    query = build_evidence_query(report, retry_count)

    try:
        evidence = search_evidence(query, top_k=5)
        retrieval_status = "success" if evidence else "no_results"
    except (FileNotFoundError, OSError, ValueError):
        evidence = []
        retrieval_status = "unavailable"

    evidence_items = [
        {
            "source": item.get("source", ""),
            "page": item.get("page"),
            "extraction_method": item.get("extraction_method", "unknown"),
            "matched_terms": item.get("matched_terms", []),
            "text": item.get("text", ""),
        }
        for item in evidence
    ]

    return {
        "case_id": report.case_id,
        "priority": triage["priority"],
        "signals": triage["signals"],
        "retrieval_status": retrieval_status,
        "search_attempt": retry_count + 1,
        "search_query": query,
        "evidence": evidence_items,
        "escalation": "human_review_required",
        "causality_assessed": False,
        "final_medical_decision": False,
        "requires_qualified_review": True,
        "notice": (
            "Retrieved passages provide context only and do not establish "
            "causality or replace qualified review."
        ),
    }