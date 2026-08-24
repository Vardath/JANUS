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
from .senses import Appraisal, SenseFrame, merge_appraisals
from .topology import (
    ARCHITECTURE,
    CORE_NAMES,
    FRONT_CORE,
    HEMISPHERE_ROLES,
    INTERFACE_CORE,
    MECHANICAL_FLOW,
    SPECIALIST_ROLES,
    metadata as topology_metadata,
)

SPECIALISTS = tuple(SPECIALIST_ROLES.keys())
HEMISPHERES = tuple(HEMISPHERE_ROLES.keys())
LEGACY_FRONT_NAME = "consensus"


def _clip(text: str, n: int = 2400) -> str:
    return " ".join((text or "").split())[:n]


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", (text or "").lower())
    stop = {"the","and","that","this","with","from","have","what","when","where","your","you","for","are","was","were","can","could","would","should","into","about","please","janus"}
    out: list[str] = []
    for word in words:
        if word not in stop and word not in out:
            out.append(word)
    return out[:20]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(term in low for term in terms)


def _sense_appraisal(frame: SenseFrame, memories: list[dict[str, Any]], evidence: str, web_text: str) -> Appraisal:
    text = frame.content.lower()
    risk_terms = ("danger", "unsafe", "leak", "breach", "harm", "crash", "delete", "exposed", "security", "private", "urgent")
    opportunity_terms = ("improve", "build", "create", "idea", "possible", "opportunity", "explore", "design", "upgrade")
    negative_terms = ("bad", "wrong", "fail", "broken", "problem", "error", "harm", "risk", "hate", "dislike")
    positive_terms = ("good", "like", "love", "useful", "better", "success", "helpful", "excellent")
    conflict_terms = ("but", "however", "conflict", "contradict", "disagree", "versus", "instead")
    risk = 0.75 if _contains_any(text, risk_terms) else 0.2
    urgency = 0.75 if _contains_any(text, ("urgent", "immediately", "now", "critical", "breach", "crash")) else 0.2
    opportunity = 0.75 if _contains_any(text, opportunity_terms) else 0.35
    conflict = 0.7 if _contains_any(text, conflict_terms) else 0.25
    positive = sum(1 for t in positive_terms if t in text)
    negative = sum(1 for t in negative_terms if t in text)
    valence = max(-1.0, min(1.0, 0.25 * (positive - negative)))
    familiarity = min(1.0, 0.25 + 0.12 * min(5, len(memories)))
    confidence = 0.45 + (0.18 if evidence else 0.0) + (0.12 if web_text else 0.0)
    uncertainty = max(0.1, 0.65 - (0.18 if evidence else 0.0) - (0.12 if web_text else 0.0))
    novelty = max(frame.novelty, 0.7 if not memories else 0.4)
    return Appraisal(
        confidence=confidence,
        valence=valence,
        salience=frame.salience,
        uncertainty=uncertainty,
        novelty=novelty,
        urgency=urgency,
        familiarity=familiarity,
        risk=risk,
        opportunity=opportunity,
        conflict=conflict,
    )


@dataclass
class CoreState:
    name: str
    cycle_count: int = 0
    last_public_summary: str = ""
    last_active_at: int = 0
    inbox: deque = field(default_factory=lambda: deque(maxlen=80))
    appraisal: Appraisal = field(default_factory=Appraisal)


