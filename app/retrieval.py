
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_DIR / "data" / "corpus" / "evidence_index.json"


def load_index():
    """Load and validate the evidence index."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Evidence index not found: {INDEX_PATH}"
        )

    with INDEX_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Evidence index must contain a JSON list.")

    return records


def tokenize(text):
    """Convert text into lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def search_evidence(query, top_k=5):
    """
    Search indexed evidence using keyword overlap.

    Returns matching evidence records ranked by overlap score.
    """
    if not query or not query.strip():
        return []

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be an integer greater than or equal to 1.")

    query_terms = set(tokenize(query))

    if not query_terms:
        return []

    records = load_index()
    results = []

    for record in records:
        text = record.get("text", "")

        if not isinstance(text, str) or not text.strip():
            continue

        text_terms = set(tokenize(text))
        matched_terms = sorted(query_terms & text_terms)

        if not matched_terms:
            continue

        overlap_score = len(matched_terms) / len(query_terms)

        results.append(
            {
                "source": record.get("source", "unknown"),
                "page": record.get("page"),
                "chunk": record.get("chunk"),
                "extraction_method": record.get(
                    "extraction_method", "unknown"
                ),
                "matched_terms": matched_terms,
                "score": overlap_score,
                "keyword_overlap_score": overlap_score,
                "text": text,
            }
        )

    results.sort(
        key=lambda item: (
            item["score"],
            len(item["matched_terms"]),
        ),
        reverse=True,
    )

    return results[:top_k]
