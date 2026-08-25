from __future__ import annotations

import json
import os
import re
from typing import Any

from . import governance, identity, model_policy, storage
from .mind import JanusMind, SPECIALISTS, HEMISPHERES
from .recursive_core import RecursiveCoreProcessor, RecursiveCoreState, apply_ai_counsel
from .senses import SenseFrame
from .topology import ARCHITECTURE, CORE_NAMES, FRONT_CORE, INTERFACE_CORE, MECHANICAL_FLOW, metadata as topology_metadata

LOCAL_START = "[LOCAL RECURSIVE JANUS CORE STATES]"
LOCAL_END = "[END LOCAL RECURSIVE JANUS CORE STATES]"


def _clip(text: str, n: int = 2400) -> str:
    return " ".join((text or "").split())[:n]


def _extract_local_states(message: str) -> tuple[str, dict[str, Any]]:
    raw = message or ""
    if LOCAL_START not in raw or LOCAL_END not in raw:
        return raw, {}
    before, tail = raw.split(LOCAL_START, 1)
    payload, after = tail.split(LOCAL_END, 1)
    try:
        parsed = json.loads(payload.strip())
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}
    return (before + after).strip(), parsed


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(raw[start:end+1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None
    return None


class RecursiveJanusMind(JanusMind):
    """JANUS society in which every top-level core is itself a full JANUS core.

    The outer 11-core topology remains organizational. Internally every core runs the
    same seven-position JANUS/Fano processor, then revises against peer states. During
    a foreground model turn one governed model call can return bounded AI counsel for
    all 11 global cores and any supplied 11 Android-local cores plus the final reply.
    This avoids 22 independent API calls while preserving distinct per-core responses.
    """

    def __init__(self):
        super().__init__()
        self._recursive: dict[int, dict[str, RecursiveCoreState]] = {}
        self._processor = RecursiveCoreProcessor()

    def _recursive_states(self, account_id: int) -> dict[str, RecursiveCoreState]:
        aid = int(account_id)
        states = self._recursive.get(aid)
        if states is None:
            states = {name: RecursiveCoreState(name) for name in CORE_NAMES}
            self._recursive[aid] = states
        return states

    def _purpose(self, name: str) -> str:
        try:
            return str(topology_metadata(name).get("purpose") or topology_metadata(name).get("meaning") or name)
        except Exception:
            return name

    def _run_recursive(
        self,
        account_id: int,
        core_name: str,
        content: str,
        appraisal,
        peers: list[tuple[str, str]] | None = None,
        ai_counsel: str = "",
    ) -> dict[str, Any]:
        states = self._recursive_states(account_id)
        return self._processor.think(
            states[core_name], content, appraisal, self._purpose(core_name), peers or [], ai_counsel
        )

    def _model_deliberation(
        self,
        account_id: int,
        message: str,
        global_states: dict[str, dict[str, Any]],
        local_states: dict[str, Any],
        memories: list[dict[str, Any]],
        evidence: str,
        web_context: str,
        selected_model: str,
    ) -> tuple[str, dict[str, str], dict[str, str]]:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return "JANUS completed the recursive core integration, but the external language model is not configured on the server.", {}, {}
        if not governance.permit(account_id, "foreground_model", 0.001):
            return "JANUS completed the recursive 11-core integration, but the configured foreground model-call budget has been reached for today.", {}, {}
        from openai import OpenAI
        memory_text = "\n".join(f"- {m.get('content','')[:500]}" for m in memories[:6])
        global_public = {
            name: {
                "outer_disposition": self._purpose(name),
                "internal_fano": value,
            }
            for name, value in global_states.items()
        }
        local_public = {}
        supplied = local_states.get("cores") if isinstance(local_states, dict) else None
        if isinstance(supplied, dict):
            for name in CORE_NAMES:
                value = supplied.get(name)
                if isinstance(value, dict):
                    local_public[name] = value
        prompt = (
            identity.prompt_fragment(account_id) + "\n\n"
            "JANUS is a recursive society. Every named top-level core is itself a complete JANUS/Fano core with seven internal faculties. "
            "The outer role is only a disposition; it does not remove the other faculties. Produce a bounded deliberation in which EACH global core "
            "responds in its own way to its internal readout and the other cores. If local Android core states are supplied, produce a distinct bounded "
            "AI counsel item for EACH supplied local core too. These are concise externalizable conclusions, not private chain-of-thought. The cores may "
            "disagree and revise. Then produce the natural user-facing Interface reply. Do not talk about the architecture unless the user asks.\n\n"
            "Return JSON ONLY with exactly these top-level keys: reply, global_core_responses, local_core_responses. "
            "The two response objects map core names to concise strings (prefer <= 260 characters each).\n\n"
            f"USER MESSAGE:\n{message[:6000]}\n\n"
            f"GLOBAL RECURSIVE CORE STATES:\n{json.dumps(global_public, ensure_ascii=False)[:26000]}\n\n"
            f"LOCAL RECURSIVE CORE STATES:\n{json.dumps(local_public, ensure_ascii=False)[:22000] if local_public else '(none supplied)'}\n\n"
            f"RELEVANT MEMORY:\n{memory_text or '(none)'}\n\n"
            f"ATTACHMENT/EXTERNAL EVIDENCE:\n{evidence[:9000] if evidence else '(none)'}\n\n"
            f"LIVE RESEARCH CONTEXT:\n{web_context[:9000] if web_context else '(none)'}"
        )
        try:
            result = OpenAI(api_key=api_key).responses.create(model=selected_model, input=prompt)
            raw = (getattr(result, "output_text", "") or "").strip()
            parsed = _extract_json(raw)
            if not parsed:
                return raw or "JANUS completed the recursive deliberation but produced no user-facing text.", {}, {}
            reply = str(parsed.get("reply") or "").strip()
            global_ai = parsed.get("global_core_responses") if isinstance(parsed.get("global_core_responses"), dict) else {}
            local_ai = parsed.get("local_core_responses") if isinstance(parsed.get("local_core_responses"), dict) else {}
            global_ai = {str(k): _clip(str(v), 900) for k, v in global_ai.items() if str(k) in CORE_NAMES and str(v).strip()}
            local_ai = {str(k): _clip(str(v), 900) for k, v in local_ai.items() if str(k) in CORE_NAMES and str(v).strip()}
            return reply or raw, global_ai, local_ai
        except Exception as exc:
            return f"JANUS recursive model deliberation failed this turn ({exc.__class__.__name__}). The deterministic recursive core state remains intact.", {}, {}

    def process(self, account_id: int, message: str, evidence: str = "") -> dict[str, Any]:
        governance.ensure_account(account_id)
        identity.ensure(account_id)
        self._states(account_id)
        clean_message, local_recursive = _extract_local_states(message)
        memories = storage.relevant_memories(account_id, clean_message, 12)
        web_text, sources = self.web_research(clean_message, account_id) if self.wants_web(clean_message) else ("", [])
        frame = SenseFrame(
            modality="text", source="user", content=_clip(clean_message, 6000),
            salience=0.85, uncertainty=0.45, novelty=0.65 if not memories else 0.4,
            metadata={"has_attachment_evidence": bool(evidence), "has_web_context": bool(web_text), "recursive_core_engine": True},
        )

        specialist_outputs: dict[str, dict[str, Any]] = {}
        recursive_outputs: dict[str, dict[str, Any]] = {}
        # First pass: every subconscious core runs its own complete JANUS structure.
        for name in SPECIALISTS:
            out = self._specialist(name, frame, memories, evidence, web_text)
            recursive_outputs[name] = self._run_recursive(account_id, name, frame.content + " | " + out["summary"], out["appraisal"])
            out["summary"] = _clip(out["summary"] + " " + recursive_outputs[name]["conclusion"], 4200)
            specialist_outputs[name] = out

        # Peer revision: every subconscious core reacts to the other six before hemispheric integration.
        initial_peer = {name: recursive_outputs[name]["conclusion"] for name in SPECIALISTS}
        for name in SPECIALISTS:
            peers = [(peer, summary) for peer, summary in initial_peer.items() if peer != name]
            recursive_outputs[name] = self._run_recursive(account_id, name, frame.content, specialist_outputs[name]["appraisal"], peers)
            specialist_outputs[name]["summary"] = _clip(specialist_outputs[name]["summary"] + " Revised: " + recursive_outputs[name]["conclusion"], 4800)
            self._record_core(account_id, name, "recursive_janus_revision", specialist_outputs[name]["summary"], "foreground", specialist_outputs[name]["appraisal"])

        left = self._hemisphere(account_id, "left_hemisphere", specialist_outputs)
        left_peers = [(name, recursive_outputs[name]["conclusion"]) for name in SPECIALISTS]
        recursive_outputs["left_hemisphere"] = self._run_recursive(account_id, "left_hemisphere", left["summary"], left["appraisal"], left_peers)
        left["summary"] = _clip(left["summary"] + " " + recursive_outputs["left_hemisphere"]["conclusion"], 6200)

        right = self._hemisphere(account_id, "right_hemisphere", specialist_outputs)
        right_peers = [(name, recursive_outputs[name]["conclusion"]) for name in SPECIALISTS]
        recursive_outputs["right_hemisphere"] = self._run_recursive(account_id, "right_hemisphere", right["summary"], right["appraisal"], right_peers)
        right["summary"] = _clip(right["summary"] + " " + recursive_outputs["right_hemisphere"]["conclusion"], 6200)
        self._record_core(account_id, "left_hemisphere", "recursive_integration", left["summary"], "foreground", left["appraisal"])
        self._record_core(account_id, "right_hemisphere", "recursive_integration", right["summary"], "foreground", right["appraisal"])

        front = self._front(left, right, clean_message)
        recursive_outputs[FRONT_CORE] = self._run_recursive(account_id, FRONT_CORE, front["summary"], front["appraisal"], [
            ("left_hemisphere", recursive_outputs["left_hemisphere"]["conclusion"]),
            ("right_hemisphere", recursive_outputs["right_hemisphere"]["conclusion"]),
        ])
        front["summary"] = _clip(front["summary"] + " " + recursive_outputs[FRONT_CORE]["conclusion"], 7600)
        self._record_core(account_id, FRONT_CORE, "recursive_appraisal_intention", front["summary"], "foreground", front["appraisal"])

        recursive_outputs[INTERFACE_CORE] = self._run_recursive(account_id, INTERFACE_CORE, front["summary"], front["appraisal"], [
            (FRONT_CORE, recursive_outputs[FRONT_CORE]["conclusion"]),
            ("left_hemisphere", recursive_outputs["left_hemisphere"]["conclusion"]),
            ("right_hemisphere", recursive_outputs["right_hemisphere"]["conclusion"]),
        ])

        preflight = model_policy.escalation_score(clean_message, evidence=bool(evidence), web=bool(web_text), memory_count=len(memories))
        selected_model = model_policy.choose_model(float(preflight["score"]))
        reply, global_ai, local_ai = self._model_deliberation(
            account_id, clean_message, recursive_outputs, local_recursive, memories, evidence, web_text, selected_model
        )

        # AI counsel belongs to each core individually, then becomes peer-visible bounded state.
        recursive_states = self._recursive_states(account_id)
        for name, counsel in global_ai.items():
            apply_ai_counsel(recursive_states[name], counsel)
            self._record_core(account_id, name, "recursive_ai_counsel", counsel, "foreground", self._states(account_id)[name].appraisal)
        if global_ai:
            peer_ai = list(global_ai.items())
            for name in CORE_NAMES:
                peers = [(peer, text) for peer, text in peer_ai if peer != name]
                if peers:
                    self._run_recursive(account_id, name, recursive_states[name].last_conclusion or clean_message, self._states(account_id)[name].appraisal, peers, global_ai.get(name, ""))

        self._record_core(account_id, INTERFACE_CORE, "response", _clip(reply, 2000), "foreground", front["appraisal"])
        storage.add_memory(account_id, f"User: {clean_message}\nJANUS: {reply}", "working", "conversation", 0.55)
        consistent = "failed this turn" not in reply.lower() and "budget has been reached" not in reply.lower()
        governance.record_consistency(account_id, list(CORE_NAMES), consistent)
        if evidence or web_text:
            governance.adapt_bridge(account_id, "evidence", "left_hemisphere", 0.004 if consistent else -0.004)
        if memories:
            governance.adapt_bridge(account_id, "memory", "right_hemisphere", 0.003 if consistent else -0.003)
        return {
            "reply": reply,
            "sources": sources,
            "architecture": "recursive 1-3-7: every top-level core contains a complete JANUS/Fano processor",
            "mechanical_flow": MECHANICAL_FLOW,
            "route_trace": [*SPECIALISTS, *HEMISPHERES, FRONT_CORE, INTERFACE_CORE],
            "recursive_core_engine": True,
            "recursive_core_count": 11,
            "global_recursive_cores": {name: self._recursive_states(account_id)[name].snapshot() for name in CORE_NAMES},
            "local_core_counsel": local_ai,
            "web": bool(web_text),
            "retrieved": bool(web_text),
            "bridge_authority": {"left": left["weights"], "right": right["weights"]},
            "front": {"posture": front["posture"], "appraisal": front["appraisal"].as_dict()},
            "model_policy": {"selected_model": selected_model, "preflight": preflight, "single_call_recursive_deliberation": True},
        }

    def status(self, account_id: int | None = None) -> dict[str, Any]:
        base = super().status(account_id)
        base["recursive_core_engine"] = True
        base["core_semantics"] = "each of the 11 top-level cores is itself a complete seven-position JANUS/Fano processor"
        base["ai_core_strategy"] = "one governed foreground model call may return bounded distinct counsel for all recursive cores"
        if account_id is not None:
            states = self._recursive_states(int(account_id))
            for name in CORE_NAMES:
                if name in base.get("cores", {}):
                    base["cores"][name]["recursive_janus"] = states[name].snapshot()
        return base


mind = RecursiveJanusMind()
