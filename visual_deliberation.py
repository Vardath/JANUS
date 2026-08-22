"""Step 9: bounded multi-core visual deliberation scaffolding.

This module stores externalizable concept/critique/selection records for future
visual collaboration across the JANUS 7→2→1→1 society. It intentionally has no
image-generation import or render call. Autonomous/background rendering remains
impossible here until a later, explicit revenue-gated implementation.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import auth

router = APIRouter(prefix="/visual-deliberations", tags=["visual-deliberation"])
DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
MAX_OPEN_PER_ACCOUNT = max(1, int(os.getenv("JANUS_VISUAL_DELIBERATION_MAX_OPEN", "3")))
MAX_RECORDS_PER_RUN = max(4, int(os.getenv("JANUS_VISUAL_DELIBERATION_MAX_RECORDS", "24")))
MAX_CONCEPTS = max(1, int(os.getenv("JANUS_VISUAL_DELIBERATION_MAX_CONCEPTS", "3")))
MAX_CRITIQUES = max(1, int(os.getenv("JANUS_VISUAL_DELIBERATION_MAX_CRITIQUES", "8")))
MAX_REVISIONS = max(0, int(os.getenv("JANUS_VISUAL_DELIBERATION_MAX_REVISIONS", "2")))
REVENUE_GATE = os.getenv("JANUS_VISUAL_REVENUE_GATE", "0").strip().lower() in {"1", "true", "yes", "on"}
RENDERING_REQUESTED = os.getenv("JANUS_VISUAL_DELIBERATION_RENDERING", "0").strip().lower() in {"1", "true", "yes", "on"}
# Deliberation rendering is deliberately disabled in Step 9 even if an env var is
# accidentally set. A future step must replace this constant intentionally.
AUTONOMOUS_RENDERING_ENABLED = False

ALLOWED_CORES = {
    "evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty",
    "left_hemisphere", "right_hemisphere", "consensus", "interface",
}
ALLOWED_KINDS = {"concept", "critique", "selection"}


class StartRequest(BaseModel):
    topic: str
    purpose: str = "explanatory_visual"
    source: str = "foreground"


class RecordRequest(BaseModel):
    core: str
    kind: str
    text: str
    candidate_id: Optional[str] = None
    revision: int = 0
    metadata: Optional[dict] = None


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init_db() -> None:
    with _db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS janus_visual_deliberations(
            id TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            purpose TEXT NOT NULL,
            source TEXT NOT NULL,
            state TEXT NOT NULL,
            concept_count INTEGER NOT NULL DEFAULT 0,
            critique_count INTEGER NOT NULL DEFAULT 0,
            selection_count INTEGER NOT NULL DEFAULT 0,
            max_concepts INTEGER NOT NULL,
            max_critiques INTEGER NOT NULL,
            max_revisions INTEGER NOT NULL,
            rendering_enabled INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS janus_visual_deliberation_records(
            id TEXT PRIMARY KEY,
            deliberation_id TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            core TEXT NOT NULL,
            kind TEXT NOT NULL,
            candidate_id TEXT,
            revision INTEGER NOT NULL DEFAULT 0,
            text TEXT NOT NULL,
            metadata_json TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(deliberation_id) REFERENCES janus_visual_deliberations(id) ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_visual_delib_account ON janus_visual_deliberations(account_id,updated_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_visual_delib_records ON janus_visual_deliberation_records(deliberation_id,created_at)")


def policy_status() -> dict:
    return {
        "step": 9,
        "scaffolding_enabled": True,
        "revenue_gate_satisfied": REVENUE_GATE,
        "rendering_requested": RENDERING_REQUESTED,
        "autonomous_rendering_enabled": AUTONOMOUS_RENDERING_ENABLED,
        "background_rendering_enabled": False,
        "max_open_per_account": MAX_OPEN_PER_ACCOUNT,
        "max_records_per_run": MAX_RECORDS_PER_RUN,
        "max_concepts": MAX_CONCEPTS,
        "max_critiques": MAX_CRITIQUES,
        "max_revisions": MAX_REVISIONS,
        "allowed_record_kinds": sorted(ALLOWED_KINDS),
    }


def _account_id(account) -> int:
    return int(account["id"])


def start(account, req: StartRequest) -> dict:
    _init_db()
    topic = " ".join((req.topic or "").split()).strip()[:2000]
    if len(topic) < 3:
        raise HTTPException(400, "visual deliberation topic is empty")
    source = (req.source or "foreground").strip().lower()
    if source not in {"foreground", "background", "artifact", "research"}:
        source = "foreground"
    aid = _account_id(account)
    with _db() as c:
        open_count = int(c.execute("SELECT COUNT(*) FROM janus_visual_deliberations WHERE account_id=? AND state='open'", (aid,)).fetchone()[0])
        if open_count >= MAX_OPEN_PER_ACCOUNT:
            raise HTTPException(429, "visual deliberation open-run limit reached")
        now = int(time.time())
        did = uuid.uuid4().hex
        c.execute("""INSERT INTO janus_visual_deliberations(
            id,account_id,topic,purpose,source,state,max_concepts,max_critiques,max_revisions,rendering_enabled,created_at,updated_at
        ) VALUES(?,?,?,?,?,'open',?,?,?,0,?,?)""",
        (did, aid, topic, (req.purpose or "explanatory_visual")[:80], source, MAX_CONCEPTS, MAX_CRITIQUES, MAX_REVISIONS, now, now))
    return get(account, did)


def add_record(account, deliberation_id: str, req: RecordRequest) -> dict:
    _init_db()
    aid = _account_id(account)
    core = (req.core or "").strip().lower().replace(" ", "_")
    kind = (req.kind or "").strip().lower()
    text = " ".join((req.text or "").split()).strip()[:6000]
    if core not in ALLOWED_CORES:
        raise HTTPException(400, "unknown JANUS core")
    if kind not in ALLOWED_KINDS:
        raise HTTPException(400, "record kind must be concept, critique or selection")
    if len(text) < 2:
        raise HTTPException(400, "record text is empty")
    revision = max(0, int(req.revision or 0))
    with _db() as c:
        run = c.execute("SELECT * FROM janus_visual_deliberations WHERE id=? AND account_id=?", (deliberation_id, aid)).fetchone()
        if not run:
            raise HTTPException(404, "visual deliberation not found")
        if run["state"] != "open":
            raise HTTPException(409, "visual deliberation is closed")
        total = int(c.execute("SELECT COUNT(*) FROM janus_visual_deliberation_records WHERE deliberation_id=?", (deliberation_id,)).fetchone()[0])
        if total >= MAX_RECORDS_PER_RUN:
            raise HTTPException(429, "visual deliberation record limit reached")
        if revision > int(run["max_revisions"]):
            raise HTTPException(429, "visual deliberation revision limit reached")
        if kind == "concept" and int(run["concept_count"]) >= int(run["max_concepts"]):
            raise HTTPException(429, "visual concept limit reached")
        if kind == "critique" and int(run["critique_count"]) >= int(run["max_critiques"]):
            raise HTTPException(429, "visual critique limit reached")
        if kind == "selection" and core not in {"consensus", "interface"}:
            raise HTTPException(400, "only Consensus or Interface may record a final selection")
        rid = uuid.uuid4().hex
        candidate = (req.candidate_id or "").strip()[:128] or None
        now = int(time.time())
        c.execute("""INSERT INTO janus_visual_deliberation_records(
            id,deliberation_id,account_id,core,kind,candidate_id,revision,text,metadata_json,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""", (rid, deliberation_id, aid, core, kind, candidate, revision, text, json.dumps(req.metadata or {}, separators=(",", ":")), now))
        count_col = {"concept": "concept_count", "critique": "critique_count", "selection": "selection_count"}[kind]
        state_sql = ", state='selected'" if kind == "selection" else ""
        c.execute(f"UPDATE janus_visual_deliberations SET {count_col}={count_col}+1, updated_at=?{state_sql} WHERE id=? AND account_id=?", (now, deliberation_id, aid))
    return get(account, deliberation_id)


def get(account, deliberation_id: str) -> dict:
    _init_db()
    aid = _account_id(account)
    with _db() as c:
        run = c.execute("SELECT * FROM janus_visual_deliberations WHERE id=? AND account_id=?", (deliberation_id, aid)).fetchone()
        if not run:
            raise HTTPException(404, "visual deliberation not found")
        records = c.execute("SELECT id,core,kind,candidate_id,revision,text,metadata_json,created_at FROM janus_visual_deliberation_records WHERE deliberation_id=? AND account_id=? ORDER BY created_at,id", (deliberation_id, aid)).fetchall()
    return {
        "id": run["id"], "topic": run["topic"], "purpose": run["purpose"], "source": run["source"], "state": run["state"],
        "counts": {"concepts": int(run["concept_count"]), "critiques": int(run["critique_count"]), "selections": int(run["selection_count"])},
        "limits": {"concepts": int(run["max_concepts"]), "critiques": int(run["max_critiques"]), "revisions": int(run["max_revisions"]), "records": MAX_RECORDS_PER_RUN},
        "rendering_enabled": False,
        "records": [{**dict(r), "metadata": json.loads(r["metadata_json"] or "{}")} for r in records],
        "policy": policy_status(),
    }


def list_runs(account, limit: int = 20) -> dict:
    _init_db()
    aid = _account_id(account)
    limit = max(1, min(int(limit or 20), 100))
    with _db() as c:
        rows = c.execute("SELECT id,topic,purpose,source,state,concept_count,critique_count,selection_count,created_at,updated_at FROM janus_visual_deliberations WHERE account_id=? ORDER BY updated_at DESC LIMIT ?", (aid, limit)).fetchall()
    return {"items": [dict(r) for r in rows], "policy": policy_status()}


@router.get("/policy")
def visual_deliberation_policy(authorization: Optional[str] = Header(default=None)):
    auth.require_account(authorization)
    return {"ok": True, **policy_status()}


@router.post("")
def start_visual_deliberation(req: StartRequest, authorization: Optional[str] = Header(default=None)):
    return {"ok": True, "deliberation": start(auth.require_account(authorization), req)}


@router.get("")
def list_visual_deliberations(limit: int = 20, authorization: Optional[str] = Header(default=None)):
    return {"ok": True, **list_runs(auth.require_account(authorization), limit)}


@router.get("/{deliberation_id}")
def get_visual_deliberation(deliberation_id: str, authorization: Optional[str] = Header(default=None)):
    return {"ok": True, "deliberation": get(auth.require_account(authorization), deliberation_id)}


@router.post("/{deliberation_id}/records")
def add_visual_deliberation_record(deliberation_id: str, req: RecordRequest, authorization: Optional[str] = Header(default=None)):
    return {"ok": True, "deliberation": add_record(auth.require_account(authorization), deliberation_id, req)}
