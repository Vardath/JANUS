import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib import request, error, parse

APP_NAME = "JANUS - Global 7-3-1 v0.14"
DEFAULT_SERVER = "https://janus-global-core.onrender.com"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".janus")
CONFIG_FILE = os.path.join(CONFIG_DIR, "client.json")


class ApiError(Exception):
    pass


class JanusAPI:
    def __init__(self, base_url=DEFAULT_SERVER):
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def request(self, method, path, payload=None, timeout=60):
        url = self.base_url + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", errors="replace")
                if not raw:
                    return {}
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"text": raw}
        except error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body)
            except Exception:
                detail = body or str(e)
            raise ApiError(f"HTTP {e.code}: {detail}")
        except Exception as e:
            raise ApiError(str(e))

    def health(self):
        return self.request("GET", "/health", timeout=15)

    def chat(self, profile_id, message):
        return self.request("POST", "/desktop/chat", {"profile_id": profile_id, "message": message}, timeout=120)

    def get_screen(self, screen, profile_id):
        query = parse.urlencode({"username": profile_id})
        return self.request("GET", f"/desktop/{screen}?{query}", timeout=30)


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def flatten_rows(data):
    rows = []
    tables = (data or {}).get("tables", {}) if isinstance(data, dict) else {}
    for table, items in tables.items():
        for item in items or []:
            if not isinstance(item, dict):
                continue
            text = item.get("detail") or item.get("content") or item.get("message") or item.get("text") or ""
            kind = item.get("event_type") or item.get("role") or item.get("type") or table
            when = item.get("created_at") or item.get("updated_at") or item.get("timestamp") or ""
            rows.append({"table": table, "kind": str(kind), "when": str(when), "text": str(text), "raw": item})
    rows.sort(key=lambda r: r["when"], reverse=True)
    return rows


class JanusClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.api = JanusAPI(self.cfg.get("server", DEFAULT_SERVER))
        self.profile_id = self.cfg.get("profile_id") or self.cfg.get("username") or os.environ.get("USERNAME") or os.environ.get("USER") or "local-user"
        self.cfg["profile_id"] = self.profile_id
        self.cfg.pop("username", None)
        self.auto_refresh = tk.BooleanVar(value=self.cfg.get("auto_refresh", True))
        self.refresh_seconds = tk.IntVar(value=int(self.cfg.get("refresh_seconds", 10)))
        self.show_chat_activity = tk.BooleanVar(value=self.cfg.get("show_chat_activity", True))
        self.show_technical = tk.BooleanVar(value=self.cfg.get("show_technical", False))
        self._refresh_job = None

        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(940, 640)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except Exception:
            pass
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Sub.TLabel", font=("Segoe UI", 10))
        self.style.configure("Card.TLabelframe", padding=10)
        self.style.configure("Card.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

        self.status_var = tk.StringVar(value="Checking global server...")
        self.user_var = tk.StringVar(value=f"Local profile: {self.profile_id}")
        self._build_shell()
        self.after(150, self.check_health)
        self.after(350, lambda: self.append_chat("JANUS", "Connected. Ready."))

    def _build_shell(self):
        top = ttk.Frame(self, padding=(12, 8)); top.pack(fill="x")
        ttk.Label(top, text="JANUS", font=("Segoe UI", 17, "bold")).pack(side="left")
        ttk.Label(top, text="Global 7-3-1", font=("Segoe UI", 11)).pack(side="left", padx=(8, 0))
        ttk.Label(top, textvariable=self.user_var).pack(side="right")
        ttk.Label(top, textvariable=self.status_var).pack(side="right", padx=(0, 18))

        body = ttk.Frame(self); body.pack(fill="both", expand=True)
        self.nav = ttk.Frame(body, padding=(8, 10), width=175); self.nav.pack(side="left", fill="y"); self.nav.pack_propagate(False)
        self.content = ttk.Frame(body, padding=(12, 8)); self.content.pack(side="left", fill="both", expand=True)
        self.pages = {}
        for label, key in [("Chat","chat"),("Observe","observe"),("Cores","cores"),("Memory","memory"),("Activity","activity"),("Settings","settings")]:
            ttk.Button(self.nav, text=label, command=lambda k=key: self.show_page(k)).pack(fill="x", pady=3)
        ttk.Separator(self.nav).pack(fill="x", pady=10)
        ttk.Label(self.nav, text="Sign-in will be handled by the app store/platform.", wraplength=150, justify="left").pack(fill="x", pady=4)

        self._build_chat_page()
        self._build_observe_page()
        self._build_cores_page()
        self._build_memory_page()
        self._build_activity_page()
        self._build_settings_page()
        self.show_page("chat")

    def _new_page(self, key):
        f = ttk.Frame(self.content); self.pages[key] = f; return f

    def _header(self, page, title, subtitle="", refresh=None):
        h = ttk.Frame(page); h.pack(fill="x", pady=(0, 10))
        left = ttk.Frame(h); left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text=title, style="Title.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(left, text=subtitle, style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        if refresh:
            ttk.Button(h, text="Refresh", command=refresh).pack(side="right")

    def _build_chat_page(self):
        page = self._new_page("chat")
        self._header(page, "Conversation", "Enter sends • Shift+Enter starts a new line")
        self.chat_log = tk.Text(page, wrap="word", state="disabled", font=("Segoe UI", 11), padx=8, pady=8)
        self.chat_log.pack(fill="both", expand=True)
        bottom = ttk.Frame(page); bottom.pack(fill="x", pady=(8, 0))
        self.message_entry = tk.Text(bottom, height=4, wrap="word", font=("Segoe UI", 11), padx=6, pady=6)
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", self._enter_send)
        self.message_entry.bind("<Shift-Return>", self._shift_enter)
        ttk.Button(bottom, text="Send", command=self.send_chat).pack(side="left", padx=(8, 0), fill="y")

    def _build_observe_page(self):
        page = self._new_page("observe")
        self._header(page, "Observe", "Current and recent JANUS process notes", lambda: self.refresh_page("observe"))
        panes = ttk.Panedwindow(page, orient="horizontal"); panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes, padding=4); right = ttk.Frame(panes, padding=4); panes.add(left, weight=2); panes.add(right, weight=3)
        self.observe_status = tk.StringVar(value="Waiting for data...")
        ttk.Label(left, textvariable=self.observe_status, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.observe_tree = ttk.Treeview(left, columns=("time","kind"), show="headings", height=18)
        self.observe_tree.heading("time", text="Time"); self.observe_tree.heading("kind", text="Note")
        self.observe_tree.column("time", width=125, stretch=False); self.observe_tree.column("kind", width=220)
        self.observe_tree.pack(fill="both", expand=True)
        self.observe_tree.bind("<<TreeviewSelect>>", self._open_observe_note)
        ttk.Label(right, text="Selected note", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 6))
        self.observe_detail = tk.Text(right, wrap="word", state="disabled", font=("Segoe UI", 11), padx=8, pady=8)
        self.observe_detail.pack(fill="both", expand=True)
        self.observe_rows = []

    def _build_cores_page(self):
        page = self._new_page("cores")
        self._header(page, "Cores", "JANUS 7 → 3 → 1 processing architecture", lambda: self.refresh_page("cores"))
        self.cores_status = tk.StringVar(value="Loading core status...")
        ttk.Label(page, textvariable=self.cores_status, font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 8))
        self.core_cards = ttk.Frame(page); self.core_cards.pack(fill="both", expand=True)

    def _build_memory_page(self):
        page = self._new_page("memory")
        self._header(page, "Memory", "Conversation and promoted memory records", lambda: self.refresh_page("memory"))
        panes = ttk.Panedwindow(page, orient="horizontal"); panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes); right = ttk.Frame(panes); panes.add(left, weight=2); panes.add(right, weight=3)
        self.memory_tree = ttk.Treeview(left, columns=("time","level","role"), show="headings")
        for col, label, width in [("time","Time",130),("level","Level",90),("role","Type",100)]:
            self.memory_tree.heading(col, text=label); self.memory_tree.column(col, width=width, stretch=(col=="role"))
        self.memory_tree.pack(fill="both", expand=True); self.memory_tree.bind("<<TreeviewSelect>>", self._open_memory)
        self.memory_detail = tk.Text(right, wrap="word", state="disabled", font=("Segoe UI",11), padx=8, pady=8); self.memory_detail.pack(fill="both", expand=True)
        self.memory_rows = []

    def _build_activity_page(self):
        page = self._new_page("activity")
        self._header(page, "Activity", "Previous thoughts, reflections, decisions and system events", lambda: self.refresh_page("activity"))
        controls = ttk.Frame(page); controls.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(controls, text="Include chat activity", variable=self.show_chat_activity, command=lambda: self.refresh_page("activity")).pack(side="left")
        self.activity_tree = ttk.Treeview(page, columns=("time","kind","summary"), show="headings")
        self.activity_tree.heading("time", text="Time"); self.activity_tree.heading("kind", text="Type"); self.activity_tree.heading("summary", text="Summary")
        self.activity_tree.column("time", width=140, stretch=False); self.activity_tree.column("kind", width=150, stretch=False); self.activity_tree.column("summary", width=560)
        self.activity_tree.pack(fill="both", expand=True); self.activity_tree.bind("<Double-1>", self._activity_popup)
        self.activity_rows = []

    def _build_settings_page(self):
        page = self._new_page("settings")
        self._header(page, "Settings", "Desktop display and live-update controls")
        live = ttk.LabelFrame(page, text="Live updates", style="Card.TLabelframe"); live.pack(fill="x", pady=8)
        ttk.Checkbutton(live, text="Automatically refresh Observe and Activity", variable=self.auto_refresh, command=self._settings_changed).pack(anchor="w", pady=4)
        row = ttk.Frame(live); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Refresh interval:").pack(side="left")
        for sec in (5, 10, 15, 30, 60):
            ttk.Radiobutton(row, text=f"{sec}s", value=sec, variable=self.refresh_seconds, command=self._settings_changed).pack(side="left", padx=5)

        display = ttk.LabelFrame(page, text="Display", style="Card.TLabelframe"); display.pack(fill="x", pady=8)
        ttk.Checkbutton(display, text="Include chat messages in Activity", variable=self.show_chat_activity, command=self._settings_changed).pack(anchor="w", pady=4)
        ttk.Checkbutton(display, text="Show technical/raw details where available", variable=self.show_technical, command=self._settings_changed).pack(anchor="w", pady=4)

        server = ttk.LabelFrame(page, text="JANUS background core", style="Card.TLabelframe"); server.pack(fill="x", pady=8)
        self.server_settings_summary = tk.StringVar(value="Loading server configuration...")
        ttk.Label(server, textvariable=self.server_settings_summary, wraplength=760, justify="left").pack(anchor="w")
        ttk.Label(server, text="These values currently reflect the deployed JANUS server. Runtime server switches are kept separate from desktop display controls until the global worker supports safe per-profile changes.", wraplength=760, justify="left").pack(anchor="w", pady=(8,0))
        ttk.Button(page, text="Save desktop settings", command=self._save_settings).pack(anchor="w", pady=10)

    def _enter_send(self, event=None):
        self.send_chat(); return "break"

    def _shift_enter(self, event=None):
        self.message_entry.insert("insert", "\n"); return "break"

    def show_page(self, key):
        for p in self.pages.values(): p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        if key != "chat": self.refresh_page(key)
        self._schedule_refresh(key)

    def _schedule_refresh(self, key):
        if self._refresh_job:
            try: self.after_cancel(self._refresh_job)
            except Exception: pass
            self._refresh_job = None
        if self.auto_refresh.get() and key in ("observe", "activity"):
            self._refresh_job = self.after(max(5, self.refresh_seconds.get()) * 1000, lambda: self._auto_refresh_tick(key))

    def _auto_refresh_tick(self, key):
        if self.pages[key].winfo_ismapped() and self.auto_refresh.get():
            self.refresh_page(key)
            self._schedule_refresh(key)

    def _settings_changed(self):
        self._save_settings(silent=True)
        for key in ("observe", "activity"):
            if self.pages[key].winfo_ismapped(): self._schedule_refresh(key)

    def _save_settings(self, silent=False):
        self.cfg.update({
            "profile_id": self.profile_id,
            "server": self.api.base_url,
            "auto_refresh": bool(self.auto_refresh.get()),
            "refresh_seconds": int(self.refresh_seconds.get()),
            "show_chat_activity": bool(self.show_chat_activity.get()),
            "show_technical": bool(self.show_technical.get()),
        })
        save_config(self.cfg)
        if not silent: self.status_var.set("Desktop settings saved")

    def _set_text(self, widget, value):
        widget.config(state="normal"); widget.delete("1.0","end"); widget.insert("end", str(value)); widget.config(state="disabled")

    def append_chat(self, speaker, text):
        self.chat_log.config(state="normal"); self.chat_log.insert("end", f"{speaker}: {text}\n\n"); self.chat_log.see("end"); self.chat_log.config(state="disabled")

    def run_async(self, fn, success=None, failure=None):
        def worker():
            try:
                result = fn()
                if success: self.after(0, lambda: success(result))
            except Exception as e:
                if failure: self.after(0, lambda: failure(e))
                else: self.after(0, lambda: messagebox.showerror("JANUS", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def check_health(self):
        self.run_async(self.api.health, lambda r: self.status_var.set("Global server online"), lambda e: self.status_var.set("Global server unavailable"))

    def send_chat(self):
        msg = self.message_entry.get("1.0", "end").strip()
        if not msg: return
        self.message_entry.delete("1.0", "end"); self.append_chat("You", msg); self.status_var.set("JANUS is thinking...")
        def ok(result):
            self.status_var.set("Global server online")
            reply = result.get("reply") or result.get("response") or result.get("message") or result.get("text") or result
            if isinstance(reply, (dict,list)): reply = json.dumps(reply, indent=2, ensure_ascii=False)
            self.append_chat("JANUS", reply)
        self.run_async(lambda: self.api.chat(self.profile_id, msg), ok, lambda e: (self.status_var.set("Request failed"), self.append_chat("System", str(e))))

    def refresh_page(self, key):
        self.status_var.set(f"Refreshing {key}...")
        self.run_async(lambda: self.api.get_screen(key, self.profile_id), lambda data: self._render_page(key, data), lambda e: self.status_var.set(f"{key.title()} unavailable: {e}"))

    def _render_page(self, key, data):
        self.status_var.set("Global server online")
        if key == "observe": self._render_observe(data)
        elif key == "cores": self._render_cores(data)
        elif key == "memory": self._render_memory(data)
        elif key == "activity": self._render_activity(data)
        elif key == "settings": self._render_settings(data)

    def _render_observe(self, data):
        counts = data.get("stored_rows_by_table", {}) if isinstance(data, dict) else {}
        cycle = data.get("background_cycle", {}) if isinstance(data, dict) else {}
        self.observe_status.set(f"JANUS online • background cycle {cycle.get('interval_minutes','?')} min • {sum(counts.values()) if counts else 0} stored profile records")
        # Pull actual recent notes from Activity so Observe shows readable process notes.
        self.run_async(lambda: self.api.get_screen("activity", self.profile_id), self._render_observe_notes, lambda e: None)

    def _render_observe_notes(self, data):
        rows = flatten_rows(data)
        self.observe_rows = rows
        for x in self.observe_tree.get_children(): self.observe_tree.delete(x)
        for i, r in enumerate(rows[:60]):
            when = r["when"].replace("T"," ")[:19]
            kind = r["kind"].replace("_"," ").title()
            self.observe_tree.insert("", "end", iid=str(i), values=(when, kind))
        if rows:
            self.observe_tree.selection_set("0"); self._open_observe_note()
        else:
            self._set_text(self.observe_detail, "No background/process notes have been recorded for this profile yet. New chat and JANUS events will appear here as they are created.")

    def _open_observe_note(self, event=None):
        sel = self.observe_tree.selection()
        if not sel: return
        r = self.observe_rows[int(sel[0])]
        body = f"{r['kind'].replace('_',' ').title()}\n{r['when']}\n\n{r['text']}"
        if self.show_technical.get(): body += "\n\nRaw record:\n" + json.dumps(r["raw"], indent=2, ensure_ascii=False)
        self._set_text(self.observe_detail, body)

    def _render_cores(self, data):
        for child in self.core_cards.winfo_children(): child.destroy()
        status = data.get("status", "unknown"); topology = data.get("topology", "7 → 3 → 1")
        runtime = data.get("runtime", {})
        self.cores_status.set(f"Status: {status.title()}   •   Topology: {topology}   •   Model: {runtime.get('model','unknown')}")
        seven = ttk.LabelFrame(self.core_cards, text="7 specialist lenses", style="Card.TLabelframe"); seven.pack(fill="x", pady=6)
        grid = ttk.Frame(seven); grid.pack(fill="x")
        for idx, role in enumerate(data.get("seven_roles", [])):
            ttk.Label(grid, text=role.replace("_"," ").title(), relief="groove", padding=(12,8), anchor="center").grid(row=idx//4, column=idx%4, padx=4, pady=4, sticky="ew")
        for c in range(4): grid.columnconfigure(c, weight=1)
        three = ttk.LabelFrame(self.core_cards, text="3 synthesis bridges", style="Card.TLabelframe"); three.pack(fill="x", pady=6)
        bridge_row = ttk.Frame(three); bridge_row.pack(fill="x")
        for idx, role in enumerate(data.get("three_bridges", [])):
            ttk.Label(bridge_row, text=role.title(), relief="groove", padding=(12,10), anchor="center").grid(row=0,column=idx,padx=5,sticky="ew")
            bridge_row.columnconfigure(idx, weight=1)
        one = ttk.LabelFrame(self.core_cards, text="1 integrator", style="Card.TLabelframe"); one.pack(fill="x", pady=6)
        ttk.Label(one, text=data.get("one_integrator", "JANUS integrated response"), font=("Segoe UI", 13, "bold"), anchor="center", padding=12).pack(fill="x")
        rt = ttk.LabelFrame(self.core_cards, text="Runtime", style="Card.TLabelframe"); rt.pack(fill="x", pady=6)
        bits = [f"External access: {'On' if runtime.get('external_access') else 'Off'}", f"Supervisor consultation: {'On' if runtime.get('supervisor_consultation') else 'Off'}", f"Compute: {runtime.get('compute_budget','balanced')}"]
        ttk.Label(rt, text="   •   ".join(bits)).pack(anchor="w")

    def _render_memory(self, data):
        rows = flatten_rows(data); self.memory_rows = rows
        for x in self.memory_tree.get_children(): self.memory_tree.delete(x)
        for i, r in enumerate(rows):
            raw = r["raw"]; level = raw.get("level", "trace"); role = raw.get("role", r["kind"])
            self.memory_tree.insert("","end",iid=str(i),values=(r["when"].replace("T"," ")[:19], level, role))
        if rows:
            self.memory_tree.selection_set("0"); self._open_memory()
        else: self._set_text(self.memory_detail, "No stored memory records for this profile yet.")

    def _open_memory(self, event=None):
        sel = self.memory_tree.selection()
        if not sel: return
        r = self.memory_rows[int(sel[0])]
        body = r["text"]
        if self.show_technical.get(): body += "\n\n" + json.dumps(r["raw"], indent=2, ensure_ascii=False)
        self._set_text(self.memory_detail, body)

    def _render_activity(self, data):
        rows = flatten_rows(data)
        if not self.show_chat_activity.get(): rows = [r for r in rows if r["kind"] not in ("chat_input","chat_output")]
        self.activity_rows = rows
        for x in self.activity_tree.get_children(): self.activity_tree.delete(x)
        for i, r in enumerate(rows):
            summary = r["text"].replace("\n"," ")[:120]
            self.activity_tree.insert("","end",iid=str(i),values=(r["when"].replace("T"," ")[:19], r["kind"].replace("_"," ").title(), summary))

    def _activity_popup(self, event=None):
        sel = self.activity_tree.selection()
        if not sel: return
        r = self.activity_rows[int(sel[0])]
        win = tk.Toplevel(self); win.title(r["kind"].replace("_"," ").title()); win.geometry("720x480")
        txt = tk.Text(win, wrap="word", font=("Segoe UI",11), padx=10, pady=10); txt.pack(fill="both", expand=True)
        txt.insert("end", f"{r['when']}\n\n{r['text']}")
        if self.show_technical.get(): txt.insert("end", "\n\nRaw record:\n" + json.dumps(r["raw"], indent=2, ensure_ascii=False))
        txt.config(state="disabled")

    def _render_settings(self, data):
        server = data.get("server", {}) if isinstance(data, dict) else {}
        self.server_settings_summary.set(
            f"Model: {server.get('model','?')}   •   Background interval: {server.get('interval_minutes','?')} min   •   "
            f"Memory processing: {'On' if server.get('memory_processing') else 'Off'}   •   Self-evaluation: {'On' if server.get('self_evaluation') else 'Off'}   •   "
            f"External access: {'On' if server.get('external_access') else 'Off'}"
        )

    def on_close(self):
        self._save_settings(silent=True)
        self.destroy()


if __name__ == "__main__":
    JanusClient().mainloop()
