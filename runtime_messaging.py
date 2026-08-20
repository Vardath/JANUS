"""Runtime messaging integration for JANUS.

Adds a real Messages/outbox action to chat and promotes selected background reflections
into the outbox. The machine action is stripped before chat text is returned.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from fastapi import HTTPException
from openai import AsyncOpenAI

import dashboard_api as core

_ACTION_RE = re.compile(r"<janus_message>\s*(\{.*?\})\s*</janus_message>", re.IGNORECASE | re.DOTALL)
_TYPES = {
    "question": "Question",
    "observation": "Observation",
    "memory": "Memory",
    "follow-up": "Follow-up",
    "follow_up": "Follow-up",
    "followup": "Follow-up",
}


def _message_type(value: Any) -> str:
    return _TYPES.get(str(value or "follow-up").strip().lower(), "Follow-up")


def _store_outbox(profile: str, message_type: str, text: str, source: str) -> bool:
    text = str(text or "").strip()
    if not text:
        return False
    c = core._connect()
    if not c:
        return False
    try:
        recent = c.execute(
            "SELECT detail FROM desktop_events WHERE profile_id=? AND event_type='proactive_message' ORDER BY id DESC LIMIT 30",
            (profile,),
        ).fetchall()
        for row in recent:
            raw = str(row["detail"] or "")
            try:
                old = json.loads(raw)
                old_text = str(old.get("text") or "").strip()
            except Exception:
                old_text = raw.strip()
            if old_text.casefold() == text.casefold():
                return False
        detail = json.dumps(
            {"message_type": _message_type(message_type), "text": text[:4000], "source": source},
            ensure_ascii=False,
        )
        c.execute(
            "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
            (profile, "proactive_message", detail, core._utc_now()),
        )
        c.commit()
        return True
    finally:
        c.close()


def _extract_actions(text: str) -> tuple[str, list[dict[str, str]]]:
    actions: list[dict[str, str]] = []
    for match in _ACTION_RE.finditer(text or ""):
        try:
            item = json.loads(match.group(1))
        except Exception:
            continue
        message = str(item.get("text") or "").strip()
        if message:
            actions.append({"type": _message_type(item.get("type")), "text": message})
    return _ACTION_RE.sub("", text or "").strip(), actions


def _explicit_outbox_request(message: str) -> bool:
    text = str(message or "").lower()
    signals = (
        "send it through",
        "send this through",
        "send that through",
        "put it in messages",
        "put this in messages",
        "put that in messages",
        "send me a message",
        "message me",
        "through messages",
        "outbox",
        "notification",
    )
    if any(signal in text for signal in signals):
        return True
    return "messag" in text and any(word in text for word in ("send", "formulate", "through", "test"))


async def _fallback_outbox_payload(model: str, message: str, reply: str) -> dict[str, str] | None:
    prompt = (
        "The user explicitly requested a JANUS Messages/outbox item, but the first response omitted the machine action. "
        "Return ONLY JSON with keys message_type and text. message_type must be Question, Observation, Memory, or Follow-up. "
        "text must be the standalone message JANUS should actually place in the outbox. Do not say that it was sent.\n\n"
        f"User request: {message}\n\nDraft chat reply: {reply}"
    )
    try:
        response = await AsyncOpenAI().responses.create(
            model=model,
            instructions=core.JANUS_SELF_KNOWLEDGE,
            input=prompt,
        )
        data = _json_object(response.output_text or "")
        if not data:
            return None
        text = str(data.get("text") or "").strip()
        if not text:
            return None
        return {"type": _message_type(data.get("message_type")), "text": text}
    except Exception:
        return None


def _json_object(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except Exception:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except Exception:
            return None


def _ensure_promotion_table() -> None:
    c = core._connect()
    if not c:
        return
    try:
        c.execute(
            """CREATE TABLE IF NOT EXISTS janus_reflection_promotion (
                profile_id TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                processed_at TEXT NOT NULL,
                surfaced INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(profile_id,event_id)
            )"""
        )
        c.commit()
    finally:
        c.close()


async def _promote_reflections_once() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        return
    _ensure_promotion_table()
    c = core._connect()
    if not c:
        return
    try:
        rows = c.execute(
            """SELECT e.id,e.profile_id,e.detail
               FROM desktop_events e
               LEFT JOIN janus_reflection_promotion p
                 ON p.profile_id=e.profile_id AND p.event_id=e.id
               WHERE e.event_type='background_reflection' AND p.event_id IS NULL
               ORDER BY e.id ASC LIMIT 20"""
        ).fetchall()
    finally:
        c.close()

    model = os.environ.get("JANUS_MODEL", "gpt-5.6")
    client = AsyncOpenAI()
    for row in rows:
        profile = str(row["profile_id"])
        reflection = str(row["detail"] or "")
        prompt = (
            "Decide whether this already-externalized JANUS background reflection deserves a user-facing Messages notification. "
            "Return ONLY JSON with: surface (boolean), message_type (Question, Observation, Memory, or Follow-up), "
            "message (short user-facing text). Surface only genuinely useful/new/actionable/unresolved material; routine reflections stay false.\n\n"
            + reflection
        )
        surfaced = 0
        try:
            response = await client.responses.create(
                model=model,
                instructions=core.JANUS_SELF_KNOWLEDGE,
                input=prompt,
            )
            data = _json_object(response.output_text or "")
            if data and bool(data.get("surface")):
                if _store_outbox(
                    profile,
                    _message_type(data.get("message_type")),
                    str(data.get("message") or "").strip(),
                    "background",
                ):
                    surfaced = 1
        except Exception:
            surfaced = 0

        c = core._connect()
        if c:
            try:
                c.execute(
                    "INSERT OR IGNORE INTO janus_reflection_promotion(profile_id,event_id,processed_at,surfaced) VALUES(?,?,?,?)",
                    (profile, int(row["id"]), core._utc_now(), surfaced),
                )
                c.commit()
            finally:
                c.close()
        await asyncio.sleep(0.25)


async def _promotion_worker() -> None:
    await asyncio.sleep(45)
    while True:
        if os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1":
            await _promote_reflections_once()
        interval = max(1, int(os.environ.get("JANUS_INTERVAL_MINUTES", "15")))
        await asyncio.sleep(interval * 60)


def install(app) -> None:
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == "/desktop/chat" and "POST" in getattr(route, "methods", set()))
    ]

    @app.post("/desktop/chat", tags=["desktop"])
    async def desktop_chat_runtime(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if not message:
            raise HTTPException(400, "message required")
        if not os.environ.get("OPENAI_API_KEY"):
            raise HTTPException(503, "OPENAI_API_KEY is not configured on the JANUS server")

        core._store(profile, "user", message, "chat_input")
        history = core._recent_context(profile)
        model = os.environ.get("JANUS_MODEL", "gpt-5.6")
        messaging = """
