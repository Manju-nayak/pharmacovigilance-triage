
from pathlib import Path
from pypdf import PdfReader

CORPUS_DIR = Path(__file__).parent / "data" / "corpus"


def main():
    pdf_files = sorted(CORPUS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {CORPUS_DIR}")
        return

    for pdf_path in pdf_files:
        print("\n" + "=" * 80)
        print(f"FILE: {pdf_path.name}")
        print("=" * 80)

        try:
            reader = PdfReader(str(pdf_path))
            print(f"Pages: {len(reader.pages)}")

            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()

            if text:
                print(text[:1500])
                print(f"\nExtracted characters: {len(text)}")
            else:
                print("No selectable text found. This PDF may need OCR.")

        except Exception as exc:
            print(f"Could not read PDF: {exc}")


if __name__ == "__main__":
    main()
