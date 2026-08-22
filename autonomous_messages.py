"""High-value autonomous JANUS Messages.

Bridges the modern background systems (hive reflection + live curiosity research)
into the persistent Messages outbox.  It deliberately suppresses plumbing,
telemetry and repetitive self-reference.  The goal is a small number of messages
that contain an actual discovery, connection, unresolved question or useful test.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

import dashboard_api as core
from proactive_quality import assess, should_show_stored_message

DB_PATH = os.environ.get("JANUS_DB_PATH", "/data/janus.sqlite3")
SOURCE_EVENTS = ("curiosity_search_complete", "hive_language_reflection", "background_reflection")
DAILY_CAP = max(0, int(os.environ.get("JANUS_AUTONOMOUS_MESSAGES_DAILY_CAP", "3")))
MIN_GAP_SECONDS = max(900, int(os.environ.get("JANUS_AUTONOMOUS_MESSAGES_MIN_GAP_SECONDS", "10800")))
MODEL = os.environ.get("JANUS_BACKGROUND_MODEL", "gpt-5.6-luna")


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS janus_autonomous_message_review(
        event_id INTEGER PRIMARY KEY,
        profile_id TEXT NOT NULL,
        source_event TEXT NOT NULL,
        score REAL NOT NULL DEFAULT 0,
        surfaced INTEGER NOT NULL DEFAULT 0,
        reason TEXT NOT NULL DEFAULT '',
        processed_at TEXT NOT NULL
    );
    """)
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _extract(detail: Any) -> str:
    raw = str(detail or "").strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            if obj.get("result"):
                return str(obj["result"]).strip()
            if obj.get("text"):
                return str(obj["text"]).strip()
            if obj.get("note"):
                return str(obj["note"]).strip()
    except Exception:
        pass
    return raw


def _recent_outbox(profile: str, limit: int = 20) -> list[str]:
    try:
        with _db() as c:
            rows = c.execute("SELECT detail FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT ?", (profile, limit)).fetchall()
        return [_extract(r["detail"]) for r in rows]
    except Exception:
        return []


def _daily_count(profile: str) -> int:
    try:
        with _db() as c:
            rows = c.execute("SELECT detail,created_at FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' AND substr(created_at,1,10)=?", (profile, _today())).fetchall()
        count = 0
        for r in rows:
            try:
                obj = json.loads(str(r["detail"] or "{}"))
            except Exception:
                obj = {}
            if str(obj.get("source") or "").startswith("autonomous") or str(obj.get("source") or "").startswith("background"):
                count += 1
        return count
    except Exception:
        return 0


def _seconds_since_auto(profile: str) -> float:
    try:
        with _db() as c:
            rows = c.execute("SELECT detail,created_at FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT 30", (profile,)).fetchall()
        for r in rows:
            try: obj = json.loads(str(r["detail"] or "{}"))
            except Exception: obj = {}
            src = str(obj.get("source") or "")
            if src.startswith("autonomous") or src.startswith("background"):
                stamp = datetime.fromisoformat(str(r["created_at"]).replace("Z", "+00:00"))
                return max(0.0, (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds())
    except Exception:
        pass
    return 1e12


def _store(profile: str, message_type: str, text: str, source_event: str) -> bool:
    recent = _recent_outbox(profile)
    gate = assess(text, recent)
    if not gate["pass"]:
        return False
    detail = json.dumps({
        "message_type": message_type if message_type in {"Question","Observation","Memory","Follow-up"} else "Observation",
        "text": str(text).strip()[:2200],
        "source": "autonomous_quality",
        "origin": source_event,
        "quality_score": gate["score"],
    }, ensure_ascii=False)
    with _db() as c:
        c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)", (profile, "proactive_message", detail, _now()))
    return True


def _reviewed(event_id: int) -> bool:
    with _db() as c:
        return c.execute("SELECT 1 FROM janus_autonomous_message_review WHERE event_id=?", (int(event_id),)).fetchone() is not None


def _mark(event_id: int, profile: str, source_event: str, score: float, surfaced: bool, reason: str) -> None:
    with _db() as c:
        c.execute("INSERT OR REPLACE INTO janus_autonomous_message_review(event_id,profile_id,source_event,score,surfaced,reason,processed_at) VALUES(?,?,?,?,?,?,?)",
                  (int(event_id), profile, source_event, float(score), 1 if surfaced else 0, str(reason)[:500], _now()))


