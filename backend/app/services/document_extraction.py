from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PDFExtractionError(Exception):
    """Base exception for PDF extraction failures."""


class EncryptedPDFError(PDFExtractionError):
    """Raised when a PDF requires a password."""


class PDFPageLimitExceeded(PDFExtractionError):
    """Raised when the PDF exceeds the configured page limit."""


class PDFTextLimitExceeded(PDFExtractionError):
    """Raised when extracted text exceeds the configured limit."""


class InvalidPDFError(PDFExtractionError):
    """Raised when the PDF cannot be processed."""


@dataclass(frozen=True)
class ExtractedPage:
    """Extracted text and source coordinates for one PDF page."""

    page_number: int
    text: str
    source_start_char: int
    source_end_char: int


@dataclass(frozen=True)
class PDFExtractionResult:
    """Complete result of PDF text extraction."""

    page_count: int
    pages: list[ExtractedPage]
    extraction_status: str
    pages_without_text: list[int]
    total_extracted_characters: int


def extract_pdf(
    pdf_path: Path,
    *,
    max_pages: int,
    max_extracted_text_chars: int,
) -> PDFExtractionResult:
    """
    Extract machine-readable PDF text page by page.

    Does not perform OCR.

    Pages without extractable text are reported separately,
    allowing the application to identify documents that
    may require OCR.
    """

    if max_pages <= 0:
        raise ValueError(
            "Maximum page count must be positive."
        )

    if max_extracted_text_chars <= 0:
        raise ValueError(
            "Maximum extracted text must be positive."
        )

    if not pdf_path.is_file():
        raise InvalidPDFError(
            "The stored PDF file does not exist."
        )

    extracted_pages: list[ExtractedPage] = []
    pages_without_text: list[int] = []

    total_characters = 0

    try:
        with pymupdf.open(pdf_path) as document:

            if document.needs_pass:
                raise EncryptedPDFError(
                    "Password-protected PDFs are not supported."
                )

            page_count = document.page_count

            if page_count == 0:
                raise InvalidPDFError(
                    "The PDF does not contain any pages."
                )

            if page_count > max_pages:
                raise PDFPageLimitExceeded(
                    "The PDF exceeds the configured page limit."
                )

            for page_index in range(page_count):

                page = document.load_page(page_index)

                page_text = page.get_text(
                    "text",
                    sort=True,
                )

                # Page numbers exposed to users are 1-based.
                page_number = page_index + 1

                if not page_text.strip():
                    pages_without_text.append(
                        page_number
                    )
                    continue

                new_total = (
                    total_characters + len(page_text)
                )

                if new_total > max_extracted_text_chars:
                    raise PDFTextLimitExceeded(
                        "The PDF exceeds the configured "
                        "extracted-text limit."
                    )

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=page_text,
                        source_start_char=0,
                        source_end_char=len(page_text),
                    )
                )

                total_characters = new_total

            if not extracted_pages:
                extraction_status = "needs_ocr"

            elif pages_without_text:
                extraction_status = "partial_text"

            else:
                extraction_status = "text_extracted"

            return PDFExtractionResult(
                page_count=page_count,
                pages=extracted_pages,
                extraction_status=extraction_status,
                pages_without_text=pages_without_text,
                total_extracted_characters=total_characters,
            )

    except PDFExtractionError:
        raise

    except Exception as exc:
        raise InvalidPDFError(
            "The PDF could not be processed."
        ) from exc
