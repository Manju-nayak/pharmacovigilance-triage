
import json
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

# --------------------------------------------------
# Project paths and configuration
# --------------------------------------------------

PROJECT_DIR = Path(__file__).parent
CORPUS_DIR = PROJECT_DIR / "data" / "corpus"
INDEX_PATH = CORPUS_DIR / "evidence_index.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Windows Tesseract executable
TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Windows Poppler binaries directory
POPPLER_PATH = (
    r"C:\Tools\poppler-26.09.0\Library\bin"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# --------------------------------------------------
# Text chunking
# --------------------------------------------------

def split_text(text):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


# --------------------------------------------------
# PDF text extraction with OCR fallback
# --------------------------------------------------

def extract_page_text(pdf_path, page_number):
    """
    Extract text from one PDF page.
    Use OCR if the page has no selectable text.
    """
    reader = PdfReader(str(pdf_path))
    page = reader.pages[page_number - 1]

    text = (page.extract_text() or "").strip()

    if text:
        return text, "text"

    print(f"  Using OCR for page {page_number}...")

    images = convert_from_path(
        str(pdf_path),
        first_page=page_number,
        last_page=page_number,
        dpi=250,
        poppler_path=POPPLER_PATH,
    )

    if not images:
        return "", "ocr"

    text = pytesseract.image_to_string(
        images[0],
        lang="eng",
    ).strip()

    return text, "ocr"


# --------------------------------------------------
# Build evidence index
# --------------------------------------------------

def main():
    if not CORPUS_DIR.exists():
        print(f"ERROR: Corpus directory not found: {CORPUS_DIR}")
        return

    if not Path(TESSERACT_PATH).is_file():
        print(f"ERROR: Tesseract not found: {TESSERACT_PATH}")
        return

    if not (Path(POPPLER_PATH) / "pdftoppm.exe").is_file():
        print(f"ERROR: Poppler not found: {POPPLER_PATH}")
        return

    pdf_files = sorted(CORPUS_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in the corpus directory.")
        return

    records = []
    failures = []
    text_pages = 0
    ocr_pages = 0

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")

        try:
            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)

            print(f"Pages: {page_count}")

            for page_number in range(1, page_count + 1):
                try:
                    text, method = extract_page_text(
                        pdf_path,
                        page_number,
                    )

                    if not text:
                        print(
                            f"  WARNING: No text extracted "
                            f"from page {page_number}"
                        )
                        failures.append({
                            "source": pdf_path.name,
                            "page": page_number,
                            "reason": "No text extracted",
                        })
                        continue

                    if method == "text":
                        text_pages += 1
                    else:
                        ocr_pages += 1

                    for chunk_number, chunk in enumerate(
                        split_text(text),
                        start=1,
                    ):
                        records.append({
                            "source": pdf_path.name,
                            "page": page_number,
                            "chunk": chunk_number,
                            "extraction_method": method,
                            "text": chunk,
                        })

                except Exception as exc:
                    print(
                        f"  ERROR on page {page_number}: {exc}"
                    )
                    failures.append({
                        "source": pdf_path.name,
                        "page": page_number,
                        "reason": str(exc),
                    })

        except Exception as exc:
            print(f"ERROR reading {pdf_path.name}: {exc}")
            failures.append({
                "source": pdf_path.name,
                "page": None,
                "reason": str(exc),
            })

    # Do not replace an existing index if nothing was extracted.
    if not records:
        print("\nNo evidence chunks created. Index not updated.")
        return

    # Save the searchable evidence records.
    INDEX_PATH.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    indexed_sources = sorted({
        record["source"] for record in records
    })

    print("\n" + "=" * 55)
    print("EVIDENCE INDEX SUMMARY")
    print("=" * 55)
    print(f"PDF files discovered: {len(pdf_files)}")
    print(f"PDF sources indexed: {len(indexed_sources)}")
    print(f"Pages extracted with selectable text: {text_pages}")
    print(f"Pages extracted using OCR: {ocr_pages}")
    print(f"Total evidence chunks: {len(records)}")
    print(f"Index saved to: {INDEX_PATH}")

    print("\nIndexed sources:")
    for source in indexed_sources:
        print(f" - {source}")

    if failures:
        failure_path = CORPUS_DIR / "extraction_failures.json"
        failure_path.write_text(
            json.dumps(failures, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"\nPages needing attention: {len(failures)}")
        print(f"Failure report: {failure_path}")
    else:
        print("\nAll PDF pages produced text successfully.")


if __name__ == "__main__":
    main()
