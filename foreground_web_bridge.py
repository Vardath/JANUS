"""Hard-coded foreground live-web bridge for JANUS.

This module makes explicit user web/search/YouTube requests exercise the OpenAI
Responses web_search tool directly.  It is intentionally installed at runtime
rather than through a build-time patch so the capability cannot disappear when
older server sources are reconstructed.
"""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from src.janus_sleep_cycle import janus_sleep_cycle


def _source_rows(response: Any) -> list[dict[str, str]]:
    """Collect source URLs from both citations and web_search_call actions."""
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


def _models(curiosity_module) -> list[str]:
    configured = [
        os.environ.get("JANUS_CORE_FOREGROUND_MODEL", ""),
        os.environ.get("JANUS_MODEL", ""),
        getattr(curiosity_module, "FOREGROUND_MODEL", ""),
    ]
    # Known API model fallbacks. Duplicate entries are removed while preserving order.
    configured += ["gpt-5", "gpt-5-mini"]
    out: list[str] = []
    for m in configured:
        m = str(m or "").strip()
        if m and m not in out:
            out.append(m)
    return out


def install(app, curiosity_module):
    if getattr(curiosity_module, "_janus_forced_foreground_web_installed", False):
        return

    original = curiosity_module.foreground_deliberate

    def forced_foreground(profile: str, message: str):
        if not curiosity_module._needs_web(message):
            return original(profile, message)

        profile = str(profile or "local-user")
        query = str(message or "").strip()
        if not query:
            return {"ok": False, "reason": "empty", "web_attempted": False}
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            note = "Live web research was requested, but the server has no OPENAI_API_KEY configured."
            try:
                curiosity_module._route_core_note(profile, "evidence", note, "foreground_web_error")
            except Exception:
                pass
            return {"ok": False, "model": False, "web": False, "web_attempted": True, "error": "missing_api_key"}

        prompt = (
            "Perform the user's requested LIVE WEB RESEARCH now. You must use web search, not memory or runtime telemetry. "
            "Return a concise factual research note containing the actual retrieved result. Include source names and URLs in the text when available. "
            "For YouTube/channel requests, search the public web for the named channel/video and report only metadata, pages, captions, transcripts or indexed material actually found; never invent transcript text. "
            "For current weather/news/current facts, report the current retrieved value and its source.\n\n"
            "USER REQUEST:\n" + query
        )

        errors: list[str] = []
        for model in _models(curiosity_module):
            try:
                response = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")).responses.create(
                    model=model,
                    tools=[{"type": "web_search"}],
                    tool_choice="required",
                    input=prompt,
                    max_output_tokens=1800,
                )
                text = str(getattr(response, "output_text", "") or "").strip()
                sources = _source_rows(response)
                if not text:
                    raise RuntimeError("empty_web_result")

                source_text = ""
                if sources:
                    source_text = "\nSources: " + "; ".join(
                        f"{s['title']} — {s['url']}" for s in sources[:8]
                    )
                evidence = (text + source_text).strip()

                # Put the retrieved material into the actual 7->2->1->1 fabric.
                for core in getattr(curiosity_module, "SPECIALISTS", ("evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty")):
                    try:
                        janus_sleep_cycle.send(
                            "interface",
                            core,
                            f"LIVE WEB EVIDENCE FOR USER REQUEST: {query}\nRETRIEVED: {evidence[:5200]}",
                            "foreground_web_evidence",
                        )
                    except Exception:
                        pass
                try:
                    curiosity_module._route_core_note(profile, "evidence", evidence, "foreground_web")
                    curiosity_module._event(profile, "core_foreground_sources", json.dumps(sources, ensure_ascii=False))
                    curiosity_module._event(profile, "forced_foreground_web_success", json.dumps({"model": model, "query": query[:1200], "sources": sources[:8]}, ensure_ascii=False))
                    janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
                except Exception:
                    pass

                return {
                    "ok": True,
                    "model": True,
                    "web": True,
                    "web_attempted": True,
                    "retrieved": True,
                    "actual_model": model,
                    "result": text[:7000],
                    "sources": sources,
                }
            except Exception as exc:
                errors.append(f"{model}:{type(exc).__name__}:{exc}")

        error_text = " | ".join(errors)[-5000:]
        note = (
            "Live web research was actually attempted for this turn but the provider call failed. "
            "This is a provider/model/tool failure, not evidence that JANUS lacks a web tool. "
            f"Diagnostic: {error_text}"
        )
        try:
            curiosity_module._route_core_note(profile, "evidence", note, "foreground_web_error")
            curiosity_module._event(profile, "forced_foreground_web_error", note)
            janus_sleep_cycle.service_work_burst(include_interface=True, only_if_pending=True)
        except Exception:
            pass
        return {
            "ok": False,
            "model": False,
            "web": False,
            "web_attempted": True,
            "retrieved": False,
            "error": error_text or "web_search_failed",
        }

    curiosity_module.foreground_deliberate = forced_foreground
    curiosity_module._janus_forced_foreground_web_installed = True
    app.state.janus_forced_foreground_web = True

    @app.get("/capabilities/research-live-test")
    def research_live_test(q: str = "current UTC date"):
        result = forced_foreground("__research_test__", q)
        return {
            "requested": q,
            "web_attempted": bool(result.get("web_attempted")),
            "web": bool(result.get("web")),
            "retrieved": bool(result.get("retrieved")),
            "actual_model": result.get("actual_model"),
            "result": result.get("result", "")[:2500],
            "sources": result.get("sources", [])[:6],
            "error": result.get("error"),
        }

    return app
