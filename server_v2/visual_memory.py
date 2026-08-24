from __future__ import annotations

from typing import Any

from . import storage


def init_schema() -> None:
    with storage.db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS v2_visual_memory(
              file_id TEXT PRIMARY KEY REFERENCES v2_files(id) ON DELETE CASCADE,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              assessment TEXT NOT NULL,
              model TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL,
              last_used_at INTEGER NOT NULL
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_v2_visual_memory_account ON v2_visual_memory(account_id,last_used_at DESC)")


def store(account_id: int, file_id: str, assessment: str, model: str = "") -> None:
    if not assessment.strip(): return
    ts = storage.now()
    with storage.db() as c:
        c.execute(
            """INSERT INTO v2_visual_memory(file_id,account_id,assessment,model,created_at,last_used_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET
               assessment=excluded.assessment,model=excluded.model,last_used_at=excluded.last_used_at""",
            (file_id,int(account_id),assessment[:20000],model[:120],ts,ts),
        )


def get(account_id: int, file_id: str):
    row = storage.one("SELECT file_id,assessment,model,created_at,last_used_at FROM v2_visual_memory WHERE account_id=? AND file_id=?",(int(account_id),file_id))
    if row:
        storage.execute("UPDATE v2_visual_memory SET last_used_at=? WHERE account_id=? AND file_id=?",(storage.now(),int(account_id),file_id))
        return dict(row)
    return None


def retrieve(account_id: int, query: str, limit: int = 5) -> list[dict[str,Any]]:
    words = [w.lower() for w in (query or "").split() if len(w)>3][:12]
    rows = storage.rows(
        "SELECT v.file_id,v.assessment,v.model,v.created_at,v.last_used_at,f.filename FROM v2_visual_memory v JOIN v2_files f ON f.id=v.file_id WHERE v.account_id=? ORDER BY v.last_used_at DESC LIMIT 60",
        (int(account_id),),
    )
    scored=[]
    for row in rows:
        hay=(str(row.get("assessment") or "")+" "+str(row.get("filename") or "")).lower()
        score=sum(1 for w in words if w in hay)
        scored.append((score,row))
    picked=[r for score,r in sorted(scored,key=lambda x:x[0],reverse=True) if score>0][:limit]
    return picked
