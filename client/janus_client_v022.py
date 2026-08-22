import base64
import ctypes
import os
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox

import janus_client_v021 as v021

APP_NAME = "JANUS - Global 7-2-1-1 v0.23"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf


def protect_session_token(token: str) -> str:
    """Protect a JANUS bearer token to the current Windows user using DPAPI."""
    if not token:
        return ""
    if os.name != "nt":
        return ""  # never persist a raw token on unsupported platforms
    try:
        in_blob, keep = _blob(token.encode("utf-8"))
        out_blob = DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        ok = crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "JANUS session",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if not ok:
            return ""
        try:
            raw = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return base64.b64encode(raw).decode("ascii")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return ""


def unprotect_session_token(value: str) -> str:
    if not value or os.name != "nt":
        return ""
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        in_blob, keep = _blob(raw)
        out_blob = DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if not ok:
            return ""
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData).decode("utf-8")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return ""


class AuthAPI(v021.API):
    def __init__(self, token=""):
        super().__init__()
        self.token = token or ""

    def call(self, method, path, payload=None, timeout=120):
        import json
        from urllib import request, error
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = request.Request(v021.base.SERVER + path, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                parsed = json.loads(body)
                detail = parsed.get("detail", parsed)
            except Exception:
                detail = body or str(e)
            raise RuntimeError(f"HTTP {e.code}: {detail}")

    def download(self, path, timeout=60):
        from urllib import request, error
        headers = {"Accept": "image/png,image/*;q=0.9,*/*;q=0.1"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = request.Request(v021.base.SERVER + path, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body or e.reason}")

    def login(self, identifier, password):
        return self.call("POST", "/auth/login", {"identifier": identifier, "password": password})

    def register(self, username, email, password):
        return self.call("POST", "/auth/register", {"username": username, "email": email, "password": password})

    def me(self):
        return self.call("GET", "/auth/me", timeout=30)

    def logout(self):
        return self.call("POST", "/auth/logout", {}, timeout=30)


v021.base.API = AuthAPI


class App(v021.App):
    def __init__(self):
        self._chat_image_refs = []
        super().__init__()
        self.title(APP_NAME)
        # Migrate any short-lived plaintext v0.22 development token once, then
        # remove it. Production persistence uses DPAPI ciphertext only.
        legacy = str(self.cfg.pop("access_token", "") or "")
        protected = str(self.cfg.get("session_protected") or "")
        restored = unprotect_session_token(protected)
        self.api.token = restored or legacy
        if legacy:
            encrypted = protect_session_token(legacy)
            if encrypted:
                self.cfg["session_protected"] = encrypted
            v021.base.save_cfg(self.cfg)
        if self.api.token:
            self.after(120, self.resume_saved_session)

    def _build_login(self):
        self.login = ttk.Frame(self, padding=40)
        self.login.pack(fill="both", expand=True)
        box = ttk.Frame(self.login, padding=30)
        box.place(relx=.5, rely=.45, anchor="center")
        ttk.Label(box, text="JANUS", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(box, text="Sign in to continue the same JANUS identity across devices.").pack(anchor="w", pady=(4, 16))

        self.identifier_var = tk.StringVar(value=self.cfg.get("login_identifier", ""))
        self.password_var = tk.StringVar()
        self.register_username_var = tk.StringVar(value=self.cfg.get("profile_id", ""))
        self.register_email_var = tk.StringVar(value=self.cfg.get("login_identifier", "") if "@" in str(self.cfg.get("login_identifier", "")) else "")
        self.register_password_var = tk.StringVar()

        tabs = ttk.Notebook(box)
        tabs.pack(fill="both", expand=True)

        sign = ttk.Frame(tabs, padding=10)
        tabs.add(sign, text="Sign in")
        ttk.Label(sign, text="Username or email").pack(anchor="w")
        ident = ttk.Entry(sign, textvariable=self.identifier_var, width=44)
        ident.pack(fill="x", pady=(2, 8))
        ttk.Label(sign, text="Password").pack(anchor="w")
        pw = ttk.Entry(sign, textvariable=self.password_var, show="•", width=44)
        pw.pack(fill="x", pady=(2, 10))
        pw.bind("<Return>", lambda e: self.sign_in())
        ttk.Button(sign, text="Sign in", command=self.sign_in).pack(fill="x")

        create = ttk.Frame(tabs, padding=10)
        tabs.add(create, text="Create account")
        ttk.Label(create, text="Username").pack(anchor="w")
        ttk.Entry(create, textvariable=self.register_username_var, width=44).pack(fill="x", pady=(2, 6))
        ttk.Label(create, text="Email").pack(anchor="w")
        ttk.Entry(create, textvariable=self.register_email_var, width=44).pack(fill="x", pady=(2, 6))
        ttk.Label(create, text="Password (12+ characters, including a letter and number)").pack(anchor="w")
        rp = ttk.Entry(create, textvariable=self.register_password_var, show="•", width=44)
        rp.pack(fill="x", pady=(2, 10))
        rp.bind("<Return>", lambda e: self.create_account())
        ttk.Button(create, text="Create account", command=self.create_account).pack(fill="x")

        self.login_status = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.login_status, wraplength=440).pack(anchor="w", pady=(12, 0))
        ident.focus_set()

    def _save_session(self, token: str):
        self.cfg.pop("access_token", None)
        protected = protect_session_token(token)
        if protected:
            self.cfg["session_protected"] = protected
        else:
            self.cfg.pop("session_protected", None)
        v021.base.save_cfg(self.cfg)

    def resume_saved_session(self):
        if not self.api.token or self.user:
            return
        self.login_status.set("Restoring saved session…")
        self.bg(self.api.me, self._auth_success)

    def sign_in(self):
        identifier = self.identifier_var.get().strip()
        password = self.password_var.get()
        if not identifier or not password:
            self.login_status.set("Enter your username/email and password.")
            return
        self.login_status.set("Signing in…")
        self.bg(lambda: self.api.login(identifier, password), self._auth_success)

    def create_account(self):
        username = self.register_username_var.get().strip()
        email = self.register_email_var.get().strip()
        password = self.register_password_var.get()
        if not username or not email or not password:
            self.login_status.set("Username, email and password are required.")
            return
        self.login_status.set("Creating account…")
        self.bg(lambda: self.api.register(username, email, password), self._auth_success)

    def _auth_success(self, result):
        token = str(result.get("access_token") or self.api.token or "")
        account = result.get("account") or {}
        username = str(account.get("username") or "").strip()
        if not token or not username:
            self.api.token = ""
            self.cfg.pop("session_protected", None)
            v021.base.save_cfg(self.cfg)
            self.login_status.set("Saved session is no longer valid. Please sign in again.")
            return
        self.api.token = token
        self.user = username
        self.cfg.update(
            profile_id=username,
            login_identifier=str(account.get("email") or username),
        )
        self._save_session(token)
        self.password_var.set("")
        self.register_password_var.set("")
        if hasattr(self, "login") and self.login.winfo_exists():
            self.login.destroy()
        self._build_main()
        self.show("chat")
        self.health()
        self.refresh("messages")
        self.refresh("options")
        if result.get("verification_required"):
            messagebox.showinfo("JANUS", "Account created/signed in. Email verification is still required when mail delivery is configured.")

    def enter_profile(self):
        self.sign_in()

    def switch_profile(self):
        self.logout_account()

    def logout_account(self):
        if self.api.token:
            try:
                self.api.logout()
            except Exception:
                pass
        self.api.token = ""
        self.user = ""
        self._chat_image_refs = []
        self.cfg.pop("session_protected", None)
        self.cfg.pop("access_token", None)
        v021.base.save_cfg(self.cfg)
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

    def _build_main(self):
        super()._build_main()
        settings = self.pages.get("settings")
        if settings is not None:
            ttk.Separator(settings).pack(fill="x", pady=12)
            ttk.Button(settings, text="Sign out of JANUS", command=self.logout_account).pack(anchor="w")

    def chat_done(self, result):
        self.say("JANUS", result.get("reply", result.get("response", "")))
        generated = result.get("generated_image") or {}
        path = str(generated.get("download_path") or "").strip() if isinstance(generated, dict) else ""
        self.status.set("Active")
        self.refresh("messages")
        if path:
            self.status.set("Fetching JANUS image")
            self.bg(lambda: self.api.download(path), self._image_done)

    def _image_done(self, data):
        try:
            encoded = base64.b64encode(data).decode("ascii")
            image = tk.PhotoImage(data=encoded, format="png")
            # Keep a Python reference for as long as the transcript is alive;
            # Tk images disappear when their PhotoImage object is collected.
            self._chat_image_refs.append(image)
            self.chat.config(state="normal")
            self.chat.image_create("end", image=image)
            self.chat.insert("end", "\n\n")
            self.chat.config(state="disabled")
            self.chat.see("end")
            self.status.set("Active")
        except Exception as exc:
            self.say("System", f"JANUS generated an image, but Windows could not display it: {exc}")
            self.status.set("Active")


if __name__ == "__main__":
    App().mainloop()
