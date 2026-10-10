
from app.retrieval import search_evidence


def test_search_returns_relevant_evidence():
    results = search_evidence(
        "carbamazepine serious skin reactions",
        top_k=5,
    )

    assert results
    assert all("source" in item for item in results)
    assert all("page" in item for item in results)
    assert all("text" in item for item in results)


def test_search_finds_ocr_safety_notice():
    results = search_evidence(
        "carbamazepine life threatening skin reactions",
        top_k=10,
    )

    sources = {
        item["source"] for item in results
        if item["extraction_method"] == "ocr"
    }

    assert "carbamazepine_cdsco_safety_notice.pdf" in sources


def test_empty_query_returns_no_results():
    assert search_evidence("") == []
    assert search_evidence("   ") == []


def test_invalid_top_k_is_rejected():
    try:
        search_evidence("carbamazepine", top_k=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for top_k=0")
