import importlib
import os
import sqlite3
import tempfile
from pathlib import Path


def _fresh(tmp: Path):
    os.environ["JANUS_DB_PATH"] = str(tmp / "janus.sqlite3")
    import document_grounding
    importlib.reload(document_grounding)
    with sqlite3.connect(os.environ["JANUS_DB_PATH"]) as c:
        c.execute("CREATE TABLE janus_files(id TEXT PRIMARY KEY,account_id INTEGER,original_name TEXT,mime_type TEXT,extraction_status TEXT,extracted_text TEXT,created_at INTEGER)")
    document_grounding.init_schema()
    return document_grounding


def test_retrieval_finds_relevant_late_chunk_not_only_document_prefix():
    with tempfile.TemporaryDirectory() as td:
        dg = _fresh(Path(td))
        text = (
            "Introduction\n\nThis opening is generic and intentionally unrelated. " * 80
            + "\n\n[PDF page 9]\nCritical result: the sapphire mechanism reduces thermal drift by forty percent under the final protocol.\n"
            + "\n\nAppendix material follows. " * 40
        )
        with sqlite3.connect(os.environ["JANUS_DB_PATH"]) as c:
            c.execute("INSERT INTO janus_files VALUES(?,?,?,?,?,?,?)", ("f1",1,"long-report.pdf","application/pdf","pdf_cached",text,1))
        dg.index_text(1, "f1", text, force=True)
        rows = dg.retrieve(1, "What did the sapphire mechanism do to thermal drift?", file_ids=["f1"], limit=4)
        assert rows
        assert any("sapphire mechanism" in r["content"].lower() for r in rows)
        assert any(r.get("page_no") == 9 for r in rows)


def test_library_recall_can_find_previous_document_without_reattachment():
    with tempfile.TemporaryDirectory() as td:
        dg = _fresh(Path(td))
        text = "Project Atlas notes. The preferred launch window is September because monsoon risk falls sharply."
        with sqlite3.connect(os.environ["JANUS_DB_PATH"]) as c:
            c.execute("INSERT INTO janus_files VALUES(?,?,?,?,?,?,?)", ("atlas",7,"atlas-notes.txt","text/plain","cached",text,1))
        dg.index_text(7, "atlas", text, force=True)
        grounding, rows = dg.format_grounding(7, "What did my Atlas file say about the launch window?", file_ids=None)
        assert rows
        assert "September" in grounding
        assert "atlas-notes.txt" in grounding


def test_account_boundary_applies_to_document_index():
    with tempfile.TemporaryDirectory() as td:
        dg = _fresh(Path(td))
        secret = "Private owner document contains the violet-lantern phrase."
        with sqlite3.connect(os.environ["JANUS_DB_PATH"]) as c:
            c.execute("INSERT INTO janus_files VALUES(?,?,?,?,?,?,?)", ("secret",1,"secret.txt","text/plain","cached",secret,1))
        dg.index_text(1, "secret", secret, force=True)
        assert dg.retrieve(2, "violet lantern", file_ids=None) == []
