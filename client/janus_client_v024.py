import json
import os
import uuid

import janus_client_v023 as v023

APP_NAME = "JANUS - Global 7-2-1-1 v0.25"


class PresenceAPI(v023.AttachmentAPI):
    def core_exchange(self, device_id: str):
        return self.call(
            "POST", "/core-sync/exchange",
            {
                "device_id": device_id,
                "platform": "windows",
                "client_version": "0.25",
                "phase": "interface",
                "cycles": {},
                "observe_events": [],
                "memories": [],
                "conclusions": [],
            }, timeout=30,
        )

    def core_status(self):
        return self.call("GET", "/core-sync/status", timeout=30)


v023.v022.v021.base.API = PresenceAPI


class App(v023.App):
    def __init__(self):
        self._presence_timer = None
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
            self.after(300, self._presence_tick)

    def _presence_tick(self):
        if not self.user or not self.api.token:
            return
        self.bg(lambda: self.api.core_exchange(self.device_id), self._presence_done)

    def _presence_done(self, result):
        presence = (result or {}).get("presence") or {}
        server = (result or {}).get("server") or {}
        online = int(presence.get("online") or 0)
        registered = int(presence.get("registered") or 0)
        phase = str(server.get("phase") or "unknown")
        persistent = bool(server.get("persistent_storage", server.get("persistent", False)))
        self.status.set(f"Global {phase} · {online}/{registered} clients · storage {'persistent' if persistent else 'unknown'}")
        if self._presence_timer:
            try: self.after_cancel(self._presence_timer)
            except Exception: pass
        self._presence_timer = self.after(30_000, self._presence_tick)

    def render_options(self, result):
        super().render_options(result)
        if self.user and self.api.token:
            self.bg(self.api.core_status, self._render_global_presence)

    def _render_global_presence(self, runtime):
        if not isinstance(runtime, dict):
            return
        online = int(runtime.get("remote_clients") or 0)
        registered = int(runtime.get("registered_clients") or 0)
        phase = str(runtime.get("phase") or "unknown")
        persistent = bool(runtime.get("persistent_storage"))
        clients = runtime.get("clients") or []
        lines = [
            f"\n\nGLOBAL CONNECTIVITY\nPhase: {phase}\nStorage: {'persistent' if persistent else 'unknown'}\nClients online: {online} / registered: {registered}"
        ]
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
        super().logout_account()


if __name__ == "__main__":
    App().mainloop()
