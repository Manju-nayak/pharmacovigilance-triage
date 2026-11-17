import html
import re
from typing import Any, Dict, List, Optional
import streamlit as st

from frontend.config import ASSETS_DIR


def load_css():
    """Inject custom healthcare dashboard CSS."""
    css_file = ASSETS_DIR / "style.css"
    if css_file.exists():
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_regulatory_banner():
    """Display standard regulatory compliance & medical disclaimer banner."""
    st.markdown(
        """
        <div class="regulatory-notice">
            <strong>🛡️ Regulatory Compliance & Human-in-the-Loop Mandate:</strong><br>
            This system performs preliminary intake, safety signal triage, and contextual literature retrieval.
            Per <em>Good Pharmacovigilance Practices (GVP)</em> and CDSCO guidelines, this service
            <strong>does not assess medical causality</strong> or make final diagnostic/regulatory determinations.
            <strong>Qualified medical review is mandatory</strong> prior to any regulatory action.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(title: str, value: Any, subtitle: str = "", icon: str = ""):
    """Render a clean healthcare metric card."""
    display_title = f"{icon} {title}".strip()
    st.markdown(
        f"""
        <div class="kpi-container">
            <div class="kpi-title">{html.escape(display_title)}</div>
            <div class="kpi-value">{html.escape(str(value))}</div>
            <div class="kpi-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_priority_badge(priority: Optional[str]) -> str:
    """Return HTML for triage priority badge."""
    if priority == "urgent_human_review":
        return '<span class="badge-urgent">🔴 URGENT HUMAN REVIEW</span>'
    elif priority == "routine_human_review":
        return '<span class="badge-routine">🟢 ROUTINE HUMAN REVIEW</span>'
    elif priority == "rejected":
        return '<span class="badge-failed">⛔ REJECTED / QUARANTINED</span>'
    return '<span class="badge-queued">⚪ PENDING TRIAGE</span>'


def render_status_badge(status: Optional[str]) -> str:
    """Return HTML for run/case execution status badge."""
    s = (status or "unknown").lower()
    if s == "completed":
        return '<span class="badge-completed">✅ Completed</span>'
    elif s == "queued":
        return '<span class="badge-queued">⏳ Queued</span>'
    elif s == "running":
        return '<span class="badge-running">⚙️ Running</span>'
    elif s in ("failed", "error"):
        return '<span class="badge-failed">❌ Failed</span>'
    elif s == "rejected":
        return '<span class="badge-failed">⛔ Rejected</span>'
    return f'<span class="badge-queued">{html.escape(s)}</span>'


def highlight_matched_terms(text: str, terms: List[str]) -> str:
    """Highlight matched safety keywords in text."""
    escaped_text = html.escape(text)
    if not terms:
        return escaped_text

    for term in sorted(terms, key=len, reverse=True):
        if not term.strip():
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        escaped_text = pattern.sub(
            lambda m: f'<span class="highlight-danger">{m.group(0)}</span>',
            escaped_text,
        )
    return escaped_text


def render_agent_stepper(workflow_status: str, errors: Optional[List[str]] = None):
    """Render visual multi-agent workflow pipeline execution stepper."""
    steps = [
        ("1. Intake Agent", "Validates schema & case integrity"),
        ("2. Triage Agent", "Identifies safety signals & urgency"),
        ("3. Evidence Agent", "Retrieves indexed literature passages"),
        ("4. Verification Agent", "Audits citation structure & traceability"),
    ]

    status_map = {
        "started": 0,
        "intake_completed": 1,
        "intake_failed": 0,
        "triage_completed": 2,
        "triage_skipped": 1,
        "triage_failed": 1,
        "evidence_completed": 3,
        "evidence_skipped": 2,
        "evidence_failed": 2,
        "verification_completed": 4,
        "verification_failed": 4,
        "verification_incomplete": 3,
        "completed": 4,
    }

    current_step = status_map.get(workflow_status, 0)
    failed = "failed" in workflow_status or "incomplete" in workflow_status

    cols = st.columns(4)
    for i, (title, desc) in enumerate(steps):
        with cols[i]:
            if i < current_step or (i == 3 and current_step == 4 and not failed):
                st.success(f"**{title}**\n\n✓ {desc}")
            elif i == current_step and failed:
                st.error(f"**{title}**\n\n⚠️ Failed / Incomplete")
            elif i == current_step:
                st.info(f"**{title}**\n\n⚙️ Processing...")
            else:
                st.caption(f"**{title}**\n\n⏸️ {desc}")

    if errors:
        st.warning(f"**Workflow Flags:** {', '.join(errors)}")


def render_evidence_card(item: Dict[str, Any], idx: int = 1):
    """Render an evidence citation passage card."""
    source = item.get("source", "Unknown Document")
    page = item.get("page", 1)
    method = item.get("extraction_method", "text").upper()

    # Retrieve score without falling back to misleading 0.0%
    raw_score = item.get("score")
    if raw_score is None:
        raw_score = item.get("keyword_overlap_score")

    if raw_score is not None and isinstance(raw_score, (int, float)):
        score_display = f"{raw_score:.1%}"
    else:
        score_display = "N/A (Unscored)"

    matched_terms = item.get("matched_terms", [])
    raw_text = item.get("text", "")

    tags_html = "".join([f'<span class="tag-term">{html.escape(t)}</span>' for t in matched_terms])
    highlighted_text = highlight_matched_terms(raw_text, matched_terms)

    st.markdown(
        f"""
        <div class="evidence-card">
            <div class="evidence-header">
                <div>
                    <strong>Citation #{idx}:</strong> 📄 <code>{html.escape(source)}</code> (Page {page})
                    <span style="margin-left: 8px; font-size: 0.75rem; color: #64748b;">Method: {method}</span>
                </div>
                <div>
                    <strong>Keyword Overlap:</strong> {score_display}
                </div>
            </div>
            <div style="margin-bottom: 8px;">
                {tags_html}
            </div>
            <div class="evidence-text">
                "{highlighted_text}"
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
