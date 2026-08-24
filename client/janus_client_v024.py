import json
import os
import uuid

import janus_client_v023 as v023
from janus_local_society import LocalJanusSociety

APP_NAME = "JANUS - Local + Global 1|3|7 v0.25"


class PresenceAPI(v023.AttachmentAPI):
    def core_exchange(self, device_id: str, local_snapshot: dict):
        payload = {
            "device_id": device_id,
            "platform": "windows",
            "client_version": "0.25",
            "phase": str(local_snapshot.get("phase") or "interface"),
            "architecture": "1|3|7",
            "mechanical_flow": "7 -> 2 -> 1 -> 1",
            "cycles": local_snapshot.get("cycles") or {},
            "core_summaries": local_snapshot.get("core_summaries") or {},
            "front": local_snapshot.get("front") or "",
            "front_appraisal": local_snapshot.get("front_appraisal") or {},
            "consensus": local_snapshot.get("front") or "",  # temporary transport alias
            "interface": local_snapshot.get("interface") or "",
            "interface_appraisal": local_snapshot.get("interface_appraisal") or {},
            "observe_events": [],
            "memories": [],
            "conclusions": [],
        }
        return self.call("POST", "/core-sync/exchange", payload, timeout=30)

    def core_status(self):
        return self.call("GET", "/desktop/runtime-cores", timeout=30)


v023.v022.v021.base.API = PresenceAPI


class App(v023.App):
    def __init__(self):
        self._presence_timer = None
        self.local_society = LocalJanusSociety()
        super().__init__()
        self.title(APP_NAME)
        device_id = str(self.cfg.get("device_id") or "").strip()
        if not device_id:
            device_id = "windows-" + uuid.uuid4().hex
            self.cfg["device_id"] = device_id
            v023.v022.v021.base.save_cfg(self.cfg)
        self.device_id = device_id

    def _auth_success(self, result):
        super()._auth_success(result)
        if self.user and self.api.token:
            self.local_society.sense("runtime", "windows-client", "authenticated Windows JANUS session became active", salience=0.45, uncertainty=0.05, novelty=0.15)
            self.after(300, self._presence_tick)

    def send(self):
        try:
            message = self.entry.get("1.0", "end").strip()
            attachments = list(getattr(self, "_pending_attachments", []) or [])
            if message:
                self.local_society.sense("text", "user", message, salience=0.8, uncertainty=0.25, novelty=0.5)
            for item in attachments[:4]:
                self.local_society.sense("file", "user-attachment", str(item.get("filename") or "attached file"), salience=0.65, uncertainty=0.45, novelty=0.45)
        except Exception:
            pass
        super().send()

    def _presence_tick(self):
        if not self.user or not self.api.token:
            return
        local = self.local_society.pulse()
        self.bg(lambda: self.api.core_exchange(self.device_id, local), self._presence_done)

    def _presence_done(self, result):
        presence = (result or {}).get("presence") or {}
        server = (result or {}).get("server") or {}
        try:
            local = self.local_society.ingest_peer(server)
        except Exception:
            local = self.local_society.snapshot()
        online = int(presence.get("online") or 0)
        registered = int(presence.get("registered") or 0)
        phase = str(server.get("phase") or "unknown")
        topology = str(server.get("conceptual_topology") or "1|3|7")
        front = str(server.get("front") or server.get("consensus") or "").strip()
        appraisal = server.get("front_appraisal") or {}
        posture = str(appraisal.get("action_posture") or "").strip()
        local_posture = str((local.get("front_appraisal") or {}).get("action_posture") or "respond_normally")
        suffix = f" · global {posture}" if posture else ""
        self.status.set(f"Local {local_posture} ↔ Global {topology} {phase} · {online}/{registered} clients{suffix}")
        self._last_front = front
        self._last_front_appraisal = appraisal
        if self._presence_timer:
            try: self.after_cancel(self._presence_timer)
            except Exception: pass
        self._presence_timer = self.after(30_000, self._presence_tick)

    def render_options(self, result):
        super().render_options(result)
        self._render_local_society()
        if self.user and self.api.token:
            self.bg(self.api.core_status, self._render_global_presence)

    def _render_local_society(self):
        local = self.local_society.snapshot()
        app = local.get("front_appraisal") or {}
        cycles = local.get("cycles") or {}
        lines = [
            "\n\nLOCAL JANUS SOCIETY",
            "Topology: 1|3|7 (mechanical 7 -> 2 -> 1 -> 1)",
            "Persistent deterministic 11-core Windows runtime · background external API calls: 0",
            "All seven Fano senses feed both hemispheres; Left constrains, Right expands, Front appraises/intends, Interface expresses/acts.",
            "Front appraisal: " + ", ".join(f"{k}={v}" for k, v in app.items() if k in {"confidence", "valence", "uncertainty", "risk", "opportunity", "conflict", "action_posture"}),
            "Cycles: " + ", ".join(f"{name}={cycles.get(name, 0)}" for name in ("evidence", "safety", "counterpoint", "context", "logic", "novelty", "memory", "left_hemisphere", "right_hemisphere", "front", "interface")),
        ]
        try:
            self.options_text.config(state="normal")
            self.options_text.insert("end", "\n".join(lines))
            self.options_text.config(state="disabled")
        except Exception:
            pass

    def _render_global_presence(self, response):
        runtime = response.get("runtime") if isinstance(response, dict) and isinstance(response.get("runtime"), dict) else response
        if not isinstance(runtime, dict):
            return
        online = int(runtime.get("remote_clients") or 0)
        registered = int(runtime.get("registered_clients") or 0)
        phase = str(runtime.get("phase") or "unknown")
        topology = str(runtime.get("conceptual_topology") or runtime.get("topology") or "1|3|7")
        flow = str(runtime.get("mechanical_flow") or runtime.get("mechanical_topology") or "7 -> 2 -> 1 -> 1")
        persistent = bool(runtime.get("persistent_storage"))
        clients = runtime.get("clients") or []
        cores = runtime.get("cores") or {}
        front = cores.get("front") or cores.get("consensus") or {}
        appraisal = front.get("appraisal") or {}
        lines = [
            f"\n\nGLOBAL JANUS SOCIETY\nTopology: {topology} (mechanical {flow})\nPhase: {phase}\nStorage: {'persistent' if persistent else 'unknown'}\nClients online: {online} / registered: {registered}",
            "Seven Fano subconscious cores all feed both hemispheres; peer state returns to the local society as a new sense rather than overwriting it.",
        ]
        if appraisal:
            lines.append("Front appraisal: " + ", ".join(f"{k}={v}" for k, v in appraisal.items() if k in {"confidence", "valence", "uncertainty", "risk", "opportunity", "conflict", "action_posture"}))
        for c in clients[:8]:
            lines.append(f"• {c.get('platform','device')} {c.get('client_version','?')} · {('online' if c.get('online') else 'offline')} · last seen {c.get('age_seconds','?')}s ago")
        try:
            self.options_text.config(state="normal")
            self.options_text.insert("end", "\n".join(lines))
            self.options_text.config(state="disabled")
        except Exception:
            pass

    def logout_account(self):
        if self._presence_timer:
            try: self.after_cancel(self._presence_timer)
            except Exception: pass
            self._presence_timer = None
        try:
            self.local_society.sense("runtime", "windows-client", "authenticated Windows JANUS session signed out", salience=0.3, uncertainty=0.05, novelty=0.1)
        except Exception:
            pass
        super().logout_account()


if __name__ == "__main__":
    App().mainloop()
