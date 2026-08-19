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
        self.token = ""
        self.openapi = None

    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
            h["X-Access-Token"] = self.token
        return h

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
        for path, method in candidates:
            try:
                return self.request(method, path, payload if method != "GET" else None)
            except ApiError as e:
                last = e
        raise last or ApiError("No compatible server endpoint was found.")

    def register(self, username, password):
        payloads = [
            {"username": username, "password": password},
            {"name": username, "password": password},
        ]
        candidates = [("/auth/register", "POST"), ("/register", "POST"), ("/users/register", "POST")]
        candidates += self._discover(["register"], ("post",))
        last = None
        for payload in payloads:
            try:
                return self._try_candidates(candidates, payload)
            except ApiError as e:
                last = e
        raise last or ApiError("Registration failed.")

    def login(self, username, password):
        payloads = [
            {"username": username, "password": password},
            {"name": username, "password": password},
        ]
        candidates = [("/auth/login", "POST"), ("/login", "POST"), ("/users/login", "POST")]
        candidates += self._discover(["login"], ("post",))
        last = None
        for payload in payloads:
            try:
                result = self._try_candidates(candidates, payload)
                token = result.get("access_token") or result.get("token") or result.get("session_token")
                if token:
                    self.token = token
                return result
            except ApiError as e:
                last = e
        raise last or ApiError("Login failed.")

    def chat(self, username, message):
        payloads = [
            {"username": username, "message": message},
            {"user": username, "message": message},
            {"username": username, "text": message},
            {"message": message},
        ]
        candidates = [("/chat", "POST"), ("/conversation", "POST"), ("/message", "POST"), ("/talk", "POST")]
        candidates += self._discover(["chat", "message", "conversation"], ("post",))
        last = None
        for payload in payloads:
            try:
                return self._try_candidates(candidates, payload)
            except ApiError as e:
                last = e
        raise last or ApiError("Chat endpoint unavailable.")

    def get_screen(self, screen, username):
        known = {
            "observe": ["/observe", "/status", "/state"],
            "cores": ["/cores", "/core-status", "/architecture"],
            "memory": ["/memory", "/memories"],
            "activity": ["/activity", "/events", "/history"],
            "settings": ["/settings", "/preferences"],
            "account": ["/account", "/me", "/profile"],
        }
        candidates = [(p, "GET") for p in known.get(screen, [])]
        candidates += self._discover([screen], ("get",))
        last = None
        for p, m in candidates:
            for suffix in ("", f"?username={username}"):
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
        self.username = self.cfg.get("username", "")
        self.logged_in = False
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
        self.user_var = tk.StringVar(value="Not logged in")
        self._build_shell()
        self.after(150, self.check_health)
        self.after(350, self.show_login)

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
            ("Account", "account"),
        ]
        for label, key in nav_items:
            ttk.Button(self.nav, text=label, command=lambda k=key: self.show_page(k)).pack(fill="x", pady=3)
        ttk.Separator(self.nav).pack(fill="x", pady=10)
        ttk.Button(self.nav, text="Log in / Register", command=self.show_login).pack(fill="x", pady=3)
        ttk.Button(self.nav, text="Log out", command=self.logout).pack(fill="x", pady=3)

        self._build_chat_page()
        for key, title in [("observe", "Observe"), ("cores", "Cores"), ("memory", "Memory"), ("activity", "Activity"), ("settings", "Settings"), ("account", "Account")]:
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
        if key != "chat" and self.logged_in:
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

    def show_login(self):
        win = tk.Toplevel(self)
        win.title("JANUS Account")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=18)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="JANUS Account", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(frm, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        u = ttk.Entry(frm, width=34)
        u.grid(row=1, column=1, pady=5)
        u.insert(0, self.username)
        ttk.Label(frm, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        p = ttk.Entry(frm, width=34, show="*")
        p.grid(row=2, column=1, pady=5)
        msg = tk.StringVar(value="Use an existing account or create a new one.")
        ttk.Label(frm, textvariable=msg, wraplength=330).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 10))

        def perform(mode):
            username = u.get().strip()
            password = p.get()
            if not username or not password:
                msg.set("Enter both username and password.")
                return
            msg.set("Contacting JANUS global server...")
            action = self.api.login if mode == "login" else self.api.register

            def ok(result):
                if mode == "register":
                    msg.set("Account created. Logging in...")
                    self.run_async(lambda: self.api.login(username, password), lambda r: finish(r, username), lambda e: msg.set(str(e)))
                else:
                    finish(result, username)

            def finish(result, name):
                self.username = name
                self.logged_in = True
                self.user_var.set(f"Logged in: {name}")
                self.cfg["username"] = name
                self.cfg["server"] = self.api.base_url
                save_config(self.cfg)
                win.destroy()
                self.append_chat("JANUS", f"Connected as {name}. Ready.")
                self.show_page("chat")

            self.run_async(lambda: action(username, password), ok, lambda e: msg.set(str(e)))

        buttons = ttk.Frame(frm)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Log in", command=lambda: perform("login")).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(buttons, text="Create account", command=lambda: perform("register")).pack(side="left", fill="x", expand=True, padx=(4, 0))
        p.bind("<Return>", lambda e: perform("login"))
        u.focus_set()

    def logout(self):
        self.api.token = ""
        self.logged_in = False
        self.user_var.set("Not logged in")
        self.append_chat("JANUS", "Logged out locally.")
        self.show_login()

    def send_chat(self):
        if not self.logged_in:
            self.show_login()
            return
        msg = self.message_entry.get("1.0", "end").strip()
        if not msg:
            return
        self.message_entry.delete("1.0", "end")
        self.append_chat(self.username, msg)
        self.status_var.set("JANUS is thinking...")

        def ok(result):
            self.status_var.set("Global server online")
            reply = result.get("reply") or result.get("response") or result.get("message") or result.get("text") or result
            if isinstance(reply, (dict, list)):
                reply = json.dumps(reply, indent=2, ensure_ascii=False)
            self.append_chat("JANUS", reply)

        self.run_async(lambda: self.api.chat(self.username, msg), ok, lambda e: (self.status_var.set("Request failed"), self.append_chat("System", str(e))))

    def refresh_page(self, key):
        if not self.logged_in:
            self._set_text(self.pages[key].data_text, "Log in to view this screen.")
            return
        self._set_text(self.pages[key].data_text, "Loading...")
        self.run_async(
            lambda: self.api.get_screen(key, self.username),
            lambda r: self._set_text(self.pages[key].data_text, r),
            lambda e: self._set_text(self.pages[key].data_text, f"This screen is ready in the client, but the server did not expose a compatible endpoint yet.\n\n{e}"),
        )

    def on_close(self):
        self.cfg["username"] = self.username
        self.cfg["server"] = self.api.base_url
        save_config(self.cfg)
        self.destroy()


if __name__ == "__main__":
    JanusClient().mainloop()