async def _evaluate(row: sqlite3.Row) -> None:
    event_id = int(row["id"]); profile = str(row["profile_id"]); source_event = str(row["event_type"])
    material = _extract(row["detail"])
    recent = _recent_outbox(profile)
    pre = assess(material, recent)
    # Raw source notes may be long, but telemetry-heavy/repetitive candidates are
    # never worth a paid rewrite.
    if pre["telemetry_heavy"] or pre["max_similarity"] >= 0.72 or len(material) < 70:
        _mark(event_id, profile, source_event, pre["score"], False, ",".join(pre["reasons"]) or "prefilter")
        return
    if DAILY_CAP <= 0 or _daily_count(profile) >= DAILY_CAP or _seconds_since_auto(profile) < MIN_GAP_SECONDS:
        _mark(event_id, profile, source_event, pre["score"], False, "rate-limit")
        return
    if not os.environ.get("OPENAI_API_KEY"):
        _mark(event_id, profile, source_event, pre["score"], False, "no-api-key")
        return

    prompt = (
        "Judge whether this externalized JANUS background material deserves interrupting the user with an unsolicited Messages notification. "
        "Most candidates should NOT surface. Surface only when there is concrete new subject matter: a useful discovery, non-obvious connection, serious unresolved question, contradiction, or test worth trying. "
        "Never surface cycle counts, Fano/control numbers, routing/integration descriptions, or generic statements that JANUS has been thinking. "
        "If surfacing, rewrite it as a natural standalone message that states WHAT was found/thought and WHY it matters. Keep it under 130 words. "
        "Return ONLY JSON: {\"surface\":true|false,\"message_type\":\"Question|Observation|Memory|Follow-up\",\"message\":\"...\",\"reason\":\"...\"}.\n\n"
        f"Source kind: {source_event}\nMaterial:\n{material[:6000]}"
    )
    surfaced = False; reason = "model-declined"; final_score = pre["score"]
    try:
        response = await AsyncOpenAI().responses.create(model=MODEL, input=prompt, max_output_tokens=500)
        raw = (response.output_text or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        data = json.loads(raw)
        if isinstance(data, dict) and bool(data.get("surface")):
            text = str(data.get("message") or "").strip()
            post = assess(text, recent); final_score = post["score"]
            if post["pass"]:
                surfaced = _store(profile, str(data.get("message_type") or "Observation"), text, source_event)
                reason = str(data.get("reason") or "high-value") if surfaced else "post-gate"
            else:
                reason = "post-gate:" + ",".join(post["reasons"])
        else:
            reason = str(data.get("reason") or "model-declined") if isinstance(data, dict) else "model-declined"
    except Exception as exc:
        reason = f"{type(exc).__name__}"
    _mark(event_id, profile, source_event, final_score, surfaced, reason)


async def _scan_once() -> None:
    with _db() as c:
        marks = ",".join("?" for _ in SOURCE_EVENTS)
        rows = c.execute(f"SELECT id,profile_id,event_type,detail,created_at FROM desktop_events WHERE event_type IN ({marks}) ORDER BY id ASC LIMIT 80", SOURCE_EVENTS).fetchall()
    processed = 0
    for row in rows:
        if _reviewed(int(row["id"])):
            continue
        await _evaluate(row); processed += 1
        if processed >= 12:
            break
        await asyncio.sleep(0.15)


async def _worker() -> None:
    await asyncio.sleep(55)
    while True:
        try:
            await _scan_once()
        except Exception:
            pass
        await asyncio.sleep(max(300, int(os.environ.get("JANUS_AUTONOMOUS_MESSAGE_REVIEW_SECONDS", "900"))))


def filtered_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in items:
        source = str(item.get("source") or "")
        if should_show_stored_message(item.get("detail"), source):
            out.append(item)
    return out


def status(profile: str) -> dict[str, Any]:
    with _db() as c:
        row = c.execute("SELECT COUNT(*) reviewed, COALESCE(SUM(surfaced),0) surfaced FROM janus_autonomous_message_review WHERE profile_id=?", (profile,)).fetchone()
    return {
        "enabled": True,
        "daily_cap": DAILY_CAP,
        "min_gap_seconds": MIN_GAP_SECONDS,
        "today_autonomous_messages": _daily_count(profile),
        "seconds_since_last_autonomous": _seconds_since_auto(profile),
        "reviewed": int(row["reviewed"] or 0),
        "surfaced": int(row["surfaced"] or 0),
        "source_events": list(SOURCE_EVENTS),
        "quality_policy": "concrete novelty/usefulness over activity volume; telemetry/self-reference suppressed",
    }


def install(app, message_reader=None) -> None:
    @app.on_event("startup")
    async def _start_autonomous_message_quality_worker():
        if os.environ.get("JANUS_AUTONOMOUS_MESSAGES", "1") == "1":
            asyncio.create_task(_worker())

    @app.get("/desktop/message-quality", tags=["desktop"])
    def message_quality(username: str):
        return {"profile": username, **status(username)}
