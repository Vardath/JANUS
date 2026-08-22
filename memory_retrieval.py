"""Durable JANUS conversation-memory retrieval.

Conversation history is persisted in desktop_memory. Retrieval searches the whole
retained profile history, prefers the user's own statements, and now preserves the
*thread around* explicit memory/attention signals such as "remember this",
"think about this", "ponder this", and "mull this over".
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

_MEMORY_SIGNALS = (
    "remember", "remember this", "remember that", "don't forget", "do not forget",
    "keep this in mind", "keep that in mind", "retain this", "retain that",
    "think about this", "think about that", "think this over", "think it over",
    "ponder this", "ponder that", "ponder it", "ponder on this",
    "mull this over", "mull it over", "mull over this", "mull over that",
    "consider this", "consider that", "reflect on this", "reflect on that",
    "come back to this", "we'll come back to this", "we will come back to this",
    "from now on", "my cosmology", "my theory", "my research", "that is not", "i mean",
)


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", str(text or "").lower()) if w not in _STOP}


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _has_memory_signal(text: str) -> bool:
    low = " ".join(str(text or "").lower().split())
    return any(m in low for m in _MEMORY_SIGNALS)


def retrieve(profile: str, query: str, *, limit: int = 22, scan_limit: int = 3000) -> list[dict[str, Any]]:
    """Return relevant retained records plus enough neighbouring context to restore a thread."""
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
        score = overlap * 8.0
        if q and toks:
            score += 12.0 * overlap / max(1, len(q))
        role = str(r["role"] or "")
        level = str(r["level"] or "trace")
        if role == "user": score += 5.0
        elif role.startswith("core_memory") or role == "memory": score += 2.5
        elif role in {"process","system"}: score -= 4.0
        score += {"core": 6.0, "episodic": 4.5, "working": 1.5, "trace": 0.0}.get(level, 0.0)
        score += 2.0 * (1.0 - (pos / total))
        if role == "user" and _has_memory_signal(content): score += 7.0
        qlow = str(query or "").lower()
        if qlow and len(qlow) > 18 and qlow[:32] in content.lower(): score += 20.0
        if overlap or (role == "user" and score >= 8):
            scored.append((score, dict(r)))

    scored.sort(key=lambda x: (x[0], int(x[1]["id"])), reverse=True)
    anchors = scored[: max(1, int(limit // 2))]
    anchor_ids = {int(x[1]["id"]) for x in anchors}

    # Restore conversational continuity around strong matches. This is the key
    # difference between remembering isolated facts and remembering the thread.
    chosen: dict[int, dict[str, Any]] = {int(x[1]["id"]): x[1] for x in anchors}
    if anchor_ids:
        try:
            with _db() as c:
                for aid in list(anchor_ids):
                    lo, hi = max(1, aid - 2), aid + 2
                    neighbors = c.execute(
                        "SELECT id,role,content,level,created_at FROM desktop_memory WHERE profile_id=? AND id BETWEEN ? AND ? ORDER BY id",
                        (profile, lo, hi),
                    ).fetchall()
                    for n in neighbors:
                        role = str(n["role"] or "")
                        if role not in {"system","process"} and len(str(n["content"] or "").strip()) >= 8:
                            chosen[int(n["id"])] = dict(n)
        except Exception:
            pass

    ordered = [chosen[k] for k in sorted(chosen)]
    if len(ordered) > limit:
        # Preserve chronological shape while trimming oldest low-priority context.
        ordered = ordered[-limit:]
    return ordered


def format_recall(profile: str, query: str, *, limit: int = 22) -> str:
    rows = retrieve(profile, query, limit=limit)
    if not rows:
        return ""
    return "\n".join(
        f"[{r.get('created_at','')}] {r.get('role','memory')} ({r.get('level','trace')}): {str(r.get('content',''))[:1800]}"
        for r in rows
    )


def promote_user_correction(profile: str, content: str) -> bool:
    """Promote explicit corrections *and attention/pondering cues* with their context.

    If the user says "think about this", "ponder it", "mull it over", etc., the
    important memory is usually not those few words alone: it is the nearby
    conversational material they refer to. Therefore the signal turn and up to six
    preceding non-system conversation turns are promoted to episodic memory.
    """
    if not _has_memory_signal(content):
        return False
    try:
        with _db() as c:
            row = c.execute(
                "SELECT id FROM desktop_memory WHERE profile_id=? AND role='user' AND content=? ORDER BY id DESC LIMIT 1",
                (profile, content),
            ).fetchone()
            if not row:
                return False
            current_id = int(row[0])
            recent = c.execute(
                "SELECT id,role FROM desktop_memory WHERE profile_id=? AND id<=? AND role NOT IN ('system','process') ORDER BY id DESC LIMIT 7",
                (profile, current_id),
            ).fetchall()
            ids = [int(r["id"]) for r in recent]
            if not ids:
                return False
            marks = ",".join("?" for _ in ids)
            c.execute(f"UPDATE desktop_memory SET level='episodic' WHERE id IN ({marks})", ids)
            c.commit()
        return True
    except Exception:
        return False