class JanusMind:
    """Server-side JANUS 1-3-7 society with account-private persistent state.

    Every sensed event is projected through all seven original subconscious cores.
    Both hemispheres receive all seven projections and transform them with complementary
    biases. Front performs affect-like appraisal/intention formation, then Interface
    selects expression/action. Action results and peer feedback re-enter as new sensing;
    Interface output is never recursively injected straight back into Front.
    Deterministic wake/sleep cycles make zero external model/API calls.
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
                raw_name = str(row.get("core_name") or "")
                name = FRONT_CORE if raw_name == LEGACY_FRONT_NAME else raw_name
                if name not in states:
                    continue
                states[name].cycle_count = max(states[name].cycle_count, int(row.get("cycle_count") or 0))
                summary = str(row.get("last_public_summary") or "")[:4000]
                if summary:
                    states[name].last_public_summary = summary
                states[name].last_active_at = max(states[name].last_active_at, int(row.get("last_active_at") or 0))

    def export_profile(self, account_id: int) -> list[dict[str, Any]]:
        states = self._states(account_id)
        with self._lock:
            rows = [
                {
                    "core_name": name,
                    "cycle_count": state.cycle_count,
                    "last_public_summary": state.last_public_summary,
                    "last_active_at": state.last_active_at,
                }
                for name, state in states.items()
            ]
            # Temporary compatibility row for older storage/readers.
            front = states[FRONT_CORE]
            rows.append({
                "core_name": LEGACY_FRONT_NAME,
                "cycle_count": front.cycle_count,
                "last_public_summary": front.last_public_summary,
                "last_active_at": front.last_active_at,
            })
            return rows

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
                for core in self._states(aid).values():
                    core.cycle_count += 1
        # No external model calls here. Curiosity/research is separately governed.

    def _specialist(self, name: str, frame: SenseFrame, memories: list[dict[str, Any]], evidence: str, web_text: str) -> dict[str, Any]:
        role = SPECIALIST_ROLES[name]
        text = _clip(frame.content, 6000)
        kws = _keywords(text)
        mem = [_clip(m.get("content", ""), 420) for m in memories[:5]]
        base_appraisal = _sense_appraisal(frame, memories, evidence, web_text)
        if name == "evidence":
            summary = f"Evidence sensed claims/support and calibrated confidence. Key terms: {', '.join(kws[:8]) or 'none'}."
            if evidence or web_text:
                summary += " External/file/web evidence is available and must be weighed rather than assumed true."
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "confidence": min(1.0, base_appraisal.confidence + 0.08)})
        elif name == "safety":
            summary = "Safety sensed welfare/valence, user goals, privacy, boundaries, benefit/harm and reversibility; it may raise interrupt pressure without owning final judgment."
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "risk": max(base_appraisal.risk, 0.35)})
        elif name == "counterpoint":
            summary = "Counterpoint sensed consequential conflict, objections, contradictions, failure modes and why unresolved differences matter."
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "conflict": max(base_appraisal.conflict, 0.45)})
        elif name == "context":
            summary = "Context sensed framing, relationships, environment, analogy and larger configuration without turning pattern into fact."
            appraisal = base_appraisal
        elif name == "logic":
            summary = "Logic combined grounding with pattern to test causal structure, constraints, explanatory models and falsifiable implications."
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "confidence": min(1.0, base_appraisal.confidence + 0.04)})
        elif name == "novelty":
            summary = f"Novelty sensed useful possibilities, alternative paths and testable adjacent ideas around {', '.join(kws[:6]) or 'the request'}."
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "novelty": max(base_appraisal.novelty, 0.65), "opportunity": max(base_appraisal.opportunity, 0.5)})
        else:
            summary = "Memory sensed continuity and learned appraisal from retained history: " + (" | ".join(mem) if mem else "no strong stored match this turn")
            appraisal = Appraisal(**{**base_appraisal.as_dict(), "familiarity": max(base_appraisal.familiarity, 0.55 if mem else 0.25)})
        return {
            "core": name,
            "fano_direction": role.direction,
            "axes": list(role.axes),
            "meaning": role.meaning,
            "summary": _clip(summary),
            "keywords": kws[:10],
            "appraisal": appraisal,
            "sense": frame,
        }

    def _hemisphere(self, account_id: int, name: str, specialists: dict[str, dict[str, Any]]) -> dict[str, Any]:
        governance.ensure_account(account_id)
        rows = governance.bridge_authority(account_id)
        weights = {(x["specialist"], x["hemisphere"]): float(x["weight"]) for x in rows}
        role = HEMISPHERE_ROLES[name]
        ranked = sorted(
            ((weights.get((core, name), 0.5), core, specialists[core]["summary"]) for core in SPECIALISTS),
            key=lambda x: x[0], reverse=True,
        )
        prefix = (
            "Left constrained the complete seven-core field into explicit sequential causal/consistency structure. "
            if name == "left_hemisphere" else
            "Right expanded the complete seven-core field through contextual, relational, gestalt and imaginative alternatives. "
        )
        parts = [f"{core} authority={weight:.2f}: {summary}" for weight, core, summary in ranked]
        appraisal = merge_appraisals(*(specialists[core]["appraisal"] for core in SPECIALISTS))
        return {
            "core": name,
            "role": role["meaning"],
            "summary": _clip(prefix + " ".join(parts), 5600),
            "weights": {core: weight for weight, core, _ in ranked},
            "appraisal": appraisal,
        }

    def _front(self, left: dict[str, Any], right: dict[str, Any], message: str) -> dict[str, Any]:
        appraisal = merge_appraisals(left["appraisal"], right["appraisal"])
        posture = appraisal.action_posture()
        summary = _clip(
            "Front/Bridge felt out the two hemisphere interpretations as computational appraisal, preserved disagreement, and formed an intention. "
            f"Posture={posture}; confidence={appraisal.confidence:.2f}; valence={appraisal.valence:.2f}; salience={appraisal.salience:.2f}; "
            f"uncertainty={appraisal.uncertainty:.2f}; urgency={appraisal.urgency:.2f}; risk={appraisal.risk:.2f}; opportunity={appraisal.opportunity:.2f}; "
            f"conflict={appraisal.conflict:.2f}. Left: {left['summary']} Right: {right['summary']}",
            7600,
        )
        return {"core": FRONT_CORE, "summary": summary, "intent": _clip(message, 1200), "appraisal": appraisal, "posture": posture}

    def _model_reply(self, account_id: int, message: str, front: dict[str, Any], memories: list[dict[str, Any]], evidence: str, web_context: str, selected_model: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return "JANUS completed the 1-3-7 integration, but the external language model is not configured on the server."
        if not governance.permit(account_id, "foreground_model", 0.001):
            return "JANUS completed the 11-core integration, but the configured foreground model-call budget has been reached for today."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            memory_text = "\n".join(f"- {m.get('content','')[:700]}" for m in memories[:8])
            app = front["appraisal"]
            prompt = (
                identity.prompt_fragment(account_id) + "\n\n"
                "You are the Interface core of JANUS. Give a natural direct answer, not a report about architecture unless asked. "
                "Use the Front state as the primary integrated basis. Feel out how the response should meet the user: preserve uncertainty when needed, "
                "warn when risk is material, explore when opportunity is high, and do not invent actions or capabilities. Do not expose private chain-of-thought.\n\n"
                f"USER MESSAGE:\n{message}\n\nFRONT/BRIDGE SUMMARY:\n{front['summary']}\n\n"
                f"INTERFACE POSTURE:\n{front['posture']}\n"
                f"APPRAISAL:\n{json.dumps(app.as_dict(), sort_keys=True)}\n\n"
                f"RELEVANT DURABLE MEMORY:\n{memory_text or '(none)'}\n\n"
                f"ATTACHMENT/EXTERNAL EVIDENCE:\n{evidence or '(none)'}\n\n"
                f"LIVE RESEARCH CONTEXT:\n{web_context or '(none)'}"
            )
            result = client.responses.create(model=selected_model, input=prompt)
            text = getattr(result, "output_text", "") or ""
            return text.strip() or "JANUS completed integration but produced no interface text."
        except Exception as exc:
            return f"JANUS completed the 11-core integration, but the interface model call failed this turn ({type(exc).__name__})."

    def web_research(self, query: str, account_id: int | None = None, governed: bool = True) -> tuple[str, list[dict[str, str]]]:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or os.getenv("JANUS_FOREGROUND_WEB", "1") != "1":
            return "", []
        if account_id is not None and governed and not governance.permit(account_id, "foreground_web", 0.002):
            return "", []
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = os.getenv("JANUS_CORE_FOREGROUND_MODEL", os.getenv("JANUS_MODEL_LUNA", "gpt-5.6-luna"))
            result = client.responses.create(
                model=model,
                tools=[{"type": "web_search_preview"}],
                input="Research this request using current web sources. Return a concise factual synthesis with source URLs where available:\n" + query,
            )
            text = (getattr(result, "output_text", "") or "").strip()
            urls: list[dict[str, str]] = []
            for match in re.finditer(r"https?://[^\s)\]]+", text):
                url = match.group(0).rstrip(".,;")
                if url not in [x["url"] for x in urls]:
                    urls.append({"title": "Retrieved source", "url": url})
            return text, urls[:12]
        except Exception:
            return "", []

    @staticmethod
    def wants_web(message: str) -> bool:
        text = (message or "").lower()
        return any(t in text for t in ("current", "today", "latest", "recent", "web", "internet", "search", "look up", "youtube", "weather", "news", "website", "online"))

    def process(self, account_id: int, message: str, evidence: str = "") -> dict[str, Any]:
        governance.ensure_account(account_id)
        identity.ensure(account_id)
        self._states(account_id)
        memories = storage.relevant_memories(account_id, message, 12)
        web_text, sources = self.web_research(message, account_id) if self.wants_web(message) else ("", [])
        frame = SenseFrame(
            modality="text",
            source="user",
            content=_clip(message, 6000),
            salience=0.85,
            uncertainty=0.45,
            novelty=0.65 if not memories else 0.4,
            metadata={"has_attachment_evidence": bool(evidence), "has_web_context": bool(web_text)},
        )
        specialist_outputs: dict[str, dict[str, Any]] = {}
        for name in SPECIALISTS:
            out = self._specialist(name, frame, memories, evidence, web_text)
            specialist_outputs[name] = out
            self._record_core(account_id, name, "sensory_projection", out["summary"], "foreground", out["appraisal"])
        left = self._hemisphere(account_id, "left_hemisphere", specialist_outputs)
        right = self._hemisphere(account_id, "right_hemisphere", specialist_outputs)
        self._record_core(account_id, "left_hemisphere", "integration", left["summary"], "foreground", left["appraisal"])
        self._record_core(account_id, "right_hemisphere", "integration", right["summary"], "foreground", right["appraisal"])
        front = self._front(left, right, message)
        self._record_core(account_id, FRONT_CORE, "appraisal_intention", front["summary"], "foreground", front["appraisal"])
        preflight = model_policy.escalation_score(message, evidence=bool(evidence), web=bool(web_text), memory_count=len(memories))
        selected_model = model_policy.choose_model(float(preflight["score"]))
        storage.add_event(account_id, FRONT_CORE, "model_escalation", f"Model tier selected {selected_model}; escalation score {preflight['score']}", f"Model tier {selected_model}; escalation {preflight['score']}", "foreground")
        reply = self._model_reply(account_id, message, front, memories, evidence, web_text, selected_model)
        interface_appraisal = front["appraisal"]
        self._record_core(account_id, INTERFACE_CORE, "response", _clip(reply, 2000), "foreground", interface_appraisal)
        storage.add_memory(account_id, f"User: {message}\nJANUS: {reply}", "working", "conversation", 0.55)
        consistent = "failed this turn" not in reply.lower() and "budget has been reached" not in reply.lower()
        governance.record_consistency(account_id, list(CORE_NAMES), consistent)
        if evidence or web_text:
            governance.adapt_bridge(account_id, "evidence", "left_hemisphere", 0.004 if consistent else -0.004)
        if memories:
            governance.adapt_bridge(account_id, "memory", "right_hemisphere", 0.003 if consistent else -0.003)
        return {
            "reply": reply,
            "sources": sources,
            "architecture": ARCHITECTURE,
            "mechanical_flow": MECHANICAL_FLOW,
            "route_trace": [*SPECIALISTS, *HEMISPHERES, FRONT_CORE, INTERFACE_CORE],
            "web": bool(web_text),
            "retrieved": bool(web_text),
            "bridge_authority": {"left": left["weights"], "right": right["weights"]},
            "front": {"posture": front["posture"], "appraisal": front["appraisal"].as_dict()},
            "model_policy": {"selected_model": selected_model, "preflight": preflight},
        }

    def _record_core(self, account_id: int, core: str, event_type: str, public_summary: str, mode: str, appraisal: Appraisal | None = None):
        ts = int(time.time())
        states = self._states(account_id)
        with self._lock:
            state = states[core]
            state.last_public_summary = public_summary[:4000]
            state.last_active_at = ts
            state.cycle_count += 1
            if appraisal is not None:
                state.appraisal = appraisal
        storage.add_event(account_id, core, event_type, public_summary, public_summary, mode)

    def ingest_device(self, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        governance.ensure_account(account_id)
        self._states(account_id)
        device_id = str(payload.get("device_id") or payload.get("installation_id") or "android-unknown")[:120]
        phase = str(payload.get("phase") or "unknown")[:40]
        version = str(payload.get("client_version") or payload.get("version") or "")[:80]
        local_front = _clip(str(payload.get("front") or payload.get("consensus") or ""), 1200)
        safe_state = {
            "phase": phase,
            "cycle_count": payload.get("cycle_count") or payload.get("cycles"),
            "front": local_front,
            "consensus": local_front,
            "interface": _clip(str(payload.get("interface") or ""), 1200),
            "core_summaries": payload.get("core_summaries") or payload.get("cores") or {},
            "local_memories": (payload.get("local_memories") or [])[-20:],
            "front_appraisal": payload.get("front_appraisal") or payload.get("appraisal") or {},
        }
        with storage.db() as c:
            c.execute(
                "INSERT INTO v2_device_presence(account_id,device_id,client_version,phase,state_json,last_seen_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(account_id,device_id) DO UPDATE SET client_version=excluded.client_version,phase=excluded.phase,state_json=excluded.state_json,last_seen_at=excluded.last_seen_at",
                (int(account_id), device_id, version, phase, json.dumps(safe_state, ensure_ascii=False), int(time.time())),
            )
        feedback = _clip((safe_state["front"] + " " + safe_state["interface"]).strip(), 1600)
        if feedback:
            peer_frame = SenseFrame(modality="peer", source=f"local:{device_id}", content=feedback, salience=0.6, uncertainty=0.5, novelty=0.4)
            # Every one of the seven receives the peer event. This is a sensory event,
            # never a direct local-Front -> global-Front injection.
            for specialist in SPECIALISTS:
                role = SPECIALIST_ROLES[specialist]
                detail = f"Peer sense for {specialist} d{role.direction} ({role.meaning}): {_clip(peer_frame.content, 900)}"
                storage.add_event(account_id, specialist, "peer_sense", detail, detail, "sync")
        for ev in (payload.get("observe_events") or [])[-12:]:
            if isinstance(ev, dict):
                detail = _clip(str(ev.get("detail") or ev.get("summary") or ""), 800)
                if detail:
                    for specialist in SPECIALISTS:
                        storage.add_event(account_id, specialist, "peer_observation", detail, detail, "sync")
        return {
            "ok": True,
            "server_phase": self.phase,
            "architecture": ARCHITECTURE,
            "mechanical_flow": MECHANICAL_FLOW,
            "guidance": {
                "sync_policy": "selective-no-overwrite",
                "memory_policy": "local-and-global-remain-distinct",
                "peer_policy": "peer-state-reenters-through-all-seven-senses",
                "background_external_api": False,
            },
        }

    def status(self, account_id: int | None = None) -> dict[str, Any]:
        base = {
            "architecture": ARCHITECTURE,
            "mechanical_flow": MECHANICAL_FLOW,
            "conceptual_topology": "1|3|7",
            "core_count": 11,
            "specialist_count": 7,
            "hemisphere_count": 2,
            "front_core": FRONT_CORE,
            "interface_core": INTERFACE_CORE,
            "phase": self.phase,
            "interface_available": True,
            "persistent_storage": True,
            "background_external_api_budget_used": self.background_external_api_calls,
            "background_cycle_model_calls": 0,
            "started_at": self.started_at,
            "last_cycle_at": self.last_cycle_at,
        }
        if account_id is None:
            with self._lock:
                base["active_private_profiles"] = len(self._profiles)
            base["cores"] = {name: {"name": name, "summary": "private-per-account", "topology": topology_metadata(name)} for name in CORE_NAMES}
            base.update({"remote_clients": 0, "registered_clients": 0, "clients": [], "bridge_authority": [], "core_reliability": []})
            return base
        aid = int(account_id)
        governance.ensure_account(aid)
        identity.ensure(aid)
        states = self._states(aid)
        with self._lock:
            base["cores"] = {
                name: {
                    "name": name,
                    "cycle_count": state.cycle_count,
                    "last_active_at": state.last_active_at,
                    "summary": state.last_public_summary,
                    "topology": topology_metadata(name),
                    "appraisal": state.appraisal.as_dict() if name in (FRONT_CORE, INTERFACE_CORE) else None,
                }
                for name, state in states.items()
            }
            # Temporary read alias only; Front remains canonical.
            base["cores"][LEGACY_FRONT_NAME] = {**base["cores"][FRONT_CORE], "name": LEGACY_FRONT_NAME, "alias_for": FRONT_CORE}
        remote = storage.rows("SELECT device_id,client_version,phase,last_seen_at FROM v2_device_presence WHERE account_id=? ORDER BY last_seen_at DESC LIMIT 20", (aid,))
        online = [x for x in remote if int(time.time()) - int(x["last_seen_at"]) < 180]
        base.update({
            "remote_clients": len(online),
            "registered_clients": len(remote),
            "clients": remote,
            "bridge_authority": governance.bridge_authority(aid),
            "core_reliability": governance.reliability(aid),
        })
        return base


mind = JanusMind()
