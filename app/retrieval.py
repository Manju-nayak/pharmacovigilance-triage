
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_DIR / "data" / "corpus" / "evidence_index.json"


def load_index():
    """Load evidence chunks from the JSON index."""
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
    """Normalize text into lowercase keyword tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def search_evidence(query, top_k=5):
    """
    Search evidence chunks by keyword overlap.

    Returns source filename, page, extraction method,
    matched terms, and relevant text.
    """
    if not query or not query.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    query_terms = set(tokenize(query))

    if not query_terms:
        return []

    records = load_index()
    results = []

    for record in records:
        text = record.get("text", "")
        text_terms = set(tokenize(text))
        matched_terms = sorted(query_terms & text_terms)

        if not matched_terms:
            continue

        results.append({
            "source": record.get("source", "unknown"),
            "page": record.get("page"),
            "chunk": record.get("chunk"),
            "extraction_method": record.get(
                "extraction_method", "unknown"
            ),
            "matched_terms": matched_terms,
            "score": len(matched_terms) / len(query_terms),
            "text": text,
        })

    results.sort(
        key=lambda item: (
            item["score"],
            len(item["matched_terms"]),
        ),
        reverse=True,
    )

    return results[:top_k]


if __name__ == "__main__":
    query = (
        "carbamazepine severe skin reactions "
        "Stevens Johnson syndrome"
    )

    results = search_evidence(query, top_k=5)

    print(f"Query: {query}")
    print(f"Results found: {len(results)}")

    for number, result in enumerate(results, start=1):
        print("\n" + "=" * 60)
        print(f"Result {number}")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Method: {result['extraction_method']}")
        print(f"Score: {result['score']:.2f}")
        print(f"Matched terms: {result['matched_terms']}")
        print(f"Text: {result['text'][:700]}")
