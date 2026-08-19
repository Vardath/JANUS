import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib import request, error, parse

APP_NAME = "JANUS - Global 7-3-1 v0.12"
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
        return self.request(
            "POST",
            "/desktop/chat",
            {"profile_id": profile_id, "message": message},
            timeout=120,
        )

    def get_screen(self, screen, profile_id):
        if screen not in {"observe", "cores", "memory", "activity", "settings"}:
            raise ApiError(f"Unknown screen: {screen}")
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


class JanusClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.api = JanusAPI(self.cfg.get("server", DEFAULT_SERVER))

        # No JANUS username/password gate. This is an internal continuity key
        # until Google Play / Apple platform identity is connected later.
        self.profile_id = (
            self.cfg.get("profile_id")
            or self.cfg.get("username")
            or os.environ.get("USERNAME")
            or os.environ.get("USER")
            or "local-user"
        )
        self.cfg["profile_id"] = self.profile_id
        self.cfg.pop("username", None)

        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(900, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except Exception:
            pass

        self.status_var = tk.StringVar(value="Checking global server...")
        self.user_var = tk.StringVar(value=f"Local profile: {self.profile_id}")
        self._build_shell()
        self.after(150, self.check_health)
        self.after(350, lambda: self.append_chat("JANUS", "Connected. Ready."))

    def _build_shell(self):
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="JANUS", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="Global 7-3-1", font=("Segoe UI", 11)).pack(side="left", padx=(8, 0))
        ttk.Label(top, textvariable=self.user_var).pack(side="right")
        ttk.Label(top, textvariable=self.status_var).pack(side="right", padx=(0, 20))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self.nav = ttk.Frame(body, padding=(8, 10), width=165)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)

        self.content = ttk.Frame(body, padding=(10, 8))
        self.content.pack(side="left", fill="both", expand=True)

        self.pages = {}
        nav_items = [
            ("Chat", "chat"),
            ("Observe", "observe"),
            ("Cores", "cores"),
            ("Memory", "memory"),
            ("Activity", "activity"),
            ("Settings", "settings"),
        ]
        for label, key in nav_items:
            ttk.Button(
                self.nav,
                text=label,
                command=lambda k=key: self.show_page(k),
            ).pack(fill="x", pady=3)

        ttk.Separator(self.nav).pack(fill="x", pady=10)
        ttk.Label(
            self.nav,
            text="Sign-in will be handled by the app store/platform.",
            wraplength=145,
            justify="left",
        ).pack(fill="x", pady=4)

        self._build_chat_page()
        for key, title in [
            ("observe", "Observe"),
            ("cores", "Cores"),
            ("memory", "Memory"),
            ("activity", "Activity"),
            ("settings", "Settings"),
        ]:
            self._build_data_page(key, title)
        self.show_page("chat")

    def _new_page(self, key):
        f = ttk.Frame(self.content)
        self.pages[key] = f
        return f

    def _build_chat_page(self):
        page = self._new_page("chat")
        ttk.Label(page, text="Conversation", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 8))
        self.chat_log = tk.Text(page, wrap="word", state="disabled", font=("Segoe UI", 11))
        self.chat_log.pack(fill="both", expand=True)
        bottom = ttk.Frame(page)
        bottom.pack(fill="x", pady=(8, 0))
        self.message_entry = tk.Text(bottom, height=4, wrap="word", font=("Segoe UI", 11))
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Control-Return>", lambda e: self.send_chat())
        ttk.Button(bottom, text="Send", command=self.send_chat).pack(side="left", padx=(8, 0), fill="y")

    def _build_data_page(self, key, title):
        page = self._new_page(key)
        header = ttk.Frame(page)
        header.pack(fill="x")
        ttk.Label(header, text=title, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Refresh", command=lambda k=key: self.refresh_page(k)).pack(side="right")
        text = tk.Text(page, wrap="word", state="disabled", font=("Consolas", 10))
        text.pack(fill="both", expand=True, pady=(8, 0))
        page.data_text = text

    def show_page(self, key):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        if key != "chat":
            self.refresh_page(key)

    def _set_text(self, widget, value):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        if isinstance(value, (dict, list)):
            widget.insert("end", json.dumps(value, indent=2, ensure_ascii=False))
        else:
            widget.insert("end", str(value))
        widget.config(state="disabled")

    def append_chat(self, speaker, text):
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", f"{speaker}: {text}\n\n")
        self.chat_log.see("end")
        self.chat_log.config(state="disabled")

    def run_async(self, fn, success=None, failure=None):
        def worker():
            try:
                result = fn()
                if success:
                    self.after(0, lambda: success(result))
            except Exception as e:
                if failure:
                    self.after(0, lambda: failure(e))
                else:
                    self.after(0, lambda: messagebox.showerror("JANUS", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def check_health(self):
        self.run_async(
            self.api.health,
            lambda r: self.status_var.set("Global server online"),
            lambda e: self.status_var.set("Global server unavailable"),
        )

    def send_chat(self):
        msg = self.message_entry.get("1.0", "end").strip()
        if not msg:
            return
        self.message_entry.delete("1.0", "end")
        self.append_chat("You", msg)
        self.status_var.set("JANUS is thinking...")

        def ok(result):
            self.status_var.set("Global server online")
            reply = result.get("reply") or result.get("response") or result.get("message") or result.get("text") or result
            if isinstance(reply, (dict, list)):
                reply = json.dumps(reply, indent=2, ensure_ascii=False)
            self.append_chat("JANUS", reply)

        self.run_async(
            lambda: self.api.chat(self.profile_id, msg),
            ok,
            lambda e: (
                self.status_var.set("Request failed"),
                self.append_chat("System", str(e)),
            ),
        )

    def refresh_page(self, key):
        self._set_text(self.pages[key].data_text, "Loading...")
        self.run_async(
            lambda: self.api.get_screen(key, self.profile_id),
            lambda r: self._set_text(self.pages[key].data_text, r),
            lambda e: self._set_text(
                self.pages[key].data_text,
                f"JANUS server request failed.\n\n{e}",
            ),
        )

    def on_close(self):
        self.cfg["profile_id"] = self.profile_id
        self.cfg["server"] = self.api.base_url
        self.cfg.pop("username", None)
        save_config(self.cfg)
        self.destroy()


if __name__ == "__main__":
    JanusClient().mainloop()
