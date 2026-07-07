# ============================================================
# input_processors/pdf_processor.py
# ============================================================
# STEP 5B: PDF File Input Processor
#
# The user uploads a PDF meeting document (agenda, minutes,
# printed transcript). This module uses 'pypdf' to read each
# page and extract all its text content.
#
# RESPONSIBILITY:
#   Extract all readable text from a PDF file object and
#   return it as a single plain text string for the LLM.
#
# LIMITATION:
#   Scanned PDFs (image-only) will return empty text since
#   pypdf cannot OCR images. Only text-based PDFs are supported.
# ============================================================

import io
from pypdf import PdfReader


def process_pdf(file_bytes: bytes) -> str:
    """
    STEP 5B.1: Extract all text from a PDF file.

    Args:
        file_bytes (bytes): Raw bytes of the uploaded PDF file
                            (from Streamlit's st.file_uploader).

    Returns:
        str: Concatenated plain text from all PDF pages.
        Returns empty string if PDF has no extractable text.
    """
    # STEP 5B.1.1: Wrap raw bytes in a BytesIO stream
    # PdfReader expects a file-like object, not raw bytes
    pdf_stream = io.BytesIO(file_bytes)

    # STEP 5B.1.2: Initialize the pypdf PdfReader
    try:
        reader = PdfReader(pdf_stream)
    except Exception as e:
        # PDF is corrupt or password-protected → return empty
        print(f"[pdf_processor] Failed to read PDF: {e}")
        return ""

    # STEP 5B.1.3: Extract text from each page and accumulate
    extracted_pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        # extract_text() returns a string or None for image pages
        page_text = page.extract_text()
        if page_text:
            # Add a page separator comment for LLM context clarity
            extracted_pages.append(
                f"--- Page {page_number} ---\n{page_text.strip()}"
            )

    # STEP 5B.1.4: Guard — warn if no text was extracted
    if not extracted_pages:
        print("[pdf_processor] Warning: No text found in PDF pages.")
        return ""

    # STEP 5B.1.5: Join all pages with double newlines
    return "\n\n".join(extracted_pages)
