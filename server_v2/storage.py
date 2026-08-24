from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

DB_PATH = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
FILE_ROOT = Path(os.getenv("JANUS_FILE_ROOT", "/data/janus_files_v2"))


@contextmanager
def db():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def now() -> int:
    return int(time.time())


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def jload(value: str | None, default: Any):
    try:
        return json.loads(value or "")
    except Exception:
        return default


def init_schema() -> None:
    FILE_ROOT.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS v2_accounts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE COLLATE NOCASE,
              email TEXT NOT NULL UNIQUE COLLATE NOCASE,
              password_hash TEXT,
              google_sub TEXT UNIQUE,
              email_verified INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v2_sessions(
              token_hash TEXT PRIMARY KEY,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_sessions_account ON v2_sessions(account_id);

            CREATE TABLE IF NOT EXISTS v2_auth_tokens(
              token_hash TEXT PRIMARY KEY,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              purpose TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS v2_memories(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              tier TEXT NOT NULL DEFAULT 'working',
              kind TEXT NOT NULL DEFAULT 'conversation',
              content TEXT NOT NULL,
              salience REAL NOT NULL DEFAULT 0.5,
              access_count INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_memories_account_time ON v2_memories(account_id,updated_at DESC);

            CREATE TABLE IF NOT EXISTS v2_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              core_name TEXT NOT NULL,
              event_type TEXT NOT NULL,
              mode TEXT NOT NULL DEFAULT 'foreground',
              detail TEXT NOT NULL,
              public_detail TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_events_account_time ON v2_events(account_id,id DESC);

            CREATE TABLE IF NOT EXISTS v2_messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              message_type TEXT NOT NULL,
              detail TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'janus',
              state TEXT NOT NULL DEFAULT 'unread',
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_messages_account_state ON v2_messages(account_id,state,id DESC);

            CREATE TABLE IF NOT EXISTS v2_chat_receipts(
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              client_message_id TEXT NOT NULL,
              response_json TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY(account_id,client_message_id)
            );

            CREATE TABLE IF NOT EXISTS v2_files(
              id TEXT PRIMARY KEY,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              filename TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              storage_path TEXT NOT NULL,
              extracted_text TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL,
              last_used_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_files_account_time ON v2_files(account_id,created_at DESC);

            CREATE TABLE IF NOT EXISTS v2_claims(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              statement TEXT NOT NULL,
              claim_kind TEXT NOT NULL DEFAULT 'hypothesis',
              epistemic_state TEXT NOT NULL DEFAULT 'open',
              domain TEXT NOT NULL DEFAULT 'general',
              tags_json TEXT NOT NULL DEFAULT '[]',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_claims_account ON v2_claims(account_id,id DESC);

            CREATE TABLE IF NOT EXISTS v2_research(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              mode TEXT NOT NULL,
              query TEXT NOT NULL,
              result TEXT NOT NULL,
              sources_json TEXT NOT NULL DEFAULT '[]',
              useful INTEGER,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_research_account_time ON v2_research(account_id,id DESC);

            CREATE TABLE IF NOT EXISTS v2_artifacts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              file_id TEXT NOT NULL REFERENCES v2_files(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS v2_device_presence(
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              device_id TEXT NOT NULL,
              client_version TEXT NOT NULL DEFAULT '',
              phase TEXT NOT NULL DEFAULT 'unknown',
              state_json TEXT NOT NULL DEFAULT '{}',
              last_seen_at INTEGER NOT NULL,
              PRIMARY KEY(account_id,device_id)
            );

            CREATE TABLE IF NOT EXISTS v2_maintenance(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER,
              report_json TEXT NOT NULL,
              review_state TEXT NOT NULL DEFAULT 'awaiting_owner_review',
              created_at INTEGER NOT NULL,
              decided_at INTEGER
            );
            """
        )


def account_by_identifier(identifier: str):
    value = (identifier or "").strip()
    with db() as c:
        return c.execute(
            "SELECT * FROM v2_accounts WHERE lower(username)=lower(?) OR lower(email)=lower(?) LIMIT 1",
            (value, value),
        ).fetchone()


def account_by_id(account_id: int):
    with db() as c:
        return c.execute("SELECT * FROM v2_accounts WHERE id=?", (int(account_id),)).fetchone()


def create_account(username: str, email: str, password_hash: str | None = None, google_sub: str | None = None, email_verified: bool = False):
    ts = now()
    with db() as c:
        cur = c.execute(
            "INSERT INTO v2_accounts(username,email,password_hash,google_sub,email_verified,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (username.strip(), email.strip().lower(), password_hash, google_sub, int(email_verified), ts, ts),
        )
        return c.execute("SELECT * FROM v2_accounts WHERE id=?", (cur.lastrowid,)).fetchone()


def update_account(account_id: int, **fields):
    allowed = {"username", "email", "password_hash", "google_sub", "email_verified"}
    pairs = [(k, v) for k, v in fields.items() if k in allowed]
    if not pairs:
        return account_by_id(account_id)
    sets = ",".join(f"{k}=?" for k, _ in pairs) + ",updated_at=?"
    vals = [v for _, v in pairs] + [now(), int(account_id)]
    with db() as c:
        c.execute(f"UPDATE v2_accounts SET {sets} WHERE id=?", vals)
    return account_by_id(account_id)


def delete_account(account_id: int) -> None:
    with db() as c:
        paths = [r[0] for r in c.execute("SELECT storage_path FROM v2_files WHERE account_id=?", (int(account_id),)).fetchall()]
        c.execute("DELETE FROM v2_accounts WHERE id=?", (int(account_id),))
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


def token_hash(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session(account_id: int, days: int = 30) -> str:
    token = secrets.token_urlsafe(40)
    ts = now()
    with db() as c:
        c.execute(
            "INSERT INTO v2_sessions(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",
            (token_hash(token), int(account_id), ts, ts + days * 86400),
        )
    return token


def account_for_session(token: str):
    if not token:
        return None
    ts = now()
    with db() as c:
        row = c.execute(
            "SELECT a.* FROM v2_sessions s JOIN v2_accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>?",
            (token_hash(token), ts),
        ).fetchone()
    return row


def revoke_session(token: str) -> None:
    with db() as c:
        c.execute("DELETE FROM v2_sessions WHERE token_hash=?", (token_hash(token),))


def revoke_all_sessions(account_id: int) -> None:
    with db() as c:
        c.execute("DELETE FROM v2_sessions WHERE account_id=?", (int(account_id),))


def issue_auth_token(account_id: int, purpose: str, ttl_seconds: int = 3600) -> str:
    token = secrets.token_urlsafe(24)
    ts = now()
    with db() as c:
        c.execute(
            "INSERT INTO v2_auth_tokens(token_hash,account_id,purpose,created_at,expires_at) VALUES(?,?,?,?,?)",
            (token_hash(token), int(account_id), purpose, ts, ts + ttl_seconds),
        )
    return token


def consume_auth_token(token: str, purpose: str):
    h = token_hash(token)
    with db() as c:
        row = c.execute(
            "SELECT * FROM v2_auth_tokens WHERE token_hash=? AND purpose=? AND expires_at>?",
            (h, purpose, now()),
        ).fetchone()
        if row:
            c.execute("DELETE FROM v2_auth_tokens WHERE token_hash=?", (h,))
        return row


def add_event(account_id: int, core: str, event_type: str, detail: str, public_detail: str | None = None, mode: str = "foreground") -> int:
    pub = (public_detail if public_detail is not None else detail)[:12000]
    with db() as c:
        cur = c.execute(
            "INSERT INTO v2_events(account_id,core_name,event_type,mode,detail,public_detail,created_at) VALUES(?,?,?,?,?,?,?)",
            (int(account_id), core, event_type, mode, detail[:50000], pub, now()),
        )
        return int(cur.lastrowid)


def add_memory(account_id: int, content: str, tier: str = "working", kind: str = "conversation", salience: float = 0.5) -> int:
    text = " ".join((content or "").split()).strip()
    if not text:
        return 0
    ts = now()
    with db() as c:
        row = c.execute(
            "SELECT id,access_count,tier,salience FROM v2_memories WHERE account_id=? AND lower(content)=lower(?) ORDER BY id DESC LIMIT 1",
            (int(account_id), text),
        ).fetchone()
        if row:
            access = int(row["access_count"]) + 1
            ladder = ["trace", "working", "episodic", "core"]
            current = row["tier"] if row["tier"] in ladder else "working"
            promoted = ladder[min(len(ladder)-1, ladder.index(current) + (1 if access in {3, 7, 15} else 0))]
            c.execute(
                "UPDATE v2_memories SET access_count=?,tier=?,salience=?,updated_at=? WHERE id=?",
                (access, promoted, max(float(row["salience"]), salience), ts, int(row["id"])),
            )
            return int(row["id"])
        cur = c.execute(
            "INSERT INTO v2_memories(account_id,tier,kind,content,salience,access_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (int(account_id), tier, kind, text[:20000], float(salience), 0, ts, ts),
        )
        return int(cur.lastrowid)


def list_memories(account_id: int, limit: int = 80):
    with db() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,tier,kind,content,salience,access_count,created_at,updated_at FROM v2_memories WHERE account_id=? ORDER BY CASE tier WHEN 'core' THEN 4 WHEN 'episodic' THEN 3 WHEN 'working' THEN 2 ELSE 1 END DESC,updated_at DESC LIMIT ?",
            (int(account_id), max(1, min(200, int(limit)))),
        ).fetchall()]


def relevant_memories(account_id: int, query: str, limit: int = 12) -> list[dict[str, Any]]:
    words = [w.lower() for w in (query or "").split() if len(w) > 3][:12]
    rows = list_memories(account_id, 120)
    scored = []
    for r in rows:
        content = r["content"].lower()
        overlap = sum(1 for w in words if w in content)
        tier_bonus = {"core": 4, "episodic": 2, "working": 1, "trace": 0}.get(r["tier"], 0)
        scored.append((overlap * 5 + tier_bonus + float(r.get("salience") or 0), r))
    picked = [r for score, r in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0][:limit]
    if picked:
        ids = [int(x["id"]) for x in picked]
        with db() as c:
            c.executemany("UPDATE v2_memories SET access_count=access_count+1,updated_at=? WHERE id=?", [(now(), x) for x in ids])
    return picked


def add_message(account_id: int, message_type: str, detail: str, source: str = "janus") -> int:
    with db() as c:
        cur = c.execute(
            "INSERT INTO v2_messages(account_id,message_type,detail,source,state,created_at) VALUES(?,?,?,?,?,?)",
            (int(account_id), message_type, detail[:12000], source, "unread", now()),
        )
        return int(cur.lastrowid)


def file_path(file_id: str) -> Path:
    return FILE_ROOT / file_id[:2] / file_id


def save_file(account_id: int, filename: str, mime: str, data: bytes, extracted_text: str = "") -> dict[str, Any]:
    import uuid
    fid = uuid.uuid4().hex
    path = file_path(fid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    ts = now()
    with db() as c:
        c.execute(
            "INSERT INTO v2_files(id,account_id,filename,mime_type,size_bytes,storage_path,extracted_text,created_at,last_used_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (fid, int(account_id), filename[:240], mime[:160], len(data), str(path), extracted_text[:200000], ts, ts),
        )
    return {"id": fid, "filename": filename, "mime_type": mime, "size_bytes": len(data), "created_at": ts}


def get_file(account_id: int, file_id: str):
    with db() as c:
        row = c.execute("SELECT * FROM v2_files WHERE id=? AND account_id=?", (file_id, int(account_id))).fetchone()
        if row:
            c.execute("UPDATE v2_files SET last_used_at=? WHERE id=?", (now(), file_id))
        return row


def rows(sql: str, args: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with db() as c:
        return [dict(r) for r in c.execute(sql, tuple(args)).fetchall()]


def one(sql: str, args: Iterable[Any] = ()):
    with db() as c:
        return c.execute(sql, tuple(args)).fetchone()


def execute(sql: str, args: Iterable[Any] = ()) -> int:
    with db() as c:
        cur = c.execute(sql, tuple(args))
        return int(cur.lastrowid or 0)
