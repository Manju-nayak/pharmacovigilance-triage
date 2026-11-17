from typing import Any, TypedDict


class TriageWorkflowState(TypedDict, total=False):
    """Shared state passed between pharmacovigilance workflow nodes."""

    request_id: str
    case_id: str

    report: dict[str, Any]
    triage_result: dict[str, Any]
    evidence_result: dict[str, Any]
    verification_result: dict[str, Any]

    workflow_status: str
    errors: list[str]

    escalation: str
    requires_qualified_review: bool

    # Retry tracking
    retry_count: int
    retry_recommended: bool