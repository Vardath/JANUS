"""Small read-only bridge from persisted deliberation tasks into device sync."""
from __future__ import annotations
import os, sqlite3

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")


def active_for_profile(profile_id: str) -> dict:
    profile = str(profile_id or "").strip()
    if not profile:
        return {}
    try:
        c = sqlite3.connect(DB_PATH, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            row = c.execute(
                "SELECT id,topic,pass_count,current_summary,last_pass_at,updated_at "
                "FROM janus_deliberation_tasks WHERE profile_id=? AND status='active' "
                "ORDER BY updated_at DESC,id DESC LIMIT 1",
                (profile,),
            ).fetchone()
        finally:
            c.close()
        if not row:
            return {}
        return {
            "id": int(row["id"]),
            "topic": str(row["topic"] or "")[:5000],
            "pass_count": int(row["pass_count"] or 0),
            "current_summary": str(row["current_summary"] or "")[:4000],
            "last_pass_at": row["last_pass_at"],
            "updated_at": row["updated_at"],
        }
    except Exception:
        return {}
