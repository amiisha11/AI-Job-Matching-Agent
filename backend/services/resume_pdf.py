"""Read text from a resume PDF in memory.

The original file is not written to disk. Failure messages never include the
PDF bytes or the extracted text.
"""

import io
import logging
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError

from services.resume_health import assess_resume

logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024
PASSWORD_MESSAGE = "This PDF is password-protected. Remove the password and upload it again."
EMPTY_FILE_MESSAGE = "This file is empty."
EMPTY_PDF_MESSAGE = "This PDF is empty."
NOT_PDF_MESSAGE = "This file is not a PDF."
TOO_LARGE_MESSAGE = "This PDF is larger than 5 MB. Upload a smaller file."
CORRUPT_MESSAGE = "This PDF could not be read. It may be corrupted."
NO_TEXT_MESSAGE = (
    "No selectable text was found. This PDF may be a scan or an image. Export a text-based PDF and try again."
)


@dataclass(frozen=True)
class ResumeExtraction:
    """One extraction attempt. Text is present only when reading succeeded."""

    ok: bool
    message: str
    filename: str = ""
    text: str = ""
    page_count: int = 0
    character_count: int = 0
    health: dict | None = None


def safe_filename(name: str | None) -> str:
    """Keep the file's own name for display, without a folder path."""
    raw = name or "resume.pdf"
    base = raw.replace("\\", "/").split("/")[-1].strip()
    cleaned = "".join(character for character in base if character.isprintable())
    cleaned = cleaned.strip()[:180]
    return cleaned or "resume.pdf"


def extract_pdf(data: bytes, filename: str | None) -> ResumeExtraction:
    """Extract text from PDF bytes. Nothing is saved."""
    display_name = safe_filename(filename)
    if not data:
        return ResumeExtraction(False, EMPTY_FILE_MESSAGE, display_name)
    if len(data) > MAX_RESUME_BYTES:
        return ResumeExtraction(False, TOO_LARGE_MESSAGE, display_name)
    if not display_name.lower().endswith(".pdf") or not data.startswith(b"%PDF"):
        return ResumeExtraction(False, NOT_PDF_MESSAGE, display_name)
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not _opened_without_password(reader):
            return ResumeExtraction(False, PASSWORD_MESSAGE, display_name)
        page_count = len(reader.pages)
        if page_count == 0:
            return ResumeExtraction(False, EMPTY_PDF_MESSAGE, display_name)
        parts = [(page.extract_text() or "") for page in reader.pages]
    except FileNotDecryptedError:
        return ResumeExtraction(False, PASSWORD_MESSAGE, display_name)
    except Exception as exc:
        logger.warning("Resume PDF could not be read (%s).", type(exc).__name__)
        return ResumeExtraction(False, CORRUPT_MESSAGE, display_name)
    text = "\n".join(parts).strip()
    if not re.search(r"[A-Za-z]", text):
        return ResumeExtraction(False, NO_TEXT_MESSAGE, display_name, page_count=page_count)
    return ResumeExtraction(
        True,
        f"Text extracted from {display_name}.",
        display_name,
        text,
        page_count,
        len(text),
        assess_resume(text),
    )


def _opened_without_password(reader: PdfReader) -> bool:
    try:
        return bool(reader.decrypt(""))
    except Exception:
        return False
