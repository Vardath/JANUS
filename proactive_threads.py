"""Thread continuity for proactive JANUS Messages.

Links autonomous findings back to an explicit continuity item or durable background
thread, stores provenance, and supplies compact follow-up grounding to Chat. This
layer never creates or mutates project/question lifecycle state by itself.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

import continuity_ledger

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_STOP = {
    "the","and","that","this","with","from","have","has","was","were","are","for","you","your","what",
    "which","about","into","then","than","them","they","their","there","janus","message","background","research",
    "result","finding","found","note","question","project","think","thinking","thought","more","tell","follow","update",
}
FOLLOWUP_RE = re.compile(r"\b(that|this|it|those|that one|tell me more|what about that|follow(?: |-)?up|continue|go on|expand on that|why does that matter)\b", re.I)


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS janus_message_threads(
      event_id INTEGER PRIMARY KEY,
      profile_id TEXT NOT NULL,
      thread_key TEXT NOT NULL,
      thread_type TEXT NOT NULL,
      title TEXT NOT NULL,
      continuity_item_id INTEGER,
      source_event TEXT NOT NULL,
      source_event_id INTEGER,
      confidence REAL NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_message_threads_profile_time
      ON janus_message_threads(profile_id,event_id DESC);
    CREATE INDEX IF NOT EXISTS idx_message_threads_profile_key
      ON janus_message_threads(profile_id,thread_key,event_id DESC);
    """)
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(str(text or "")) if w.lower() not in _STOP}


def _score(material: str, item: dict[str, Any]) -> float:
    mt = _tokens(material)
    title = _tokens(item.get("title") or "")
    detail = _tokens(item.get("detail") or "")
    if not mt or not title:
        return 0.0
    title_overlap = len(mt & title)
    detail_overlap = len(mt & detail)
    if title_overlap == 0 and detail_overlap < 2:
        return 0.0
    title_ratio = title_overlap / max(1, len(title))
    detail_ratio = detail_overlap / max(1, min(12, len(detail)))
    priority = min(1.0, max(0.0, float(item.get("priority") or 0) / 100.0))
    return min(1.0, 0.58 * title_ratio + 0.27 * detail_ratio + 0.15 * priority)


def resolve_thread(profile: str, material: str) -> dict[str, Any]:
    """Resolve material to a current ledger item only when the lexical signal is useful."""
    best = None
    for item in continuity_ledger.list_items(profile, open_only=True, limit=80):
        score = _score(material, item)
        if best is None or score > best[0]:
            best = (score, item)
    if best and best[0] >= 0.34:
        item = best[1]
        return {
            "thread_key": f"continuity:{int(item['id'])}",
            "thread_type": str(item.get("kind") or "continuity"),
            "title": str(item.get("title") or "Tracked JANUS thread")[:240],
            "continuity_item_id": int(item["id"]),
            "confidence": round(float(best[0]), 3),
            "state": str(item.get("state") or ""),
        }
    sig = sorted(_tokens(material))[:8]
    key = "background:" + ("-".join(sig[:5]) if sig else "unclassified")
    title = "Background finding: " + (", ".join(sig[:5]) if sig else "unclassified topic")
    return {"thread_key": key[:220], "thread_type": "background", "title": title[:240], "continuity_item_id": None, "confidence": 0.0, "state": None}


