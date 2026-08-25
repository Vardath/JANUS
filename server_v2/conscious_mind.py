from __future__ import annotations

import json
import os
import time
from typing import Any

from . import governance, identity, memory_maintenance, model_policy, storage
from .mind import SPECIALISTS, HEMISPHERES
from .recursive_core import apply_ai_counsel
from .recursive_mind import RecursiveJanusMind, _clip, _extract_json, _extract_local_states
from .senses import SenseFrame
from .topology import CORE_NAMES, FRONT_CORE, INTERFACE_CORE, MECHANICAL_FLOW


class ConsciousStreamJanusMind(RecursiveJanusMind):
    """Recursive JANUS with one enforced outward stream of consciousness.

    Every user event is registered to every core, but active outward routing is strict:
    seven specialists -> both hemispheres -> Front -> Interface. Interface never receives
    specialist/hemisphere state directly. Background peer exchange is permitted, but it
    cannot bypass Front when producing a user-facing response.
    """

    def __init__(self):
        super().__init__()
        self.last_rest_maintenance_at = 0
        self.last_rouse_at = 0

    def _loop(self):
        while self._running:
            self.phase = "wake"
            deadline = time.time() + self.wake_seconds
            while self._running and time.time() < deadline:
                self._background_tick()
                time.sleep(min(30, max(2, deadline - time.time())))
            if not self._running:
                break
            self.phase = "sleep"
            self._rest_maintenance()
            deadline = time.time() + self.sleep_seconds
            # Rest is passive but interruptible: foreground process() remains callable.
            while self._running and time.time() < deadline:
                time.sleep(min(30, max(2, deadline - time.time())))

    def _background_tick(self):
        if self.phase != "wake":
            return
        self.last_cycle_at = int(time.time())
        from . import recursive_background
        for row in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            recursive_background.tick(self, int(row["id"]))

    def _rest_maintenance(self):
        self.last_rest_maintenance_at = int(time.time())
        for row in storage.rows("SELECT id FROM v2_accounts ORDER BY id"):
            aid = int(row["id"])
            memory_maintenance.maintain(aid)
        # No recursive think() calls here: loaded state remains responsive but quiet.

    def _deliberate_one_call(self, account_id: int, message: str, global_states: dict[str, dict[str, Any]],
                             local_states: dict[str, Any], memories: list[dict[str, Any]], evidence: str,
                             web_context: str, selected_model: str, front_state: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, str]]:
        # Preserve the historical offline test hook when explicitly replaced.
        hook = getattr(self, "_model_reply", None)
        base_hook = getattr(RecursiveJanusMind, "_model_reply", None)
        if hook is not None and getattr(hook, "__func__", None) is not base_hook and not os.getenv("OPENAI_API_KEY", "").strip():
            try:
                return str(hook(account_id, message, front_state, memories, evidence, web_context, selected_model)), {}, {}
            except Exception:
                pass
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return "JANUS completed the recursive stream integration, but the external language model is not configured on the server.", {}, {}
        if not governance.permit(account_id, "foreground_model", 0.001):
            return "JANUS completed the recursive stream integration, but the configured foreground model-call budget has been reached for today.", {}, {}
        from openai import OpenAI
        supplied = local_states.get("cores") if isinstance(local_states, dict) else None
        local_public = {name: supplied.get(name) for name in CORE_NAMES if isinstance(supplied, dict) and isinstance(supplied.get(name), dict)}
        global_public = {name: {"outer_disposition": self._purpose(name), "internal_fano": state} for name, state in global_states.items()}
        memory_text = "\n".join(f"- {m.get('content','')[:500]}" for m in memories[:8])
        prompt = (
            identity.prompt_fragment(account_id) + "\n\n"
            "JANUS has 11 recursive top-level cores. Every core may receive bounded AI counsel, but there is exactly one outward cognitive stream. "
            "The seven specialist results are integrated by Left and Right, then Front/stream-of-consciousness integrates the hemispheres. "
            "Interface is an output boundary and MUST receive only the Front stream result; no specialist or hemisphere may bypass Front into Interface. "
            "Return concise externalizable conclusions, never private chain-of-thought. Avoid repeating a peer conclusion unless it materially changes the assessment.\n\n"
            "Return JSON ONLY with keys front_stream_reply, global_core_responses, local_core_responses. "
            "front_stream_reply is the natural answer to the user and must be expressed from FRONT_STREAM_STATE only. "
            "The response maps contain short per-core counsel; Interface counsel, if present, must be based only on the corresponding Front state.\n\n"
            f"USER EVENT (registered to all cores):\n{message[:6000]}\n\n"
            f"FRONT_STREAM_STATE (sole outward source):\n{json.dumps(front_state, ensure_ascii=False)[:12000]}\n\n"
            f"GLOBAL CORE STATES (for per-core counsel, not direct Interface input):\n{json.dumps(global_public, ensure_ascii=False)[:25000]}\n\n"
            f"LOCAL CORE STATES (for per-core counsel):\n{json.dumps(local_public, ensure_ascii=False)[:20000] if local_public else '(none)'}\n\n"
            f"RELEVANT MEMORY:\n{memory_text or '(none)'}\n\n"
            f"EVIDENCE:\n{evidence[:7000] if evidence else '(none)'}\n\n"
            f"WEB CONTEXT:\n{web_context[:7000] if web_context else '(none)'}"
        )
        try:
            result = OpenAI(api_key=api_key).responses.create(model=selected_model, input=prompt)
            raw = (getattr(result, "output_text", "") or "").strip()
            parsed = _extract_json(raw)
            if not parsed:
                return raw or "JANUS completed the stream integration but produced no outward text.", {}, {}
            reply = str(parsed.get("front_stream_reply") or "").strip()
            g = parsed.get("global_core_responses") if isinstance(parsed.get("global_core_responses"), dict) else {}
            l = parsed.get("local_core_responses") if isinstance(parsed.get("local_core_responses"), dict) else {}
            global_ai = {str(k): _clip(str(v), 900) for k,v in g.items() if str(k) in CORE_NAMES and str(v).strip()}
            local_ai = {str(k): _clip(str(v), 900) for k,v in l.items() if str(k) in CORE_NAMES and str(v).strip()}
            return reply or raw, global_ai, local_ai
        except Exception as exc:
            return f"JANUS completed deterministic stream integration, but the foreground model call failed ({exc.__class__.__name__}).", {}, {}

    def process(self, account_id: int, message: str, evidence: str = "") -> dict[str, Any]:
        aid = int(account_id)
        governance.ensure_account(aid); identity.ensure(aid); self._states(aid)
        clean_message, local_recursive = _extract_local_states(message)
        memories = storage.relevant_memories(aid, clean_message, 12)
        web_text, sources = self.web_research(clean_message, aid) if self.wants_web(clean_message) else ("", [])
        was_resting = self.phase == "sleep"
        if was_resting:
            self.last_rouse_at = int(time.time())
            storage.add_event(aid, FRONT_CORE, "foreground_rouse", "User input interrupted passive rest; recursive cores became available for this foreground turn.", mode="foreground")

        nested = self._recursive_states(aid)
        # Presentation to all cores is a sensory registration, not an unauthorized shortcut.
        for name in CORE_NAMES:
            self._processor.register_user_input(nested[name], clean_message)

        frame = SenseFrame(modality="text", source="user", content=_clip(clean_message,6000), salience=0.85,
                           uncertainty=0.45, novelty=0.65 if not memories else 0.4,
                           metadata={"broadcast_to_all_cores": True, "roused_from_rest": was_resting})
        specialist_outputs: dict[str, dict[str, Any]] = {}
        recursive_outputs: dict[str, dict[str, Any]] = {}
        for name in SPECIALISTS:
            out = self._specialist(name, frame, memories, evidence, web_text)
            recursive_outputs[name] = self._run_recursive(aid, name, frame.content + " | " + out["summary"], out["appraisal"])
            out["summary"] = _clip(out["summary"] + " " + recursive_outputs[name]["conclusion"], 4200)
            specialist_outputs[name] = out
        initial = {n: recursive_outputs[n]["conclusion"] for n in SPECIALISTS}
        for name in SPECIALISTS:
            peers = [(p,s) for p,s in initial.items() if p != name]
            revised = self._run_recursive(aid, name, frame.content, specialist_outputs[name]["appraisal"], peers)
            recursive_outputs[name] = revised
            specialist_outputs[name]["summary"] = _clip(specialist_outputs[name]["summary"] + " Revised: " + revised["conclusion"], 4800)
            self._record_core(aid, name, "recursive_janus_revision", specialist_outputs[name]["summary"], "foreground", specialist_outputs[name]["appraisal"])

        left = self._hemisphere(aid, "left_hemisphere", specialist_outputs)
        right = self._hemisphere(aid, "right_hemisphere", specialist_outputs)
        seven_peers = [(n, recursive_outputs[n]["conclusion"]) for n in SPECIALISTS]
        recursive_outputs["left_hemisphere"] = self._run_recursive(aid, "left_hemisphere", left["summary"], left["appraisal"], seven_peers)
        recursive_outputs["right_hemisphere"] = self._run_recursive(aid, "right_hemisphere", right["summary"], right["appraisal"], seven_peers)
        left["summary"] = _clip(left["summary"] + " " + recursive_outputs["left_hemisphere"]["conclusion"],6200)
        right["summary"] = _clip(right["summary"] + " " + recursive_outputs["right_hemisphere"]["conclusion"],6200)
        self._record_core(aid,"left_hemisphere","recursive_integration",left["summary"],"foreground",left["appraisal"])
        self._record_core(aid,"right_hemisphere","recursive_integration",right["summary"],"foreground",right["appraisal"])

        front = self._front(left, right, clean_message)
        front_peers = [("left_hemisphere",recursive_outputs["left_hemisphere"]["conclusion"]),("right_hemisphere",recursive_outputs["right_hemisphere"]["conclusion"])]
        recursive_outputs[FRONT_CORE] = self._run_recursive(aid, FRONT_CORE, front["summary"], front["appraisal"], front_peers)
        front["summary"] = _clip(front["summary"] + " " + recursive_outputs[FRONT_CORE]["conclusion"],7600)
        self._record_core(aid,FRONT_CORE,"stream_of_consciousness",front["summary"],"foreground",front["appraisal"])

        # Interface receives Front only. This is the enforced output boundary.
        recursive_outputs[INTERFACE_CORE] = self._run_recursive(
            aid, INTERFACE_CORE, front["summary"], front["appraisal"],
            [(FRONT_CORE, recursive_outputs[FRONT_CORE]["conclusion"])]
        )
        preflight = model_policy.escalation_score(clean_message,evidence=bool(evidence),web=bool(web_text),memory_count=len(memories))
        selected_model = model_policy.choose_model(float(preflight["score"]))
        reply, global_ai, local_ai = self._deliberate_one_call(aid, clean_message, recursive_outputs, local_recursive, memories, evidence, web_text, selected_model, front)

        for name,counsel in global_ai.items():
            # Interface never accepts direct society-wide counsel; its outward content comes from Front stream.
            if name == INTERFACE_CORE:
                continue
            apply_ai_counsel(nested[name], counsel)
            self._record_core(aid,name,"recursive_ai_counsel",counsel,"foreground",self._states(aid)[name].appraisal)
        if reply:
            apply_ai_counsel(nested[INTERFACE_CORE], reply)
        self._record_core(aid,INTERFACE_CORE,"response",_clip(reply,2000),"foreground",front["appraisal"])
        storage.add_memory(aid,f"User: {clean_message}\nJANUS: {reply}","working","conversation",0.55)
        consistent = "failed" not in reply.lower() and "budget has been reached" not in reply.lower()
        governance.record_consistency(aid,list(CORE_NAMES),consistent)
        return {
            "reply": reply, "sources": sources,
            "architecture": "recursive 1-3-7 with one Front stream-of-consciousness output path",
            "mechanical_flow": MECHANICAL_FLOW,
            "route_trace": [*SPECIALISTS,*HEMISPHERES,FRONT_CORE,INTERFACE_CORE],
            "outward_route_enforced": True, "interface_input_source": FRONT_CORE,
            "user_input_registered_to_all_cores": True, "roused_from_rest": was_resting,
            "recursive_core_engine": True, "global_recursive_cores": {n:nested[n].snapshot() for n in CORE_NAMES},
            "local_core_counsel": local_ai, "web": bool(web_text), "retrieved": bool(web_text),
            "bridge_authority": {"left":left["weights"],"right":right["weights"]},
            "front": {"posture":front["posture"],"appraisal":front["appraisal"].as_dict(),"stream":front["summary"]},
            "model_policy": {"selected_model":selected_model,"preflight":preflight,"single_call_recursive_deliberation":True},
        }

    def status(self, account_id: int | None = None) -> dict[str, Any]:
        base = super().status(account_id)
        base["outward_route"] = "7 specialists -> left/right -> front stream -> interface"
        base["interface_input_source"] = FRONT_CORE
        base["rest_is_passive"] = True
        base["foreground_can_rouse"] = True
        base["last_rest_maintenance_at"] = self.last_rest_maintenance_at
        base["last_rouse_at"] = self.last_rouse_at
        return base


mind = ConsciousStreamJanusMind()
