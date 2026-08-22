"""JANUS durable-schema registry and startup compatibility guard.

Phase 2 Step 3 makes persistence ownership explicit and refuses to start the full
application when an already-existing critical table is structurally incompatible.
Missing tables are allowed during preflight because their owning subsystem creates
them during normal import/install. No user table is deleted, renamed or rewritten
by this module.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
MATRIX_VERSION = 1

# Minimum columns that current code depends on. Extra columns are explicitly
# tolerated so additive migrations remain restart-safe.
TABLES: dict[str, dict[str, Any]] = {
    "accounts": {"owner": "auth.py", "version": 2, "critical": True, "columns": {"id","username","email","password_hash","created_at","updated_at","disabled","google_sub","email_verified"}},
    "sessions": {"owner": "auth.py", "version": 1, "critical": True, "columns": {"token_hash","account_id","created_at","expires_at"}},
    "auth_tokens": {"owner": "auth.py", "version": 1, "critical": True, "columns": {"token_hash","account_id","purpose","created_at","expires_at","used_at"}},
    "desktop_memory": {"owner": "dashboard_api.py", "version": 1, "critical": True, "columns": {"id","profile_id","role","content","level","created_at"}},
    "desktop_events": {"owner": "dashboard_api.py", "version": 1, "critical": True, "columns": {"id","profile_id","event_type","detail","created_at"}},
    "janus_continuity_items": {"owner": "continuity_ledger.py", "version": 1, "critical": False, "columns": {"id","profile_id","kind","title","detail","state","priority","created_at","updated_at"}},
    "janus_continuity_events": {"owner": "continuity_ledger.py", "version": 1, "critical": False, "columns": {"id","item_id","profile_id","event_type","created_at"}},
    "janus_research_claims": {"owner": "research_workspace.py", "version": 1, "critical": False, "columns": {"id","profile_id","programme","title","statement","claim_kind","epistemic_state","domain","created_at","updated_at"}},
    "janus_research_evidence": {"owner": "research_workspace.py", "version": 1, "critical": False, "columns": {"id","profile_id","claim_id","evidence_kind","summary","created_at"}},
    "janus_research_relations": {"owner": "research_workspace.py", "version": 1, "critical": False, "columns": {"id","profile_id","from_claim_id","to_claim_id","relation","created_at"}},
    "janus_client_presence": {"owner": "core_sync.py", "version": 1, "critical": False, "columns": {"account_id","profile_id","device_id","platform","client_version","phase","cycles_json","last_seen_at"}},
    "janus_core_observe": {"owner": "core_observer.py", "version": 2, "critical": False, "columns": {"id","profile_id","source","source_event_id","core_name","event_type","detail","created_at"}},
    "janus_deliberation_tasks": {"owner": "deliberation_tasks.py", "version": 1, "critical": False, "columns": {"id","profile_id","source_message","topic","status","pass_count","current_summary","created_at","updated_at"}},
    "janus_message_threads": {"owner": "proactive_threads.py", "version": 1, "critical": False, "columns": {"event_id","profile_id","thread_key","thread_type","title","source_event","confidence","created_at"}},
    "janus_reliability_audits": {"owner": "reliability_audit.py", "version": 1, "critical": False, "columns": {"id","profile_id","overall","summary_json","created_at"}},
    "janus_files": {"owner": "attachment_api.py", "version": 1, "critical": False, "columns": {"id","account_id","original_name","mime_type","size_bytes","sha256","storage_name","created_at"}},
    "janus_generated_images": {"owner": "image_generation.py", "version": 1, "critical": False, "columns": {"id","account_id","file_id","prompt_hash","prompt","model","quality","size","origin","created_at"}},
    "janus_schema_meta": {"owner": "persistence_matrix.py/reliability_audit.py", "version": 2, "critical": False, "columns": {"key","value","updated_at"}},
}


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _exists(c: sqlite3.Connection, table: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(c: sqlite3.Connection, table: str) -> set[str]:
    if not _exists(c, table):
        return set()
    return {str(r[1]) for r in c.execute(f'PRAGMA table_info("{table}")')}


def _inspect(c: sqlite3.Connection) -> list[dict[str, Any]]:
    rows=[]
    for table, spec in TABLES.items():
        present=_exists(c, table)
        cols=_columns(c, table) if present else set()
        missing=sorted(set(spec["columns"]) - cols) if present else []
        rows.append({
            "table": table,
            "owner": spec["owner"],
            "schema_version": int(spec["version"]),
            "critical": bool(spec["critical"]),
            "present": present,
            "compatible": (not present) or not missing,
            "missing_columns": missing,
            "extra_columns": sorted(cols - set(spec["columns"])) if present else [],
        })
    return rows


def preflight_existing() -> dict[str, Any]:
    """Validate already-existing schemas before application modules can write.

    Missing tables are normal on a clean installation. An existing table missing a
    required column is incompatible. Critical incompatibilities raise immediately;
    optional incompatibilities are reported so their subsystem can be reviewed.
    """
    with _db() as c:
        try:
            quick=str(c.execute("PRAGMA quick_check").fetchone()[0])
        except Exception as exc:
            raise RuntimeError(f"JANUS persistence quick_check failed: {type(exc).__name__}: {exc}") from exc
        if quick.lower() != "ok":
            raise RuntimeError(f"JANUS persistence quick_check failed: {quick}")
        rows=_inspect(c)
    critical=[x for x in rows if x["present"] and not x["compatible"] and x["critical"]]
    optional=[x for x in rows if x["present"] and not x["compatible"] and not x["critical"]]
    if critical:
        detail="; ".join(f"{x['table']} missing {','.join(x['missing_columns'])}" for x in critical)
        raise RuntimeError("Incompatible JANUS persistence schema; refusing full startup before writes: " + detail)
    return {"ok": True, "matrix_version": MATRIX_VERSION, "critical_incompatibilities": [], "optional_incompatibilities": optional, "tables": rows}


def record_current_matrix() -> dict[str, Any]:
    """Record the observed schema/version matrix after subsystem initialization."""
    now=int(time.time())
    with _db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS janus_schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at INTEGER NOT NULL)")
        rows=_inspect(c)
        payload={
            "matrix_version": MATRIX_VERSION,
            "tables": {x["table"]: {"owner":x["owner"],"version":x["schema_version"],"present":x["present"],"compatible":x["compatible"]} for x in rows},
        }
        c.execute("INSERT INTO janus_schema_meta(key,value,updated_at) VALUES('persistence_matrix_version',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (str(MATRIX_VERSION), now))
        c.execute("INSERT INTO janus_schema_meta(key,value,updated_at) VALUES('persistence_matrix_snapshot',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (json.dumps(payload,separators=(",",":"),sort_keys=True), now))
        c.commit()
    incompatible=[x for x in rows if x["present"] and not x["compatible"]]
    return {"ok": not incompatible, "matrix_version": MATRIX_VERSION, "incompatible": incompatible, "tables": rows}


def status() -> dict[str, Any]:
    with _db() as c:
        rows=_inspect(c)
        meta={}
        if _exists(c,"janus_schema_meta"):
            for r in c.execute("SELECT key,value,updated_at FROM janus_schema_meta WHERE key LIKE 'persistence_matrix_%'"):
                meta[str(r["key"])]= {"value":str(r["value"]),"updated_at":int(r["updated_at"])}
    incompatible=[x for x in rows if x["present"] and not x["compatible"]]
    return {"ok": not incompatible, "matrix_version": MATRIX_VERSION, "incompatible": incompatible, "tables": rows, "meta": meta}