Chat and Messages are distinct channels. You have a REAL persistent Messages/outbox action.
If the user asks to send/message/put something through Messages, the outbox, or a notification,
you must execute it instead of merely claiming you did.

To execute one outbox action, append exactly this machine block at the END of your reply:
<janus_message>{"type":"Observation","text":"the actual message to place in Messages"}</janus_message>
Allowed types: Question, Observation, Memory, Follow-up.
The server strips the block before showing chat and commits the message. Never expose or explain the block.
Never claim something was sent through Messages unless you included a valid block.
Phrases such as "send it through", "message me", "put that in Messages", and "formulate something and send it" refer to this action when context is about JANUS messaging.
"""
        instructions = (
            core.JANUS_SELF_KNOWLEDGE
            + "\n\n"
            + messaging
            + "\nSpeak naturally and directly. Use the seven lenses internally, synthesize through the three bridges, then answer as one JANUS voice."
        )
        inp = message if not history else f"Recent conversation:\n{history}\n\nCurrent user message:\n{message}"
        try:
            response = await AsyncOpenAI().responses.create(model=model, instructions=instructions, input=inp)
            raw_reply = (response.output_text or "").strip()
            if not raw_reply:
                raise RuntimeError("empty response")
            reply, actions = _extract_actions(raw_reply)
            sent = sum(1 for action in actions if _store_outbox(profile, action["type"], action["text"], "chat"))

            if sent == 0 and _explicit_outbox_request(message):
                fallback = await _fallback_outbox_payload(model, message, reply or raw_reply)
                if fallback and _store_outbox(profile, fallback["type"], fallback["text"], "chat-fallback"):
                    sent = 1
                elif reply:
                    compact = re.sub(r"\s+", " ", reply).strip()
                    if compact and _store_outbox(profile, "Follow-up", compact[:700], "chat-fallback-text"):
                        sent = 1

            if not reply:
                reply = "Sent through Messages." if sent else "I couldn't create the Messages item."
            elif _explicit_outbox_request(message) and sent == 0:
                reply = "I couldn't create the Messages item, so I have not claimed it was sent. " + reply
        except Exception as exc:
            core._store(profile, "system", f"chat_error: {exc}", "chat_error")
            raise HTTPException(502, f"JANUS model request failed: {exc}")

        core._store(profile, "assistant", reply, "chat_output")
        core._store(
            profile,
            "process",
            f"Seven specialist lenses were integrated through local/global synthesis and calibration. Outbox actions executed: {sent}.",
            "synthesis_note",
        )
        return {
            "reply": reply,
            "profile": profile,
            "model": model,
            "messages_sent": sent,
            "messaging_action": True,
        }

    @app.on_event("startup")
    async def _start_runtime_message_promoter():
        if os.environ.get("JANUS_MESSAGE_QUEUE", "1") == "1":
            asyncio.create_task(_promotion_worker())
