
from typing import Any, TypedDict


class TriageWorkflowState(TypedDict, total=False):
    """Shared state passed between pharmacovigilance workflow nodes."""

    request_id: str
    case_id: str

    # Validated synthetic adverse-event report
    report: dict[str, Any]

    # Initial rule-based triage
    triage_result: dict[str, Any]

    # Retrieved evidence from the local document corpus
    evidence_result: dict[str, Any]

    # Verification results
    verification_result: dict[str, Any]

    # Workflow status and audit information
    workflow_status: str
    errors: list[str]

    # Final routing; qualified human review remains mandatory
    escalation: str
    requires_qualified_review: bool
