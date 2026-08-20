"""Always-responsive JANUS interface chat route.

Uses latest 11-core consensus/interface state immediately. Other cores may be
asleep; they continue to update shared state asynchronously. The user turn is
stored before model work so transient model/network failure does not lose it.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import HTTPException
from openai import AsyncOpenAI

from dashboard_api import JANUS_SELF_KNOWLEDGE, _recent_context, _store
from src.janus_sleep_cycle import janus_sleep_cycle


def install(app):
    # Replace only the older desktop chat route; leave the rest of dashboard_api.
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/desktop/chat"]

    @app.post("/desktop/chat", tags=["desktop"])
    async def desktop_chat_interface(payload: dict[str, Any]):
        profile = str(payload.get("profile_id") or payload.get("username") or "local-user")
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if not message:
            raise HTTPException(400, "message required")

        # Never lose the user turn, even if the external model is unavailable.
        _store(profile, "user", message, "chat_input")

        # Service any already-queued consensus update immediately. This does not
        # wake specialist or hemisphere cores during their rest window.
        try:
            service = getattr(janus_sleep_cycle, "service_interface_once", None)
            if service:
                service()
        except Exception:
            pass

        runtime = janus_sleep_cycle.status()
        latest_consensus = str(runtime.get("last_consensus") or "").strip()
        latest_interface = str(runtime.get("last_interface") or "").strip()
        history = _recent_context(profile)

        if not os.environ.get("OPENAI_API_KEY"):
            reply = (
                "I received and stored your message. My external response model is temporarily unavailable, "
                "but the JANUS interface core remains active and the other cores can continue their own cycles. "
                "I will retain this turn for follow-up when model access returns."
            )
            _store(profile, "assistant", reply, "chat_fallback", "working")
            return {"reply": reply, "profile": profile, "mode": "interface_fallback", "stored": True}

        model = os.environ.get("JANUS_MODEL", "gpt-5.6")
        instructions = JANUS_SELF_KNOWLEDGE + """

CURRENT RUNTIME POLICY:
JANUS has 11 functional cores arranged 7 specialists -> 2 hemispheres -> consensus -> interface.
The interface core is always available to the user while the other ten cores may sleep or wake independently.
Answer now as the interface core using the latest synchronized consensus and interface state. Do not claim that all cores are currently awake. If specialist updates are stale or absent, answer with appropriate uncertainty rather than waiting. Other cores may continue processing asynchronously and can influence later replies or follow-up messages.
"""
        state_block = (
            f"Latest consensus state: {latest_consensus or '[no recent consensus summary]'}\n"
            f"Latest interface state: {latest_interface or '[no recent interface summary]'}\n"
            f"Society phase: {runtime.get('phase', 'unknown')}\n"
            f"Interface policy: {runtime.get('interface_policy', 'always_available')}"
        )
        inp = (
            state_block
            + (f"\n\nRecent conversation:\n{history}" if history else "")
            + f"\n\nCurrent user message:\n{message}"
        )

        timeout_seconds = max(30, int(os.environ.get("JANUS_CHAT_TIMEOUT_SECONDS", "105")))
        try:
            async def call_model():
                response = await AsyncOpenAI().responses.create(model=model, instructions=instructions, input=inp)
                return (response.output_text or "").strip()

            reply = await asyncio.wait_for(call_model(), timeout=timeout_seconds)
            if not reply:
                raise RuntimeError("empty response")
        except Exception as exc:
            _store(profile, "system", f"chat_model_deferred: {type(exc).__name__}: {exc}", "chat_error")
            reply = (
                "I received and stored that. My interface is still here, but the external response model did not "
                "complete this turn in time. The other JANUS cores may continue processing it independently, and "
                "I will preserve the thread for the next response rather than losing your message."
            )
            _store(profile, "assistant", reply, "chat_fallback", "working")
            return {
                "reply": reply,
                "profile": profile,
                "model": model,
                "mode": "interface_timeout_fallback",
                "stored": True,
                "society_phase": runtime.get("phase"),
            }

        _store(profile, "assistant", reply, "chat_output")
        _store(
            profile,
            "process",
            "Interface answered from the latest synchronized 11-core state; resting cores may update consensus asynchronously.",
            "synthesis_note",
        )
        return {
            "reply": reply,
            "profile": profile,
            "model": model,
            "mode": "interface_live",
            "society_phase": runtime.get("phase"),
            "interface_always_available": True,
        }
