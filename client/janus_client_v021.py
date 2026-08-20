import tkinter as tk
from tkinter import ttk

import janus_client_v020 as base

APP_NAME = "JANUS - Global 7-3-1 v0.21"


class API(base.API):
    def runtime_cores(self, user):
        return self.get("runtime-cores", user)


# v0.20 constructs API() inside App.__init__; replace that factory before
# delegating so the rest of the stable client remains intact.
base.API = API


class App(base.App):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)

    def build_cores(self):
        p = self.page("cores")
        self.head(p, "Cores", "Live seven-core wake/sleep runtime • local cycle uses no external model/API calls")

        self.core_phase = tk.StringVar(value="Runtime loading…")
        ttk.Label(p, textvariable=self.core_phase, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        self.core_tree = ttk.Treeview(
            p,
            columns=("core", "state", "cycles", "inbox", "last"),
            show="headings",
            height=8,
        )
        columns = [
            ("core", "Core", 155),
            ("state", "State", 100),
            ("cycles", "Cycles", 90),
            ("inbox", "Inbox", 80),
            ("last", "Last activity (UTC)", 235),
        ]
        for key, label, width in columns:
            self.core_tree.heading(key, text=label)
            self.core_tree.column(key, width=width, stretch=(key == "last"))
        self.core_tree.pack(fill="x", pady=(0, 10))

        self.core_architecture = tk.Text(
            p,
            state="disabled",
            wrap="word",
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
            height=13,
        )
        self.core_architecture.pack(fill="both", expand=True)

    def refresh(self, key):
        if not self.user:
            return
        self.status.set("Syncing")
        if key == "cores":
            def fetch_both():
                return {
                    "architecture": self.api.get("cores", self.user),
                    "live": self.api.runtime_cores(self.user),
                }
            return self.bg(fetch_both, self.render_cores)
        return super().refresh(key)

    def render_cores(self, result):
        architecture = result.get("architecture", {})
        live = result.get("live", {})
        runtime = live.get("runtime", {})
        phase = str(runtime.get("phase", "unknown")).upper()
        wake_seconds = runtime.get("wake_seconds", "?")
        sleep_seconds = runtime.get("sleep_seconds", "?")
        budget = runtime.get("external_api_budget_used", 0)
        paid_bg = bool(live.get("paid_background_api_enabled", False))

        self.core_phase.set(
            f"{phase}  •  wake {wake_seconds}s / sleep {sleep_seconds}s  •  "
            f"core-cycle external API usage: {budget}  •  paid background AI: {'ON' if paid_bg else 'OFF'}"
        )

        self.core_tree.delete(*self.core_tree.get_children())
        cores = runtime.get("cores", {}) or {}
        for name, info in cores.items():
            state = "AWAKE" if info.get("awake") else "SLEEPING"
            last = str(info.get("last_cycle_at") or "—").replace("T", " ")[:19]
            self.core_tree.insert(
                "",
                "end",
                values=(
                    name.replace("_", " ").title(),
                    state,
                    info.get("cycle_count", 0),
                    info.get("pending_messages", 0),
                    last,
                ),
            )

        text = "1 INTEGRATOR\n" + (architecture.get("one_integrator") or {}).get("description", "")
        text += "\n\n3 BRIDGES\n" + "".join(
            f"• {k}: {v}\n" for k, v in (architecture.get("three_bridges") or {}).items()
        )
        text += "\n7 SPECIALISTS\n" + "".join(
            f"• {k}: {v}\n" for k, v in (architecture.get("seven_roles") or {}).items()
        )
        text += "\nRUNTIME\n" + str(live.get("note") or "")
        self.settext(self.core_architecture, text)
        self.status.set("Active · " + phase.title())

    def render_options(self, result):
        latest = result.get("latest_activity") or {}
        phase = str(result.get("core_phase") or "unknown").title()
        runtime = result.get("core_runtime") or {}
        self.settext(
            self.options_text,
            f"Status: {result.get('status', 'Active')}\n"
            f"Profile: {self.user}\n"
            f"Architecture: {result.get('architecture', '7 → 3 → 1')}\n"
            f"Core phase: {phase}\n"
            f"Wake: {runtime.get('wake_seconds', '?')} seconds\n"
            f"Sleep: {runtime.get('sleep_seconds', '?')} seconds\n"
            f"Core-cycle external API usage: {result.get('external_api_budget_used_by_core_cycle', 0)}\n"
            f"Unread JANUS messages: {result.get('unread_messages', 0)}\n\n"
            f"Latest activity:\n{latest.get('detail', 'No activity yet.')}",
        )
        self.unread.set(str(result.get("unread_messages", 0)))
        self.status.set(result.get("status", "Active") + " · " + phase)

    def schedule(self, key):
        if self.timer:
            try:
                self.after_cancel(self.timer)
            except Exception:
                pass
        self.timer = None
        if self.auto.get():
            target = key if key in ("messages", "observe", "options", "cores", "memory", "activity") else "messages"
            self.timer = self.after(
                max(5, self.seconds.get()) * 1000,
                lambda: (self.refresh(target), self.schedule(key)),
            )


if __name__ == "__main__":
    App().mainloop()
