from __future__ import annotations

from pathlib import Path
import pdfplumber


def pdf_to_text(pdf_path: str | Path) -> str:
    path = Path(pdf_path)
    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text)
    return "\n\n".join(texts)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    args = ap.parse_args()
    print(pdf_to_text(args.pdf))

