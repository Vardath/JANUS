"""Longitudinal quality for JANUS background cognition.

Step 7 turns isolated background findings into a small, diversity-aware research
portfolio.  It suppresses repeated topic loops and, at most rarely, asks the
background model to connect two genuinely distinct completed research notes.
The resulting synthesis is only a candidate event; autonomous_messages.py still
applies its separate interrupt-worthiness gate before anything reaches Messages.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from openai import AsyncOpenAI

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
MODEL = os.environ.get("JANUS_BACKGROUND_MODEL", "gpt-5.6-luna")
SYNTHESIS_DAILY_CAP = max(0, int(os.environ.get("JANUS_BACKGROUND_SYNTHESIS_DAILY_CAP", "1")))
SYNTHESIS_MIN_GAP_SECONDS = max(3600, int(os.environ.get("JANUS_BACKGROUND_SYNTHESIS_MIN_GAP_SECONDS", "21600")))

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_STOP = {
    "the","and","that","this","with","from","have","what","when","where","which","would","could","should",
    "about","into","your","you","are","was","were","been","will","then","than","them","they","their","there",
    "some","more","also","using","between","through","because","janus","core","cores","research","result",
    "evidence","source","current","recent","find","found","finding","topic","material","question",
}


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS janus_background_synthesis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id TEXT NOT NULL,
        left_search_id INTEGER NOT NULL,
        right_search_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        result TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        completed_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_background_synthesis_profile_time
        ON janus_background_synthesis(profile_id,created_at);
    """)
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(str(text or "")) if w.lower() not in _STOP}


def similarity(a: str, b: str) -> float:
    x, y = tokens(a), tokens(b)
    if not x or not y:
        return 0.0
    return len(x & y) / max(1, len(x | y))


def topic_signature(text: str, limit: int = 8) -> list[str]:
    counts: dict[str,int] = {}
    for w in _WORD.findall(str(text or "").lower()):
        if w not in _STOP:
            counts[w] = counts.get(w, 0) + 1
    return [w for w,_ in sorted(counts.items(), key=lambda kv:(-kv[1],kv[0]))[:limit]]


def query_is_repetitive(query: str, recent_queries: Iterable[str], threshold: float = 0.58) -> bool:
    return any(similarity(query, old) >= threshold for old in recent_queries if str(old or "").strip())


def recent_queries(profile: str, limit: int = 16) -> list[str]:
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT query FROM janus_curiosity_searches WHERE profile_id=? AND status IN ('pending','complete') ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
        return [str(r["query"] or "") for r in rows]
    except Exception:
        return []


def _recent_research(profile: str, limit: int = 14) -> list[dict[str,Any]]:
    try:
        with _db() as c:
            rows = c.execute(
                "SELECT id,core_name,mode,query,result,sources_json,completed_at FROM janus_curiosity_searches "
                "WHERE profile_id=? AND status='complete' AND length(result)>80 ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _used_pairs(profile: str) -> set[tuple[int,int]]:
    try:
        with _db() as c:
            rows = c.execute("SELECT left_search_id,right_search_id FROM janus_background_synthesis WHERE profile_id=?", (profile,)).fetchall()
        return {tuple(sorted((int(r[0]),int(r[1])))) for r in rows}
    except Exception:
        return set()


def _choose_pair(profile: str) -> tuple[dict[str,Any],dict[str,Any]] | None:
    rows = _recent_research(profile)
    used = _used_pairs(profile)
    best = None; best_score = -1.0
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            pair = tuple(sorted((int(a["id"]), int(b["id"]))))
            if pair in used:
                continue
            sim = similarity(str(a.get("result") or ""), str(b.get("result") or ""))
            # Prefer distinct notes with a little conceptual overlap: enough to
            # make a connection plausible, but not merely duplicate searches.
            if sim > 0.55:
                continue
            mode_bonus = 0.12 if a.get("mode") != b.get("mode") else 0.0
            core_bonus = 0.10 if a.get("core_name") != b.get("core_name") else 0.0
            bridge = 1.0 - abs(sim - 0.18)
            score = bridge + mode_bonus + core_bonus
            if score > best_score:
                best_score = score; best = (a,b)
    return best


def _seconds_since_last(profile: str) -> float:
    try:
        with _db() as c:
            row = c.execute("SELECT created_at FROM janus_background_synthesis WHERE profile_id=? ORDER BY id DESC LIMIT 1", (profile,)).fetchone()
        if not row:
            return 1e12
        stamp = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc)-stamp.astimezone(timezone.utc)).total_seconds())
    except Exception:
        return 1e12


