"""Hard-coded foreground live-web bridge for JANUS."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI
from src.janus_sleep_cycle import janus_sleep_cycle


def _source_rows(response: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: Any, title: Any = None) -> None:
        u = str(url or "").strip()
        if not u or u in seen:
            return
        seen.add(u)
        found.append({"title": str(title or "Source")[:300], "url": u[:1600]})

    try:
        for item in getattr(response, "output", []) or []:
            action = getattr(item, "action", None)
            for src in getattr(action, "sources", []) or []:
                if isinstance(src, dict):
                    add(src.get("url"), src.get("title"))
                else:
                    add(getattr(src, "url", None), getattr(src, "title", None))
            for part in getattr(item, "content", []) or []:
                for ann in getattr(part, "annotations", []) or []:
                    if isinstance(ann, dict):
                        add(ann.get("url"), ann.get("title"))
                    else:
                        add(getattr(ann, "url", None), getattr(ann, "title", None))
    except Exception:
        pass
    return found[:12]


def _output_text(response: Any) -> str:
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for part in getattr(item, "content", []) or []:
            value = getattr(part, "text", None)
            if value:
                chunks.append(str(value))
    return "\n".join(chunks).strip()


def _models(curiosity_module) -> list[str]:
    configured = [
        os.environ.get("JANUS_CORE_FOREGROUND_MODEL", ""),
        os.environ.get("JANUS_MODEL", ""),
        getattr(curiosity_module, "FOREGROUND_MODEL", ""),
        "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6",
    ]
    out: list[str] = []
    for m in configured:
        m = str(m or "").strip()
        if m and m not in out:
            out.append(m)
    return out


def _context_only_followup(message: str) -> bool:
    """Do not turn conversational bookkeeping into an unrelated web search."""
    m = " ".join(str(message or "").lower().split())
    if not m or "?" in m:
        return False
    explicit = ("search", "look up", "find", "browse", "check", "verify", "research", "source", "latest", "current", "today", "youtube")
    if any(k in m for k in explicit):
        return False
    contextual = (
        "those are to go along with", "that is to go along with", "these are to go along with",
        "add that to", "add those to", "keep that with", "keep those with", "remember that",
        "alongside the", "for the project", "for our research", "include that with",
    )
    return any(k in m for k in contextual)


def _youtube_request(message: str) -> bool:
    m = str(message or "").lower()
    return "youtube" in m or "youtu.be" in m or "youtube.com" in m or "channel" in m or "transcript" in m or "captions" in m


def install(app, curiosity_module):
    if getattr(curiosity_module, "_janus_forced_foreground_web_installed", False):
        return
    original = curiosity_module.foreground_deliberate

    def forced_foreground(profile: str, message: str):
        if _context_only_followup(message):
            return original(profile, message)
        if not curiosity_module._needs_web(message):
            return original(profile, message)

        profile = str(profile or "local-user")
        query = str(message or "").strip()
        if not query:
            return {"ok": False, "reason": "empty", "web_attempted": False}
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            return {"ok": False, "model": False, "web": False, "web_attempted": True, "error": "missing_api_key"}

        youtube = _youtube_request(query)
        if youtube:
            instruction = (
                "This is a YouTube/public-video research request. Search for the exact requested channel or video first. "
                "Prefer direct youtube.com channel/watch results when indexed. If direct YouTube results are unavailable, use reputable indexed mirrors/search results but label them as indirect. "
                "For a channel request, return a bounded set of at most 8 relevant videos, not an unbounded channel crawl. "
                "For a specific video, attempt to retrieve captions/transcript or an indexed transcript. Clearly distinguish transcript/caption text from title/description/snippet metadata. "
                "Never claim playback, transcript access, direct YouTube access, or channel enumeration unless the retrieved evidence demonstrates it. "
            )
        else:
            instruction = "For current weather/news/current facts, report the retrieved value and source. "
        prompt = (
            "Perform the user's requested LIVE WEB RESEARCH now. Use web search rather than memory or runtime telemetry. "
            "After searching, always produce a concise final answer containing the retrieved result. " + instruction +
            "Report only material actually found and preserve source provenance.\n\nUSER REQUEST:\n" + query
        )

        errors: list[str] = []
        for model in _models(curiosity_module):
            try:
                response = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")).responses.create(
                    model=model, tools=[{"type": "web_search"}], input=prompt, max_output_tokens=3000,
                )
                text = _output_text(response)
                sources = _source_rows(response)
                if not text:
                    status = str(getattr(response, "status", "") or "")
                    reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
                    raise RuntimeError(f"empty_web_result(status={status},reason={reason})")

                direct_youtube = [s for s in sources if re.search(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/", s.get("url", ""), re.I)]
                provenance = {
                    "query": query[:1200], "model": model, "youtube_request": youtube,
                    "direct_youtube_sources": len(direct_youtube), "source_count": len(sources), "sources": sources[:8],
                }
                source_text = ""
                if sources:
                    source_text = "\nSources: " + "; ".join(f"{s['title']} — {s['url']}" for s in sources[:8])
                evidence = (text + source_text).strip()

                # Feed identical retrieved evidence to all seven specialists, then let the
                # existing sleep-cycle fabric carry it through hemispheres -> consensus -> interface.
                for core in getattr(curiosity_module, "SPECIALISTS", ("evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty")):
                    try:
                        janus_sleep_cycle.send("interface", core, f"LIVE WEB EVIDENCE FOR USER REQUEST: {query}\nRETRIEVED: {evidence[:5200]}", "foreground_web_evidence")
                    except Exception:
                        pass
                try:
                    curiosity_module._route_core_note(profile, "evidence", evidence, "foreground_web")
                    curiosity_module._event(profile, "core_foreground_sources", json.dumps(sources, ensure_ascii=False))
                    curiosity_module._event(profile, "forced_foreground_web_success", json.dumps(provenance, ensure_ascii=False))
                    janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
                except Exception:
                    pass

                return {
                    "ok": True, "model": True, "web": True, "web_attempted": True, "retrieved": True,
                    "actual_model": model, "result": text[:7000], "sources": sources,
                    "youtube_request": youtube, "direct_youtube_sources": len(direct_youtube), "provenance": provenance,
                }
            except Exception as exc:
                errors.append(f"{model}:{type(exc).__name__}:{exc}")

        error_text = " | ".join(errors)[-5000:]
        note = "Live web research was attempted but the provider call failed. Diagnostic: " + error_text
        try:
            curiosity_module._route_core_note(profile, "evidence", note, "foreground_web_error")
            curiosity_module._event(profile, "forced_foreground_web_error", note)
        except Exception:
            pass
        return {"ok": False, "model": False, "web": False, "web_attempted": True, "retrieved": False, "error": error_text or "web_search_failed"}

    curiosity_module.foreground_deliberate = forced_foreground
    curiosity_module._janus_forced_foreground_web_installed = True
    app.state.janus_forced_foreground_web = True

    @app.get("/capabilities/research-live-test")
    def research_live_test(q: str = "current UTC date"):
        result = forced_foreground("__research_test__", q)
        return {"requested": q, "web_attempted": bool(result.get("web_attempted")), "web": bool(result.get("web")), "retrieved": bool(result.get("retrieved")), "actual_model": result.get("actual_model"), "result": result.get("result", "")[:2500], "sources": result.get("sources", [])[:6], "youtube_request": result.get("youtube_request", False), "direct_youtube_sources": result.get("direct_youtube_sources", 0), "error": result.get("error")}

    return app
