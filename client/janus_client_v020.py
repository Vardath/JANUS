import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib import request, error, parse

APP_NAME = "JANUS - Global 7-3-1 v0.20"
SERVER = "https://janus-global-core.onrender.com"
CFG = os.path.join(os.path.expanduser("~"), ".janus", "client.json")


class API:
    def call(self, method, path, payload=None, timeout=120):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(SERVER + path, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"}, method=method)
        try:
            with request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except error.HTTPError as e:
            raise RuntimeError(e.read().decode(errors="replace") or str(e))

    def get(self, screen, user):
        return self.call("GET", "/desktop/" + screen + "?" + parse.urlencode({"username": user}), timeout=30)


def load_cfg():
    try:
        with open(CFG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(data):
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.api = API()
        self.cfg = load_cfg()
        self.user = ""
        self.pages = {}
        self.rows = {}
        self.timer = None
        self.auto = tk.BooleanVar(value=self.cfg.get("auto_refresh", True))
        self.seconds = tk.IntVar(value=int(self.cfg.get("refresh_seconds", 10)))
        self.status = tk.StringVar(value="Dormant")
        self.unread = tk.StringVar(value="0")
        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(940, 620)
        self._build_login()

    def _build_login(self):
        self.login = ttk.Frame(self, padding=40)
        self.login.pack(fill="both", expand=True)
        box = ttk.Frame(self.login, padding=30)
        box.place(relx=.5, rely=.45, anchor="center")
        ttk.Label(box, text="JANUS", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(box, text="Choose the JANUS profile this computer should continue.").pack(anchor="w", pady=(4, 16))
        profiles = self.cfg.get("profiles", [])
        last = self.cfg.get("profile_id", "")
        self.profile_var = tk.StringVar(value=last)
        self.profile_combo = ttk.Combobox(box, textvariable=self.profile_var, values=profiles, width=42)
        self.profile_combo.pack(fill="x", pady=4)
        self.profile_combo.bind("<Return>", lambda e: self.enter_profile())
        ttk.Button(box, text="Continue", command=self.enter_profile).pack(fill="x", pady=(10, 4))
        ttk.Label(box, text="Use the same profile on Windows and Android to share one persistent JANUS conversation, memory and message outbox.", wraplength=420).pack(anchor="w", pady=(12, 0))
        self.profile_combo.focus_set()

    def enter_profile(self):
        user = self.profile_var.get().strip()
        if not user:
            return
        self.user = user
        profiles = list(dict.fromkeys([*self.cfg.get("profiles", []), user]))
        self.cfg.update(profile_id=user, profiles=profiles)
        save_cfg(self.cfg)
        self.login.destroy()
        self._build_main()
        self.show("chat")
        self.health()
        self.refresh("messages")
        self.refresh("options")

    def _build_main(self):
        top = ttk.Frame(self, padding=(12, 8))
        top.pack(fill="x")
        ttk.Label(top, text="JANUS", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(top, text="Global 7→3→1").pack(side="left", padx=8)
        ttk.Label(top, text=f"Profile: {self.user}").pack(side="right", padx=(12, 0))
        ttk.Label(top, textvariable=self.status).pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        nav = ttk.Frame(body, padding=8, width=190)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        self.content = ttk.Frame(body, padding=12)
        self.content.pack(side="left", fill="both", expand=True)

        ttk.Label(nav, text="PRIMARY", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 4))
        for label, key in [("Chat", "chat"), ("Messages", "messages"), ("Observe Thoughts", "observe"), ("Options", "options")]:
            ttk.Button(nav, text=label, command=lambda k=key: self.show(k)).pack(fill="x", pady=3)
        self.nav_badge = ttk.Label(nav, textvariable=self.unread)
        self.nav_badge.pack(anchor="e", padx=8)
        ttk.Separator(nav).pack(fill="x", pady=12)
        ttk.Label(nav, text="OPTIONS", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        for label, key in [("Cores", "cores"), ("Memory", "memory"), ("Activity", "activity"), ("Settings", "settings")]:
            ttk.Button(nav, text=label, command=lambda k=key: self.show(k)).pack(fill="x", pady=3)
        ttk.Separator(nav).pack(fill="x", pady=12)
        ttk.Button(nav, text="Switch profile", command=self.switch_profile).pack(fill="x", pady=3)

        self.build_chat()
        self.build_list("messages", "Messages", "JANUS's outbox: questions, observations, memories and follow-ups.")
        self.build_list("observe", "Observe Thoughts", "Externalizable process notes, not hidden chain-of-thought.")
        self.build_options()
        self.build_cores()
        self.build_list("memory", "Memory", "Trace → working → episodic → core")
        self.build_list("activity", "Activity", "Conversation, reflections, decisions and system events")
        self.build_settings()

    def switch_profile(self):
        self.cfg["profile_id"] = self.user
        save_cfg(self.cfg)
        for child in self.winfo_children():
            child.destroy()
        self.pages = {}
        self.rows = {}
        if self.timer:
            try:
                self.after_cancel(self.timer)
            except Exception:
                pass
        self.timer = None
        self._build_login()

    def page(self, key):
        frame = ttk.Frame(self.content)
        self.pages[key] = frame
        return frame

    def head(self, page, title, subtitle=""):
        ttk.Label(page, text=title, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        if subtitle:
            ttk.Label(page, text=subtitle).pack(anchor="w", pady=(0, 10))

    def build_chat(self):
        p = self.page("chat")
        self.head(p, "Chat", "Enter sends • Shift+Enter adds a line")
        self.chat = tk.Text(p, state="disabled", wrap="word", font=("Segoe UI", 11), padx=8, pady=8)
        self.chat.pack(fill="both", expand=True)
        row = ttk.Frame(p)
        row.pack(fill="x", pady=8)
        self.entry = tk.Text(row, height=4, wrap="word", font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.enter_key)
        self.entry.bind("<Shift-Return>", self.shift_enter)
        ttk.Button(row, text="Send", command=self.send).pack(side="left", fill="y", padx=8)
        self.say("JANUS", "Connected. Ready.")

    def build_list(self, key, title, subtitle):
        p = self.page(key)
        self.head(p, title, subtitle)
        tree = ttk.Treeview(p, columns=("time", "type", "summary"), show="headings")
        for col, width in [("time", 150), ("type", 170), ("summary", 600)]:
            tree.heading(col, text=col.title())
            tree.column(col, width=width, stretch=col == "summary")
        tree.pack(fill="both", expand=True)
        tree.bind("<Double-1>", lambda e, k=key: self.detail(k))
        self.rows[key] = []
        setattr(self, key + "_tree", tree)
        if key == "messages":
            bar = ttk.Frame(p)
            bar.pack(fill="x", pady=6)
            ttk.Button(bar, text="Answer in Chat", command=self.answer_in_chat).pack(side="left")
            ttk.Button(bar, text="Mark read", command=lambda: self.message_state("read")).pack(side="left", padx=6)
            ttk.Button(bar, text="Dismiss", command=lambda: self.message_state("dismissed")).pack(side="left")

    def build_options(self):
        p = self.page("options")
        self.head(p, "Options", "Persistent JANUS status and controls")
        self.options_text = tk.Text(p, height=12, state="disabled", wrap="word", font=("Segoe UI", 11), padx=8, pady=8)
        self.options_text.pack(fill="x", pady=(0, 12))
        grid = ttk.Frame(p)
        grid.pack(fill="x")
        for i, (label, key, desc) in enumerate([
            ("Cores", "cores", "7 lenses, 3 bridges, 1 integrator"),
            ("Memory", "memory", "Promotion ladder and continuity records"),
            ("Activity", "activity", "Reflections, decisions and system events"),
            ("Settings", "settings", "Refresh and display controls"),
        ]):
            box = ttk.LabelFrame(grid, text=label, padding=10)
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
            ttk.Label(box, text=desc, wraplength=300).pack(anchor="w")
            ttk.Button(box, text="Open", command=lambda k=key: self.show(k)).pack(anchor="w", pady=(8, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def build_cores(self):
        p = self.page("cores")
        self.head(p, "Cores", "7 specialist lenses → 3 synthesis bridges → 1 JANUS voice")
        self.cores = tk.Text(p, state="disabled", wrap="word", font=("Segoe UI", 11), padx=8, pady=8)
        self.cores.pack(fill="both", expand=True)

    def build_settings(self):
        p = self.page("settings")
        self.head(p, "Settings", "Desktop display and live updates")
        ttk.Checkbutton(p, text="Auto refresh current live screen", variable=self.auto, command=self.save).pack(anchor="w", pady=8)
        row = ttk.Frame(p)
        row.pack(anchor="w")
        ttk.Label(row, text="Refresh interval").pack(side="left")
        for n in (5, 10, 15, 30, 60):
            ttk.Radiobutton(row, text=f"{n}s", value=n, variable=self.seconds, command=self.save).pack(side="left", padx=4)
        self.settings_text = tk.Text(p, height=14, state="disabled", wrap="word")
        self.settings_text.pack(fill="x", pady=12)

    def settext(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.config(state="disabled")

    def say(self, who, text):
        self.chat.config(state="normal")
        self.chat.insert("end", f"{who}\n{text}\n\n")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def enter_key(self, event=None):
        self.send()
        return "break"

    def shift_enter(self, event=None):
        self.entry.insert("insert", "\n")
        return "break"

    def send(self):
        message = self.entry.get("1.0", "end").strip()
        if not message:
            return
        self.entry.delete("1.0", "end")
        self.say("You", message)
        self.status.set("Processing")
        self.bg(lambda: self.api.call("POST", "/desktop/chat", {"profile_id": self.user, "message": message}), self.chat_done)

    def chat_done(self, result):
        self.say("JANUS", result.get("reply", ""))
        self.status.set("Active")
        self.refresh("messages")

    def show(self, key):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        if key != "chat":
            self.refresh(key)
        self.schedule(key)

    def refresh(self, key):
        if not self.user:
            return
        self.status.set("Syncing")
        if key == "options":
            return self.bg(lambda: self.api.get("home", self.user), self.render_options)
        if key == "cores":
            return self.bg(lambda: self.api.get("cores", self.user), self.render_cores)
        if key == "settings":
            return self.bg(lambda: self.api.get("settings", self.user), self.render_settings)
        self.bg(lambda: self.api.get(key, self.user), lambda r: self.render_list(key, r))

    def render_options(self, result):
        latest = result.get("latest_activity") or {}
        self.settext(self.options_text, f"Status: {result.get('status', 'Active')}\nProfile: {self.user}\nArchitecture: {result.get('architecture', '7 → 3 → 1')}\nBackground cycle: {result.get('background_interval_minutes', '?')} minutes\nUnread JANUS messages: {result.get('unread_messages', 0)}\n\nLatest activity:\n{latest.get('detail', 'No activity yet.')}")
        self.unread.set(str(result.get("unread_messages", 0)))
        self.status.set(result.get("status", "Active"))

    def render_list(self, key, result):
        tree = getattr(self, key + "_tree")
        tree.delete(*tree.get_children())
        items = result.get("items", result.get("notes", []))
        self.rows[key] = items
        for i, item in enumerate(items):
            if key == "messages":
                typ = item.get("message_type", "Follow-up")
                if item.get("state") == "unread":
                    typ = "NEW · " + typ
            else:
                typ = item.get("event_type") or item.get("role") or "item"
            text = item.get("detail") or item.get("content") or ""
            tree.insert("", "end", iid=str(i), values=(item.get("created_at", "")[:19].replace("T", " "), typ, text.replace("\n", " ")[:180]))
        if key == "messages":
            self.unread.set(str(result.get("unread", 0)))
        self.status.set("Active")

    def render_cores(self, result):
        text = "1 INTEGRATOR\n" + (result.get("one_integrator") or {}).get("description", "")
        text += "\n\n3 BRIDGES\n" + "".join(f"• {k}: {v}\n" for k, v in (result.get("three_bridges") or {}).items())
        text += "\n7 LENSES\n" + "".join(f"• {k}: {v}\n" for k, v in (result.get("seven_roles") or {}).items())
        self.settext(self.cores, text)
        self.status.set("Active")

    def render_settings(self, result):
        s = result.get("server", {})
        self.settext(self.settings_text, "Global background core\n" + f"Model: {s.get('model', '?')}\nBackground worker: {s.get('background_worker')}\nInterval: {s.get('interval_minutes')} min\nMemory processing: {s.get('memory_processing')}\nSelf evaluation: {s.get('self_evaluation')}\nMessage queue: {s.get('message_queue')}\nExternal access: {s.get('external_access')}")
        self.status.set("Active")

    def detail(self, key):
        selection = getattr(self, key + "_tree").selection()
        if selection:
            item = self.rows[key][int(selection[0])]
            messagebox.showinfo(key.title(), item.get("detail") or item.get("content") or json.dumps(item, indent=2))

    def selected_message(self):
        selection = self.messages_tree.selection()
        return self.rows["messages"][int(selection[0])] if selection else None

    def answer_in_chat(self):
        item = self.selected_message()
        if not item:
            return
        self.message_state("read", item)
        stamp = item.get("created_at", "")[:19].replace("T", " ")
        prompt = f"Regarding your {item.get('message_type', 'message')} from {stamp}:\n\"{(item.get('detail') or '')[:500]}\"\n\n"
        self.show("chat")
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", prompt)
        self.entry.focus_set()

    def message_state(self, state, item=None):
        item = item or self.selected_message()
        if not item:
            return
        self.bg(lambda: self.api.call("POST", f"/desktop/messages/{item['id']}/state", {"profile_id": self.user, "state": state}), lambda r: self.refresh("messages"))

    def save(self):
        self.cfg.update(profile_id=self.user, auto_refresh=self.auto.get(), refresh_seconds=self.seconds.get())
        save_cfg(self.cfg)
        active = next((k for k, p in self.pages.items() if p.winfo_ismapped()), "chat")
        self.schedule(active)

    def schedule(self, key):
        if self.timer:
            try:
                self.after_cancel(self.timer)
            except Exception:
                pass
        self.timer = None
        if self.auto.get():
            target = key if key in ("messages", "observe", "options", "memory", "activity") else "messages"
            self.timer = self.after(max(5, self.seconds.get()) * 1000, lambda: (self.refresh(target), self.schedule(key)))

    def bg(self, fn, done):
        def run():
            try:
                result = fn()
                self.after(0, lambda: done(result))
            except Exception as exc:
                self.after(0, lambda err=str(exc): self.status.set("Dormant · " + err[:70]))
        threading.Thread(target=run, daemon=True).start()

    def health(self):
        self.bg(lambda: self.api.call("GET", "/health", timeout=15), lambda r: self.status.set("Active"))


if __name__ == "__main__":
    App().mainloop()
