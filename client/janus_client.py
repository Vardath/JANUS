import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib import request, error

APP_NAME = "JANUS - Global 7-3-1"
DEFAULT_SERVER = "https://janus-global-core.onrender.com"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".janus")
CONFIG_FILE = os.path.join(CONFIG_DIR, "client.json")


class ApiError(Exception):
    pass


class JanusAPI:
    def __init__(self, base_url=DEFAULT_SERVER):
        self.base_url = base_url.rstrip("/")
        self.openapi = None

    def _headers(self):
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def request(self, method, path, payload=None, timeout=45):
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

    def load_openapi(self):
        try:
            self.openapi = self.request("GET", "/openapi.json", timeout=15)
        except Exception:
            self.openapi = {}
        return self.openapi

    def _discover(self, words, methods=("post", "get")):
        if self.openapi is None:
            self.load_openapi()
        paths = (self.openapi or {}).get("paths", {})
        scored = []
        for path, ops in paths.items():
            text = (path + " " + json.dumps(ops)).lower()
            score = sum(1 for w in words if w.lower() in text)
            if score:
                for m in methods:
                    if m in ops:
                        scored.append((score, path, m.upper()))
        scored.sort(reverse=True)
        return [(p, m) for _, p, m in scored]

    def _try_candidates(self, candidates, payload=None):
        last = None
        seen = set()
        for path, method in candidates:
            key = (path, method)
            if key in seen:
                continue
            seen.add(key)
            try:
                return self.request(method, path, payload if method != "GET" else None)
            except ApiError as e:
                last = e
        raise last or ApiError("No compatible server endpoint was found.")

    def chat(self, profile_id, message):
        # Store login is intentionally not used here. profile_id is only a
        # continuity key for the JANUS server until Play/App Store identity is added.
        payloads = [
            {"username": profile_id, "message": message},
            {"user": profile_id, "message": message},
            {"username": profile_id, "text": message},
            {"message": message},
        ]
        candidates = [
            ("/chat", "POST"),
            ("/conversation", "POST"),
            ("/message", "POST"),
            ("/talk", "POST"),
        ]
        candidates += self._discover(["chat", "message", "conversation"], ("post",))
        last = None
        for payload in payloads:
            try:
                return self._try_candidates(candidates, payload)
            except ApiError as e:
                last = e
        raise last or ApiError("Chat endpoint unavailable.")

    def get_screen(self, screen, profile_id):
        known = {
            "observe": ["/observe", "/status", "/state"],
            "cores": ["/cores", "/core-status", "/architecture"],
            "memory": ["/memory", "/memories"],
            "activity": ["/activity", "/events", "/history"],
            "settings": ["/settings", "/preferences"],
        }
        candidates = [(p, "GET") for p in known.get(screen, [])]
        candidates += self._discover([screen], ("get",))
        last = None
        for p, m in candidates:
            for suffix in (f"?username={profile_id}", ""):
                try:
                    return self.request(m, p + suffix)
                except ApiError as e:
                    last = e
        raise last or ApiError(f"No {screen} endpoint is exposed by the server yet.")


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

        # No JANUS username/password gate. Keep the old username value only as
        # an internal continuity key so existing server-side memories still map
        # to the same user. Store/platform identity can replace this later.
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
                "This screen is ready in the client, but the server did not expose "
                f"a compatible endpoint yet.\n\n{e}",
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
