"""Extract text from uploaded resume files."""

from pathlib import Path
from typing import Callable, Optional

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MIN_USEFUL_TEXT = 80


def extract_text(
    file_path: Path,
    pdf_ocr_fallback: Optional[Callable[[Path], str]] = None,
) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path, pdf_ocr_fallback)
    if suffix in {".docx", ".doc"}:
        return _extract_docx(file_path)
    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(
    file_path: Path,
    pdf_ocr_fallback: Optional[Callable[[Path], str]] = None,
) -> str:
    extractors = (
        _extract_pdf_pymupdf,
        _extract_pdf_pdfplumber,
        _extract_pdf_pypdf,
    )

    best = ""
    for extractor in extractors:
        try:
            text = extractor(file_path)
        except (ImportError, OSError, ValueError, RuntimeError):
            continue
        if len(text) > len(best):
            best = text
        if len(best) >= MIN_USEFUL_TEXT:
            return best

    if pdf_ocr_fallback and len(best) < MIN_USEFUL_TEXT:
        try:
            ocr_text = pdf_ocr_fallback(file_path)
            if len(ocr_text) > len(best):
                return ocr_text
        except (ImportError, OSError, ValueError, RuntimeError):
            pass

    return best


def _extract_pdf_pymupdf(file_path: Path) -> str:
    import fitz

    doc = fitz.open(str(file_path))
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages).strip()


def _extract_pdf_pdfplumber(file_path: Path) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages).strip()


def _extract_pdf_pypdf(file_path: Path) -> str:
    from pypdf import PdfReader  # imported locally so pypdf is optional

    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages).strip()


def _extract_docx(file_path: Path) -> str:
    from docx import Document  # imported locally so python-docx is optional

    doc = Document(str(file_path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()