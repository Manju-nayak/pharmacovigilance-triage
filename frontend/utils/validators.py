import re
from typing import Any, Dict, List, Optional, Tuple


CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_death_outcome_consistency(death: bool, outcome: str) -> Tuple[bool, Optional[str]]:
    """
    Ensure logical consistency between the mortality flag and outcome field.
    Matches the AdverseEventReport Pydantic model validator.
    """
    outcome_str = (outcome or "").strip().lower()

    if death and outcome_str != "death":
        return False, "If 'Resulted in Death' is checked, outcome must be 'Death'."
    if outcome_str == "death" and not death:
        return False, "If outcome is 'Death', 'Resulted in Death' must be checked."

    return True, None


def validate_report_form(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate adverse event report input fields before API submission.
    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    case_id = str(payload.get("case_id", "")).strip()
    if not case_id:
        errors.append("Case ID is required.")
    elif len(case_id) < 3 or len(case_id) > 50:
        errors.append("Case ID must be between 3 and 50 characters.")
    elif not CASE_ID_PATTERN.match(case_id):
        errors.append("Case ID may only contain alphanumeric characters, hyphens, and underscores.")

    drug_name = str(payload.get("drug_name", "")).strip()
    if not drug_name:
        errors.append("Suspect drug name is required.")
    elif len(drug_name) < 2 or len(drug_name) > 150:
        errors.append("Suspect drug name must be between 2 and 150 characters.")

    reaction_desc = str(payload.get("reaction_description", "")).strip()
    if not reaction_desc:
        errors.append("Reaction description is required.")
    elif len(reaction_desc) < 5 or len(reaction_desc) > 3000:
        errors.append("Reaction description must be between 5 and 3000 characters.")

    # Consistency check
    death = bool(payload.get("death", False))
    outcome = str(payload.get("outcome", "")).strip().lower()
    is_consistent, consistency_err = validate_death_outcome_consistency(death, outcome)
    if not is_consistent and consistency_err:
        errors.append(consistency_err)

    return len(errors) == 0, errors
