import importlib
import io
import os
import tempfile
from pathlib import Path

from pypdf import PdfWriter


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_AUTH_DB"] = str(tmp / "janus.sqlite3")
    os.environ["JANUS_FILE_DIR"] = str(tmp / "files")
    import attachment_api
    importlib.reload(attachment_api)
    return attachment_api


def test_pdf_without_text_is_detected_locally_without_false_content_claim():
    with tempfile.TemporaryDirectory() as td:
        attachment_api = _fresh(Path(td))
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        buf = io.BytesIO()
        writer.write(buf)
        text, status = attachment_api._extract_text("scan.pdf", buf.getvalue())
        assert text is None
        assert status == "pdf_no_text"


def test_malformed_pdf_fails_cleanly():
    with tempfile.TemporaryDirectory() as td:
        attachment_api = _fresh(Path(td))
        text, status = attachment_api._extract_text("broken.pdf", b"not a pdf")
        assert text is None
        assert status == "pdf_failed"