def bind_message(event_id: int, profile: str, source_event: str, source_event_id: int | None,
                 material: str, resolved: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = resolved or resolve_thread(profile, material)
    with _db() as c:
        c.execute(
            """INSERT OR REPLACE INTO janus_message_threads
               (event_id,profile_id,thread_key,thread_type,title,continuity_item_id,source_event,source_event_id,confidence,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (int(event_id), profile, str(resolved["thread_key"]), str(resolved["thread_type"]), str(resolved["title"]),
             resolved.get("continuity_item_id"), source_event, source_event_id, float(resolved.get("confidence") or 0), _now()),
        )
    return {**resolved, "event_id": int(event_id), "source_event": source_event, "source_event_id": source_event_id}


def get_thread(profile: str, event_id: int) -> dict[str, Any] | None:
    with _db() as c:
        row = c.execute("SELECT * FROM janus_message_threads WHERE profile_id=? AND event_id=?", (profile, int(event_id))).fetchone()
    if not row:
        return None
    out = dict(row)
    cid = out.get("continuity_item_id")
    if cid:
        try:
            out["continuity"] = continuity_ledger.get_item(profile, int(cid))
        except Exception:
            out["continuity"] = None
    return out


def latest_thread(profile: str) -> dict[str, Any] | None:
    with _db() as c:
        row = c.execute("SELECT event_id FROM janus_message_threads WHERE profile_id=? ORDER BY event_id DESC LIMIT 1", (profile,)).fetchone()
    return get_thread(profile, int(row["event_id"])) if row else None


def thread_for_chat(profile: str, message: str, explicit_event_id: int | None = None) -> dict[str, Any] | None:
    """Prefer explicit reply linkage; infer only clear follow-up or topical overlap."""
    if explicit_event_id:
        return get_thread(profile, int(explicit_event_id))
    latest = latest_thread(profile)
    if not latest:
        return None
    if FOLLOWUP_RE.search(message or ""):
        return latest
    mt = _tokens(message)
    tt = _tokens(str(latest.get("title") or ""))
    if mt and tt and len(mt & tt) >= 2:
        return latest
    return None


def format_chat_context(profile: str, message: str, explicit_event_id: int | None = None) -> tuple[str, dict[str, Any] | None]:
    thread = thread_for_chat(profile, message, explicit_event_id)
    if not thread:
        return "", None
    lines = [
        "PROACTIVE THREAD CONTINUITY — this user turn refers to a prior JANUS Message.",
        f"Thread: {thread.get('title')}",
        f"Origin: {thread.get('source_event')}",
    ]
    continuity = thread.get("continuity")
    if continuity:
        lines.append(f"Tracked continuity item #{continuity['id']} [{continuity['kind']}:{continuity['state']}]: {continuity['title']}")
        if continuity.get("detail"):
            lines.append("Tracked detail: " + str(continuity["detail"])[:600])
    lines.append("Continue this subject naturally. Do not treat the follow-up as an unrelated new conversation, and do not invent lifecycle changes.")
    return "\n".join(lines), thread


def status(profile: str) -> dict[str, Any]:
    with _db() as c:
        row = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT thread_key) threads, SUM(CASE WHEN continuity_item_id IS NOT NULL THEN 1 ELSE 0 END) linked FROM janus_message_threads WHERE profile_id=?", (profile,)).fetchone()
        recent = c.execute("SELECT event_id,thread_key,thread_type,title,continuity_item_id,source_event,confidence,created_at FROM janus_message_threads WHERE profile_id=? ORDER BY event_id DESC LIMIT 8", (profile,)).fetchall()
    return {
        "messages_threaded": int(row["n"] or 0),
        "distinct_threads": int(row["threads"] or 0),
        "continuity_linked": int(row["linked"] or 0),
        "recent_threads": [dict(r) for r in recent],
    }


def _latest_proactive_event(profile: str) -> tuple[int, dict[str, Any]] | None:
    with _db() as c:
        row = c.execute("SELECT id,detail FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT 1", (profile,)).fetchone()
    if not row:
        return None
    try:
        detail = json.loads(str(row["detail"] or "{}"))
    except Exception:
        detail = {"text": str(row["detail"] or "")}
    return int(row["id"]), detail if isinstance(detail, dict) else {"text": str(detail)}


def install(app) -> None:
    """Patch autonomous outbox storage and expose thread diagnostics/API."""
    if getattr(app.state, "janus_proactive_threads_installed", False):
        return
    import autonomous_messages

    original_store = autonomous_messages._store
    if not getattr(original_store, "_janus_threaded", False):
        def threaded_store(profile: str, message_type: str, text: str, source_event: str):
            before = _latest_proactive_event(profile)
            before_id = before[0] if before else 0
            stored = original_store(profile, message_type, text, source_event)
            if not stored:
                return stored
            latest = _latest_proactive_event(profile)
            if not latest or latest[0] <= before_id:
                return stored
            event_id, detail = latest
            resolved = resolve_thread(profile, text)
            thread = bind_message(event_id, profile, source_event, None, text, resolved)
            detail["thread"] = {
                "key": thread["thread_key"],
                "type": thread["thread_type"],
                "title": thread["title"],
                "continuity_item_id": thread.get("continuity_item_id"),
                "confidence": thread.get("confidence", 0),
            }
            with _db() as c:
                c.execute("UPDATE desktop_events SET detail=? WHERE id=? AND profile_id=?", (json.dumps(detail, ensure_ascii=False), event_id, profile))
            return stored
        threaded_store._janus_threaded = True
        autonomous_messages._store = threaded_store

    @app.get("/desktop/message-thread", tags=["desktop"])
    def message_thread(username: str, event_id: int):
        return {"profile": username, "thread": get_thread(username, event_id)}

    @app.get("/desktop/message-thread-status", tags=["desktop"])
    def message_thread_status(username: str):
        return {"profile": username, **status(username)}

    app.state.janus_proactive_threads_installed = True
