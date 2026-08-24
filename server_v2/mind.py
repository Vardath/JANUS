from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from . import governance, identity, model_policy, storage

SPECIALISTS = ("evidence", "logic", "counterpoint", "context", "memory", "safety", "novelty")
HEMISPHERES = ("left_hemisphere", "right_hemisphere")
CORE_NAMES = (*SPECIALISTS, *HEMISPHERES, "consensus", "interface")
ARCHITECTURE = "11-core: 7 specialists -> 2 hemispheres -> consensus -> interface"


def _clip(text: str, n: int = 2400) -> str:
    return " ".join((text or "").split())[:n]


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", (text or "").lower())
    stop = {"the","and","that","this","with","from","have","what","when","where","your","you","for","are","was","were","can","could","would","should","into","about","please","janus"}
    out = []
    for w in words:
        if w not in stop and w not in out:
            out.append(w)
    return out[:16]


@dataclass
class CoreState:
    name: str
    cycle_count: int = 0
    last_public_summary: str = ""
    last_active_at: int = 0
    inbox: deque = field(default_factory=lambda: deque(maxlen=80))


class JanusMind:
    """Fresh server-side 11-core JANUS runtime with account-private state.

    The server hosts one architecture, but each account has its own private state
    for all eleven cores. Seven specialists feed only the two hemisphere
    integrators; hemispheres feed only Consensus; Consensus feeds only Interface.
    Device/global feedback is feedback-only and must re-enter through specialist
    review. Deterministic wake/sleep cycles use no external model calls.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._profiles: dict[int, dict[str, CoreState]] = {}
        self.started_at = int(time.time())
        self.phase = "wake"
        self._running = False
        self._thread: threading.Thread | None = None
        self.wake_seconds = max(30, int(os.getenv("JANUS_WAKE_SECONDS", "300")))
        self.sleep_seconds = max(30, int(os.getenv("JANUS_SLEEP_SECONDS", "600")))
        self.background_external_api_calls = 0
        self.last_cycle_at = 0

    def _states(self, account_id: int) -> dict[str, CoreState]:
        aid = int(account_id)
        with self._lock:
            states = self._profiles.get(aid)
            if states is None:
                states = {name: CoreState(name) for name in CORE_NAMES}
                self._profiles[aid] = states
            return states

    def restore_profile(self, account_id: int, core_rows: list[dict[str, Any]]) -> None:
        states = self._states(account_id)
        with self._lock:
            for row in core_rows:
                name = str(row.get("core_name") or "")
                if name not in states:
                    continue
                states[name].cycle_count = int(row.get("cycle_count") or 0)
                states[name].last_public_summary = str(row.get("last_public_summary") or "")[:4000]
                states[name].last_active_at = int(row.get("last_active_at") or 0)

    def export_profile(self, account_id: int) -> list[dict[str, Any]]:
        states = self._states(account_id)
        with self._lock:
            return [
                {"core_name":name,"cycle_count":state.cycle_count,"last_public_summary":state.last_public_summary,"last_active_at":state.last_active_at}
                for name,state in states.items()
            ]

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, name="janus-v2-mind", daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            self.phase = "wake"
            deadline = time.time() + self.wake_seconds
            while self._running and time.time() < deadline:
                self._background_tick()
                time.sleep(min(30, max(2, deadline - time.time())))
            self.phase = "sleep"
            deadline = time.time() + self.sleep_seconds
            while self._running and time.time() < deadline:
                time.sleep(min(30, max(2, deadline - time.time())))

    def _background_tick(self):
        self.last_cycle_at = int(time.time())
        active_ids = [int(x["id"]) for x in storage.rows("SELECT id FROM v2_accounts")]
        with self._lock:
            for aid in active_ids:
                states = self._states(aid)
                for core in states.values():
                    core.cycle_count += 1
        # No external model calls here. Curiosity/research is separately governed.

    def _specialist(self, name: str, message: str, memories: list[dict[str, Any]], evidence: str) -> dict[str, Any]:
        text = _clip(message, 6000)
        kws = _keywords(text)
        mem = [_clip(m.get("content", ""), 420) for m in memories[:5]]
        if name == "evidence":
            summary = f"Evidence focus: identify factual claims and source needs. Key terms: {', '.join(kws[:8]) or 'none'}."
            if evidence: summary += " External/file evidence is available and must be weighed explicitly."
        elif name == "logic":
            summary = "Logic focus: preserve constraints, dependencies and internal consistency; distinguish requests, premises and conclusions."
        elif name == "counterpoint":
            summary = "Counterpoint focus: test alternative explanations, likely failure modes and assumptions before accepting the first interpretation."
        elif name == "context":
            summary = "Context focus: interpret the request in active conversation/project context without inventing missing facts."
        elif name == "memory":
            summary = "Memory focus: relevant durable context: " + (" | ".join(mem) if mem else "no strong stored match this turn")
        elif name == "safety":
            summary = "Safety focus: preserve user control, privacy, account boundaries and operational safeguards; do not fabricate actions or hidden access."
        else:
            summary = f"Novelty focus: look for useful non-obvious connections or missing opportunities around {', '.join(kws[:6]) or 'the request'}."
        return {"core": name, "summary": _clip(summary), "keywords": kws[:10]}

    def _hemisphere(self, account_id: int, name: str, specialists: dict[str, dict[str, Any]]) -> dict[str, Any]:
        governance.ensure_account(account_id)
        rows = governance.bridge_authority(account_id)
        weights = {(x["specialist"], x["hemisphere"]): float(x["weight"]) for x in rows}
        role = "analytic/integrity" if name == "left_hemisphere" else "contextual/creative"
        ranked = sorted(((weights.get((k,name),0.5),k,specialists[k]["summary"]) for k in SPECIALISTS), key=lambda x:x[0], reverse=True)
        parts = [f"{k} authority={w:.2f}: {summary}" for w,k,summary in ranked]
        return {"core":name,"role":role,"summary":_clip(" ".join(parts),5200),"weights":{k:w for w,k,_ in ranked}}

    def _consensus(self, left: dict[str, Any], right: dict[str, Any], message: str) -> dict[str, Any]:
        return {
            "core":"consensus",
            "summary":_clip(
                "Integrate both hemispheres without allowing either to become absolute. Bridge authority is bounded between 0.2 and 0.8. "
                "Answer the user's actual request, preserve uncertainty, and prefer concrete useful action. " + left["summary"] + " " + right["summary"],
                7000,
            ),
            "intent":_clip(message,1200),
        }

    def _model_reply(self, account_id: int, message: str, consensus: dict[str, Any], memories: list[dict[str, Any]], evidence: str, web_context: str, selected_model: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return "JANUS's server mind completed the 7 → 2 → 1 → 1 integration, but the external language model is not configured on the server."
        if not governance.permit(account_id,"foreground_model",0.001):
            return "JANUS completed the local 11-core integration, but the configured foreground model-call budget has been reached for today."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            memory_text = "\n".join(f"- {m.get('content','')[:700]}" for m in memories[:8])
            prompt = (
                identity.prompt_fragment(account_id) + "\n\n"
                "You are the Interface core. Give a natural direct answer, not a report about the architecture unless asked. "
                "Do not expose private chain-of-thought; use only supplied externalizable summaries.\n\n"
                f"USER MESSAGE:\n{message}\n\nCONSENSUS SUMMARY:\n{consensus['summary']}\n\n"
                f"RELEVANT DURABLE MEMORY:\n{memory_text or '(none)'}\n\n"
                f"ATTACHMENT/EXTERNAL EVIDENCE:\n{evidence or '(none)'}\n\n"
                f"LIVE RESEARCH CONTEXT:\n{web_context or '(none)'}"
            )
            result = client.responses.create(model=selected_model,input=prompt)
            text = getattr(result,"output_text","") or ""
            return text.strip() or "JANUS completed integration but produced no interface text."
        except Exception as exc:
            return f"JANUS completed the 11-core integration, but the interface model call failed this turn ({type(exc).__name__})."

    def web_research(self, query: str, account_id: int | None = None, governed: bool = True) -> tuple[str, list[dict[str,str]]]:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or os.getenv("JANUS_FOREGROUND_WEB","1") != "1":
            return "",[]
        if account_id is not None and governed and not governance.permit(account_id,"foreground_web",0.002):
            return "",[]
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.getenv("JANUS_CORE_FOREGROUND_MODEL",os.getenv("JANUS_MODEL_LUNA","gpt-5.6-luna"))
            result = client.responses.create(
                model=model,
                tools=[{"type":"web_search_preview"}],
                input="Research this request using current web sources. Return a concise factual synthesis with source URLs where available:\n" + query,
            )
            text = (getattr(result,"output_text","") or "").strip()
            urls: list[dict[str,str]] = []
            for match in re.finditer(r"https?://[^\s)\]]+",text):
                url = match.group(0).rstrip(".,;")
                if url not in [x["url"] for x in urls]: urls.append({"title":"Retrieved source","url":url})
            return text,urls[:12]
        except Exception:
            return "",[]

    @staticmethod
    def wants_web(message: str) -> bool:
        text = (message or "").lower()
        return any(t in text for t in ("current","today","latest","recent","web","internet","search","look up","youtube","weather","news","website","online"))

    def process(self, account_id: int, message: str, evidence: str = "") -> dict[str, Any]:
        governance.ensure_account(account_id)
        identity.ensure(account_id)
        self._states(account_id)
        memories = storage.relevant_memories(account_id,message,12)
        web_text,sources = self.web_research(message,account_id) if self.wants_web(message) else ("",[])
        specialist_outputs: dict[str,dict[str,Any]] = {}
        for name in SPECIALISTS:
            out = self._specialist(name,message,memories,evidence or web_text)
            specialist_outputs[name] = out
            self._record_core(account_id,name,"assessment",out["summary"],"foreground")
        left = self._hemisphere(account_id,"left_hemisphere",specialist_outputs)
        right = self._hemisphere(account_id,"right_hemisphere",specialist_outputs)
        self._record_core(account_id,"left_hemisphere","integration",left["summary"],"foreground")
        self._record_core(account_id,"right_hemisphere","integration",right["summary"],"foreground")
        consensus = self._consensus(left,right,message)
        self._record_core(account_id,"consensus","consensus",consensus["summary"],"foreground")
        preflight = model_policy.escalation_score(message,evidence=bool(evidence),web=bool(web_text),memory_count=len(memories))
        selected_model = model_policy.choose_model(float(preflight["score"]))
        storage.add_event(account_id,"consensus","model_escalation",f"Model tier selected {selected_model}; escalation score {preflight['score']}",f"Model tier {selected_model}; escalation {preflight['score']}","foreground")
        reply = self._model_reply(account_id,message,consensus,memories,evidence,web_text,selected_model)
        self._record_core(account_id,"interface","response",_clip(reply,2000),"foreground")
        storage.add_memory(account_id,f"User: {message}\nJANUS: {reply}","working","conversation",0.55)
        consistent = "failed this turn" not in reply.lower() and "budget has been reached" not in reply.lower()
        governance.record_consistency(account_id,list(CORE_NAMES),consistent)
        if evidence or web_text: governance.adapt_bridge(account_id,"evidence","left_hemisphere",0.004 if consistent else -0.004)
        if memories: governance.adapt_bridge(account_id,"memory","right_hemisphere",0.003 if consistent else -0.003)
        return {
            "reply":reply,"sources":sources,"architecture":"7->2->1->1","route_trace":list(CORE_NAMES),
            "web":bool(web_text),"retrieved":bool(web_text),"bridge_authority":{"left":left["weights"],"right":right["weights"]},
            "model_policy":{"selected_model":selected_model,"preflight":preflight},
        }

    def _record_core(self, account_id: int, core: str, event_type: str, public_summary: str, mode: str):
        ts = int(time.time())
        states = self._states(account_id)
        with self._lock:
            state = states[core]
            state.last_public_summary = public_summary[:4000]
            state.last_active_at = ts
            state.cycle_count += 1
        storage.add_event(account_id,core,event_type,public_summary,public_summary,mode)

    def ingest_device(self, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        governance.ensure_account(account_id)
        self._states(account_id)
        device_id = str(payload.get("device_id") or payload.get("installation_id") or "android-unknown")[:120]
        phase = str(payload.get("phase") or "unknown")[:40]
        version = str(payload.get("client_version") or payload.get("version") or "")[:80]
        safe_state = {
            "phase":phase,
            "cycle_count":payload.get("cycle_count") or payload.get("cycles"),
            "consensus":_clip(str(payload.get("consensus") or ""),1200),
            "interface":_clip(str(payload.get("interface") or ""),1200),
            "core_summaries":payload.get("core_summaries") or payload.get("cores") or {},
            "local_memories":(payload.get("local_memories") or [])[-20:],
        }
        with storage.db() as c:
            c.execute(
                "INSERT INTO v2_device_presence(account_id,device_id,client_version,phase,state_json,last_seen_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(account_id,device_id) DO UPDATE SET client_version=excluded.client_version,phase=excluded.phase,state_json=excluded.state_json,last_seen_at=excluded.last_seen_at",
                (int(account_id),device_id,version,phase,json.dumps(safe_state,ensure_ascii=False),int(time.time())),
            )
        feedback = _clip((safe_state["consensus"] + " " + safe_state["interface"]).strip(),1600)
        if feedback:
            for specialist in ("evidence","context","counterpoint","memory"):
                storage.add_event(account_id,specialist,"device_feedback",f"Feedback-only local state for specialist review: {feedback}",f"Feedback-only local state: {feedback}","sync")
        for ev in (payload.get("observe_events") or [])[-12:]:
            if isinstance(ev,dict):
                detail = _clip(str(ev.get("detail") or ev.get("summary") or ""),800)
                if detail: storage.add_event(account_id,"context","device_feedback",detail,detail,"sync")
        return {
            "ok":True,"server_phase":self.phase,"architecture":"7->2->1->1",
            "guidance":{"sync_policy":"selective-no-overwrite","memory_policy":"local-and-global-remain-distinct","background_external_api":False},
        }

    def status(self, account_id: int | None = None) -> dict[str, Any]:
        base = {
            "architecture":ARCHITECTURE,"core_count":11,"specialist_count":7,"hemisphere_count":2,
            "phase":self.phase,"interface_available":True,"persistent_storage":True,
            "background_external_api_budget_used":self.background_external_api_calls,"background_cycle_model_calls":0,
            "started_at":self.started_at,"last_cycle_at":self.last_cycle_at,
        }
        if account_id is None:
            with self._lock: base["active_private_profiles"] = len(self._profiles)
            base["cores"] = {name:{"name":name,"summary":"private-per-account"} for name in CORE_NAMES}
            base.update({"remote_clients":0,"registered_clients":0,"clients":[],"bridge_authority":[],"core_reliability":[]})
            return base
        aid = int(account_id)
        governance.ensure_account(aid); identity.ensure(aid)
        states = self._states(aid)
        with self._lock:
            base["cores"] = {
                name:{"name":name,"cycle_count":state.cycle_count,"last_active_at":state.last_active_at,"summary":state.last_public_summary}
                for name,state in states.items()
            }
        remote = storage.rows("SELECT device_id,client_version,phase,last_seen_at FROM v2_device_presence WHERE account_id=? ORDER BY last_seen_at DESC LIMIT 20",(aid,))
        online = [x for x in remote if int(time.time()) - int(x["last_seen_at"]) < 180]
        base.update({
            "remote_clients":len(online),"registered_clients":len(remote),"clients":remote,
            "bridge_authority":governance.bridge_authority(aid),"core_reliability":governance.reliability(aid),
        })
        return base


mind = JanusMind()
