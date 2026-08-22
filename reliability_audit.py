"""Step 11: non-destructive reliability/security/soak audit for JANUS.

The audit is intentionally observational. It does not repair, delete, compact or
rewrite user state. It records only audit summaries and schema-version metadata.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header

import auth

DB_PATH = Path(os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3"))
SCHEMA_VERSION = 11
router = APIRouter(prefix="/reliability", tags=["reliability"])

CORE_TABLES = {
    "accounts", "sessions", "auth_tokens", "desktop_memory",
    "janus_continuity_items", "janus_continuity_events",
    "janus_cost_events", "janus_cost_denials",
    "janus_research_claims", "janus_research_evidence",
}
ACCOUNT_SCOPED_TABLES = {
    "janus_files": "account_id",
    "janus_outbound_artifacts": "account_id",
    "janus_visual_deliberations": "account_id",
    "janus_visual_deliberation_records": "account_id",
}
PROFILE_SCOPED_TABLES = {
    "desktop_memory": "profile_id",
    "janus_continuity_items": "profile_id",
    "janus_continuity_events": "profile_id",
    "janus_cost_events": "profile_id",
    "janus_cost_denials": "profile_id",
    "janus_research_claims": "profile_id",
    "janus_research_evidence": "profile_id",
}


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _table_exists(c: sqlite3.Connection, table: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(c: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(c, table):
        return set()
    return {str(r[1]) for r in c.execute(f'PRAGMA table_info("{table}")')}


def ensure_audit_schema() -> None:
    with _db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS janus_schema_meta(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS janus_reliability_audits(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          profile_id TEXT NOT NULL,
          overall TEXT NOT NULL,
          summary_json TEXT NOT NULL,
          created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reliability_profile_time
          ON janus_reliability_audits(profile_id,created_at DESC);
        """)
        c.execute("INSERT INTO janus_schema_meta(key,value,updated_at) VALUES('reliability_schema_version',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                  (str(SCHEMA_VERSION), int(time.time())))


def _check(name: str, ok: bool, detail: str, severity: str = "error") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "severity": severity, "detail": detail}


def _duplicate_open_continuity(c: sqlite3.Connection, profile: str) -> int:
    if not _table_exists(c, "janus_continuity_items"):
        return 0
    states = ("proposed","approved","active","investigating","testing","blocked","provisional","reopened")
    marks = ",".join("?" for _ in states)
    rows = c.execute(f"SELECT lower(trim(title)) t,COUNT(*) n FROM janus_continuity_items WHERE profile_id=? AND state IN ({marks}) GROUP BY lower(trim(title)) HAVING COUNT(*)>1", (profile, *states)).fetchall()
    return sum(int(r["n"]) - 1 for r in rows)


def _repeat_ratio(c: sqlite3.Connection, profile: str) -> float:
    if not _table_exists(c, "janus_curiosity_searches") or "profile_id" not in _cols(c, "janus_curiosity_searches"):
        return 0.0
    cols = _cols(c, "janus_curiosity_searches")
    if "query" not in cols:
        return 0.0
    rows = c.execute("SELECT lower(trim(query)) q FROM janus_curiosity_searches WHERE profile_id=? ORDER BY rowid DESC LIMIT 50", (profile,)).fetchall()
    vals = [r["q"] for r in rows if r["q"]]
    if len(vals) < 2:
        return 0.0
    return round(1.0 - len(set(vals)) / len(vals), 4)


