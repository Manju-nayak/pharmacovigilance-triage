import streamlit as st

from frontend.api_client import APIClient
from frontend.utils.session import init_session_state
from frontend.utils.ui_components import (
    load_css,
    render_regulatory_banner,
    render_evidence_card,
)

st.set_page_config(
    page_title="Evidence Explorer | PV Triage",
    page_icon="🔍",
    layout="wide",
)

load_css()
init_session_state()
client: APIClient = st.session_state.api_client

st.title("🔍 Literature & Safety Notice Evidence Explorer")
st.markdown(
    "Query the indexed reference corpus directly (`/evidence/search`) to inspect official safety notices, "
    "package inserts (e.g. Tegretol / Carbamazepine), and pharmacovigilance regulatory guidance."
)

render_regulatory_banner()

# -----------------------------------------------------------------------------
# SEARCH INTERFACE
# -----------------------------------------------------------------------------
st.subheader("🔎 Search Indexed Medical Evidence")

# Sample query buttons
st.caption("Quick sample queries:")
sample_queries = [
    "carbamazepine serious skin reactions",
    "carbamazepine stevens johnson syndrome",
    "toxic epidermal necrolysis HLA-B*1502",
    "cdsco safety notice life threatening",
    "pharmacovigilance guidance mah adverse reactions",
]

sample_cols = st.columns(len(sample_queries))
chosen_sample = None
for i, sq in enumerate(sample_queries):
    with sample_cols[i]:
        if st.button(f"🔍 {sq[:24]}...", key=f"sq_{i}", help=sq, use_container_width=True):
            chosen_sample = sq

default_query = chosen_sample or st.session_state.get("evidence_query", "carbamazepine serious skin reactions")

with st.form("evidence_search_form"):
    q_col1, q_col2 = st.columns([4, 1])

    with q_col1:
        query = st.text_input(
            "Search Query:",
            value=default_query,
            placeholder="Enter medication name, adverse symptom, or regulatory notice terms (min 2 characters)...",
            help="Indexed documents include CDSCO notices, package inserts, and MAH clinical rules.",
        )
    with q_col2:
        top_k = st.slider(
            "Top Results (top_k):",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of ranked passage matches to return.",
        )

    search_submitted = st.form_submit_button("🔍 Search Evidence Corpus", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# EXECUTE SEARCH
# -----------------------------------------------------------------------------
if search_submitted or chosen_sample:
    if not query or len(query.strip()) < 2:
        st.warning("⚠️ Query must be at least 2 characters long.")
    else:
        st.session_state["evidence_query"] = query.strip()
        with st.spinner(f"Searching indexed evidence for '{query.strip()}'..."):
            res = client.search_evidence(query.strip(), top_k=top_k)

        if not res["success"]:
            st.error(f"❌ Evidence search failed (HTTP {res['status_code']}): {res['error']}")
        else:
            data = res["data"]
            results = data.get("results", [])
            req_id = data.get("request_id", "unknown")

            st.markdown(
                f"""
                <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:8px 12px; margin-bottom:14px; font-size:0.875rem; color:#166534;">
                    ✓ Found <strong>{len(results)} matching passages</strong> for query <code>{query}</code> (Request ID: <code>{req_id[:8]}...</code>)
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not results:
                st.info("No matching passages found for this keyword combination.")
            else:
                for idx, item in enumerate(results, start=1):
                    render_evidence_card(item, idx)

st.markdown("---")
with st.expander("📄 About the Indexed Medical Corpus"):
    st.markdown(
        """
        The local evidence index (`data/corpus/evidence_index.json`) is built from:
        - **Carbamazepine CDSCO Safety Notice (PDF):** National regulatory alert on serious cutaneous adverse reactions (SCARs).
        - **Tegretol (Carbamazepine) Package Insert (PDF):** Prescribing information, boxed warnings, indications, and reported adverse events.
        - **Pharmacovigilance Guidance for MAH v2 (PDF):** Regulatory reporting timelines and seriousness criteria.
        - **New Drugs & Clinical Trials Rules 2019 (PDF):** Statutory compliance framework.

        *Search ranks passages using lowercase alphanumeric tokenization and keyword overlap scoring.*
        """
    )
