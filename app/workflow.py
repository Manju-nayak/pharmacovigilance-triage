
from langgraph.graph import END, START, StateGraph

from app.evidence_agent import evidence_agent
from app.intake_agent import intake_agent
from app.triage_agent import triage_agent
from app.verification_agent import verification_agent
from app.workflow_state import TriageWorkflowState


def route_after_intake(state: TriageWorkflowState) -> str:
    """Continue only when intake succeeds."""
    if state.get("workflow_status") == "intake_completed":
        return "triage"
    return "verification"


def route_after_triage(state: TriageWorkflowState) -> str:
    """Continue only when triage succeeds."""
    if state.get("workflow_status") == "triage_completed":
        return "evidence"
    return "verification"


def build_triage_workflow():
    """Build and compile the pharmacovigilance triage workflow."""
    graph = StateGraph(TriageWorkflowState)

    graph.add_node("intake", intake_agent)
    graph.add_node("triage", triage_agent)
    graph.add_node("evidence", evidence_agent)
    graph.add_node("verification", verification_agent)

    graph.add_edge(START, "intake")

    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "triage": "triage",
            "verification": "verification",
        },
    )

    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "evidence": "evidence",
            "verification": "verification",
        },
    )

    graph.add_edge("evidence", "verification")
    graph.add_edge("verification", END)

    return graph.compile()


# Compile the workflow once when the module is imported.
triage_workflow = build_triage_workflow()


def run_workflow(report):
    """
    Execute the workflow for a validated adverse-event report.

    Accepts a Pydantic report model or a dictionary.
    """
    if hasattr(report, "model_dump"):
        report_data = report.model_dump()
    elif isinstance(report, dict):
        report_data = report
    else:
        raise TypeError(
            "report must be a Pydantic model or a dictionary."
        )

    initial_state = {
        "report": report_data,
        "workflow_status": "started",
        "errors": [],
    }

    return triage_workflow.invoke(initial_state)