def run(profile_id: str, *, persist: bool = True) -> dict[str, Any]:
    """Run a bounded, read-mostly audit for one profile.

    No table contents are repaired or mutated. The only optional write is the audit
    summary itself plus schema-version metadata.
    """
    ensure_audit_schema()
    profile = str(profile_id or "local-user")[:160]
    checks: list[dict[str, Any]] = []
    with _db() as c:
        try:
            quick = str(c.execute("PRAGMA quick_check").fetchone()[0])
        except Exception as exc:
            quick = f"error:{type(exc).__name__}"
        checks.append(_check("sqlite_integrity", quick.lower() == "ok", "SQLite quick_check passed" if quick.lower()=="ok" else "SQLite quick_check did not pass"))

        journal = str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        checks.append(_check("wal_recovery_mode", journal == "wal", f"journal_mode={journal}", "warning"))

        tables = {str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = sorted(CORE_TABLES - tables)
        checks.append(_check("core_schema_presence", not missing, "required core tables present" if not missing else "missing: " + ", ".join(missing), "warning"))

        fk = list(c.execute("PRAGMA foreign_key_check"))
        checks.append(_check("foreign_key_integrity", len(fk) == 0, "no foreign-key violations" if not fk else f"{len(fk)} foreign-key violation(s)"))

        orphan_total = 0
        if _table_exists(c, "accounts"):
            for table, col in ACCOUNT_SCOPED_TABLES.items():
                if _table_exists(c, table) and col in _cols(c, table):
                    orphan_total += int(c.execute(f'SELECT COUNT(*) FROM "{table}" t LEFT JOIN accounts a ON a.id=t."{col}" WHERE t."{col}" IS NOT NULL AND a.id IS NULL').fetchone()[0])
        checks.append(_check("account_reference_isolation", orphan_total == 0, "no orphaned account-scoped records" if orphan_total == 0 else f"{orphan_total} orphaned account-scoped record(s)"))

        bad_profile_cols = [t for t,col in PROFILE_SCOPED_TABLES.items() if _table_exists(c,t) and col not in _cols(c,t)]
        checks.append(_check("profile_scope_schema", not bad_profile_cols, "profile-scoped tables retain profile keys" if not bad_profile_cols else "missing profile key: " + ", ".join(bad_profile_cols)))

        dupes = _duplicate_open_continuity(c, profile)
        checks.append(_check("continuity_duplicate_pressure", dupes == 0, "no duplicate open continuity titles" if dupes == 0 else f"{dupes} duplicate open continuity item(s)", "warning"))

        repeat_ratio = _repeat_ratio(c, profile)
        checks.append(_check("background_repetition", repeat_ratio <= 0.35, f"recent repeated-search ratio={repeat_ratio:.2f}", "warning"))

        if _table_exists(c, "janus_cost_events"):
            negative = int(c.execute("SELECT COUNT(*) FROM janus_cost_events WHERE estimated_usd<0 OR input_tokens<0 OR output_tokens<0").fetchone()[0])
        else:
            negative = 0
        checks.append(_check("cost_ledger_sanity", negative == 0, "cost ledger values are non-negative" if negative == 0 else f"{negative} invalid cost event(s)"))

        version = c.execute("SELECT value FROM janus_schema_meta WHERE key='reliability_schema_version'").fetchone()
        checks.append(_check("schema_version_tracking", bool(version and str(version[0]) == str(SCHEMA_VERSION)), f"schema version {SCHEMA_VERSION} tracked"))

    errors = [x for x in checks if not x["ok"] and x["severity"] == "error"]
    warnings = [x for x in checks if not x["ok"] and x["severity"] == "warning"]
    overall = "healthy" if not errors and not warnings else ("warning" if not errors else "degraded")
    out = {
        "step": 11,
        "profile_id": profile,
        "overall": overall,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "non_destructive": True,
        "autonomous_repair": False,
        "timestamp": int(time.time()),
    }
    if persist:
        with _db() as c:
            c.execute("INSERT INTO janus_reliability_audits(profile_id,overall,summary_json,created_at) VALUES(?,?,?,?)",
                      (profile, overall, json.dumps(out, separators=(",", ":")), out["timestamp"]))
    return out


def history(profile_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_audit_schema()
    with _db() as c:
        rows = c.execute("SELECT id,overall,summary_json,created_at FROM janus_reliability_audits WHERE profile_id=? ORDER BY id DESC LIMIT ?", (str(profile_id)[:160], max(1,min(100,int(limit))))).fetchall()
    result=[]
    for r in rows:
        d=json.loads(r["summary_json"]); d["audit_id"]=r["id"]; result.append(d)
    return result


@router.get("/status")
def reliability_status(authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    return {"ok": True, "audit": run(str(account["username"]), persist=True)}


@router.get("/history")
def reliability_history(limit: int = 20, authorization: Optional[str] = Header(default=None)):
    account = auth.require_account(authorization)
    return {"ok": True, "items": history(str(account["username"]), limit)}