def _today_count(profile: str) -> int:
    try:
        with _db() as c:
            row = c.execute("SELECT COUNT(*) FROM janus_background_synthesis WHERE profile_id=? AND substr(created_at,1,10)=?", (profile,_today())).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0


async def maybe_synthesize(profile: str) -> dict[str,Any] | None:
    """Create at most a rare cross-research synthesis candidate."""
    if SYNTHESIS_DAILY_CAP <= 0 or not os.environ.get("OPENAI_API_KEY", "").strip():
        return None
    if _today_count(profile) >= SYNTHESIS_DAILY_CAP or _seconds_since_last(profile) < SYNTHESIS_MIN_GAP_SECONDS:
        return None
    pair = _choose_pair(profile)
    if not pair:
        return None
    left,right = pair
    with _db() as c:
        cur = c.execute(
            "INSERT INTO janus_background_synthesis(profile_id,left_search_id,right_search_id,status,created_at) VALUES(?,?,?,'pending',?)",
            (profile,int(left['id']),int(right['id']),_now()),
        )
        sid = int(cur.lastrowid)
    prompt = (
        "JANUS has two independently acquired background research notes. Decide whether connecting them yields a genuinely useful new insight. "
        "Do not force a connection. Prefer a concrete contradiction, shared mechanism, boundary condition, prediction, or test. "
        "Do not discuss JANUS architecture, cycles, Fano values, or the fact that processing occurred. "
        "Return ONLY JSON: {\"useful\":true|false,\"connection\":\"...\",\"why_it_matters\":\"...\",\"test_or_question\":\"...\",\"reason\":\"...\"}.\n\n"
        f"NOTE A ({left.get('mode')}/{left.get('core_name')}):\nQuery: {left.get('query')}\n{str(left.get('result') or '')[:4500]}\n\n"
        f"NOTE B ({right.get('mode')}/{right.get('core_name')}):\nQuery: {right.get('query')}\n{str(right.get('result') or '')[:4500]}"
    )
    useful=False; text=""; reason="model-declined"
    try:
        response = await AsyncOpenAI().responses.create(model=MODEL,input=prompt,max_output_tokens=700)
        raw=(response.output_text or "").strip()
        if raw.startswith("```"):
            raw=raw.strip("`").removeprefix("json").strip()
        data=json.loads(raw)
        useful=bool(data.get("useful")) if isinstance(data,dict) else False
        if useful:
            parts=[str(data.get("connection") or "").strip(),str(data.get("why_it_matters") or "").strip(),str(data.get("test_or_question") or "").strip()]
            text=" ".join(x for x in parts if x)[:5000]
            reason=str(data.get("reason") or "cross-research synthesis")
        elif isinstance(data,dict):
            reason=str(data.get("reason") or reason)
    except Exception as exc:
        reason=f"{type(exc).__name__}: {exc}"[:500]
    with _db() as c:
        c.execute("UPDATE janus_background_synthesis SET status=?,result=?,reason=?,completed_at=? WHERE id=?",('complete' if useful else 'declined',text,reason,_now(),sid))
        if useful and text:
            detail=json.dumps({
                "text":text,"reason":reason,"left_search_id":left['id'],"right_search_id":right['id'],
                "themes":sorted(set(topic_signature(str(left.get('result') or ''))+topic_signature(str(right.get('result') or ''))))[:12],
            },ensure_ascii=False)
            c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"background_synthesis",detail,_now()))
            c.execute("INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",(profile,"background_synthesis",text,"working",_now()))
    return {"id":sid,"useful":useful,"reason":reason,"left":left['id'],"right":right['id']}


def portfolio_status(profile: str) -> dict[str,Any]:
    rows=_recent_research(profile,20)
    themes=[]
    for r in rows:
        themes.extend(topic_signature(str(r.get('result') or ''),5))
    unique=sorted(set(themes))
    try:
        with _db() as c:
            s=c.execute("SELECT COUNT(*) n, SUM(CASE WHEN status='complete' THEN 1 ELSE 0 END) useful FROM janus_background_synthesis WHERE profile_id=?",(profile,)).fetchone()
        synth_total=int(s['n'] or 0); synth_useful=int(s['useful'] or 0)
    except Exception:
        synth_total=synth_useful=0
    return {
        "recent_completed_research":len(rows),
        "distinct_recent_themes":len(unique),
        "theme_sample":unique[:14],
        "synthesis_daily_cap":SYNTHESIS_DAILY_CAP,
        "synthesis_min_gap_seconds":SYNTHESIS_MIN_GAP_SECONDS,
        "syntheses_attempted":synth_total,
        "syntheses_useful":synth_useful,
    }
