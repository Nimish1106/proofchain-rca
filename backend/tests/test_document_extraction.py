import pymupdf
import pytest

from app.services.document_extraction import (
    InvalidPDFError,
    PDFPageLimitExceeded,
    PDFTextLimitExceeded,
    extract_pdf,
)


def create_pdf(path, page_texts):

    document = pymupdf.open()

    for text in page_texts:

        page = document.new_page()

        if text:
            page.insert_text(
                (72, 72),
                text,
            )

    document.save(path)
    document.close()

    return path


def test_extract_text_from_single_page(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "single.pdf",
        ["Metformin API batch MTF26001."],
    )

    result = extract_pdf(
        pdf_path,
        max_pages=10,
        max_extracted_text_chars=10000,
    )

    assert result.page_count == 1

    assert len(result.pages) == 1

    assert result.extraction_status == "text_extracted"

    assert "MTF26001" in result.pages[0].text

    assert result.pages[0].page_number == 1

    assert result.pages[0].source_start_char == 0

    assert result.pages[0].source_end_char == len(
        result.pages[0].text
    )


def test_extract_text_from_multiple_pages(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "multiple.pdf",
        [
            "Deviation report.",
            "Batch manufacturing record.",
            "Laboratory report.",
        ],
    )

    result = extract_pdf(
        pdf_path,
        max_pages=10,
        max_extracted_text_chars=10000,
    )

    assert result.page_count == 3

    assert len(result.pages) == 3

    assert result.extraction_status == "text_extracted"

    page_numbers = [
        page.page_number
        for page in result.pages
    ]

    assert page_numbers == [1, 2, 3]


def test_detect_pages_without_extractable_text(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "partial.pdf",
        [
            "Deviation report.",
            None,
        ],
    )

    result = extract_pdf(
        pdf_path,
        max_pages=10,
        max_extracted_text_chars=10000,
    )

    assert result.page_count == 2

    assert result.extraction_status == "partial_text"

    assert len(result.pages) == 1

    assert result.pages_without_text == [2]


def test_detect_document_needing_ocr(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "scanned.pdf",
        [
            None,
            None,
        ],
    )

    result = extract_pdf(
        pdf_path,
        max_pages=10,
        max_extracted_text_chars=10000,
    )

    assert result.page_count == 2

    assert result.extraction_status == "needs_ocr"

    assert result.pages == []

    assert result.pages_without_text == [1, 2]


def test_reject_pdf_exceeding_page_limit(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "large.pdf",
        [
            "Page one",
            "Page two",
        ],
    )

    with pytest.raises(PDFPageLimitExceeded):

        extract_pdf(
            pdf_path,
            max_pages=1,
            max_extracted_text_chars=10000,
        )


def test_reject_excessive_extracted_text(tmp_path):

    pdf_path = create_pdf(
        tmp_path / "long_text.pdf",
        [
            "A" * 100,
        ],
    )

    with pytest.raises(PDFTextLimitExceeded):

        extract_pdf(
            pdf_path,
            max_pages=10,
            max_extracted_text_chars=50,
        )


def test_reject_invalid_pdf(tmp_path):

    invalid_path = tmp_path / "invalid.pdf"

    invalid_path.write_bytes(
        b"This is not a PDF."
    )

    with pytest.raises(InvalidPDFError):

        extract_pdf(
            invalid_path,
            max_pages=10,
            max_extracted_text_chars=10000,
        )


def test_missing_pdf_is_rejected(tmp_path):

    with pytest.raises(InvalidPDFError):

        extract_pdf(
            tmp_path / "missing.pdf",
            max_pages=10,
            max_extracted_text_chars=10000,
        )
