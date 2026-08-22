"""Durable JANUS conversation-memory retrieval.

The chat log is already persisted in desktop_memory. This module fixes the retrieval
side: instead of sending only the last handful of rows to the model, it searches
across the retained profile history and returns the most relevant earlier turns.
This is lightweight/local (no embedding API cost) and deliberately prefers the
user's own statements when reconstructing personal/project history.
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")

_STOP = {
    "the","and","that","this","with","from","have","has","had","was","were","are","is","be","been","being",
    "you","your","yours","me","my","mine","we","our","ours","they","their","it","its","a","an","of","to","in",
    "on","for","as","at","by","or","but","if","then","than","so","do","did","does","what","which","who","when",
    "where","why","how","about","into","out","up","down","can","could","would","should","will","just","also",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", str(text or "").lower()) if w not in _STOP}


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def retrieve(profile: str, query: str, *, limit: int = 18, scan_limit: int = 2500) -> list[dict[str, Any]]:
    """Return relevant retained records from the whole profile history.

    Scoring is lexical but intentionally broad enough for durable project/personal
    continuity. User-authored statements receive the strongest provenance weight;
    episodic/core records are preferred over transient process chatter.
    """
    q = _tokens(query)
    if not profile:
        profile = "local-user"
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? ORDER BY id DESC LIMIT ?",
                (profile, int(scan_limit)),
            ).fetchall()
    except Exception:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    total = max(1, len(rows))
    for pos, r in enumerate(rows):
        content = str(r["content"] or "").strip()
        if len(content) < 8:
            continue
        toks = _tokens(content)
        overlap = len(q & toks)
        # Strongly reward matching distinctive terms, but retain a small recency
        # component so a recent correction can outrank an older conflicting note.
        score = overlap * 8.0
        if q and toks:
            score += 12.0 * overlap / max(1, len(q))
        role = str(r["role"] or "")
        level = str(r["level"] or "trace")
        if role == "user":
            score += 4.0
        elif role.startswith("core_memory") or role == "memory":
            score += 2.5
        elif role in {"process","system"}:
            score -= 3.0
        score += {"core": 5.0, "episodic": 3.5, "working": 1.5, "trace": 0.0}.get(level, 0.0)
        score += 2.0 * (1.0 - (pos / total))
        low = content.lower()
        qlow = str(query or "").lower()
        # Correction/identity statements are valuable continuity anchors.
        if role == "user" and any(k in low for k in ("remember", "my cosmology", "my theory", "my research", "i mean", "that is not", "from now on")):
            score += 4.0
        if qlow and len(qlow) > 18 and qlow[:32] in low:
            score += 20.0
        if overlap or role == "user" and score >= 7:
            scored.append((score, dict(r)))

    scored.sort(key=lambda x: (x[0], int(x[1]["id"])), reverse=True)
    chosen = scored[: max(1, int(limit))]
    # Present selected memories chronologically so the model sees corrections in order.
    chosen.sort(key=lambda x: int(x[1]["id"]))
    return [x[1] for x in chosen]


def format_recall(profile: str, query: str, *, limit: int = 18) -> str:
    rows = retrieve(profile, query, limit=limit)
    if not rows:
        return ""
    return "\n".join(
        f"[{r.get('created_at','')}] {r.get('role','memory')} ({r.get('level','trace')}): {str(r.get('content',''))[:1800]}"
        for r in rows
    )


def promote_user_correction(profile: str, content: str) -> bool:
    """Promote explicit user corrections/remember-this statements to episodic memory.

    The original chat row is retained; this only upgrades its memory level so it is
    less likely to be drowned by process chatter later.
    """
    low = str(content or "").lower()
    markers = ("remember", "don't forget", "do not forget", "from now on", "my cosmology", "my theory", "my research", "that is not", "i mean")
    if not any(m in low for m in markers):
        return False
    try:
        with _db() as c:
            row = c.execute(
                "SELECT id FROM desktop_memory WHERE profile_id=? AND role='user' AND content=? ORDER BY id DESC LIMIT 1",
                (profile, content),
            ).fetchone()
            if not row:
                return False
            c.execute("UPDATE desktop_memory SET level='episodic' WHERE id=?", (int(row[0]),))
            c.commit()
        return True
    except Exception:
        return False
