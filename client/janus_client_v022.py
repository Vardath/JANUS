import tkinter as tk
from tkinter import ttk, messagebox

import janus_client_v021 as v021

APP_NAME = "JANUS - Global 7-2-1-1 v0.22"


class AuthAPI(v021.API):
    def __init__(self, token=""):
        super().__init__()
        self.token = token or ""

    def call(self, method, path, payload=None, timeout=120):
        # v0.20's API.call has no auth header support, so reproduce its tiny
        # transport here while preserving the same return/error behavior.
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

    def login(self, identifier, password):
        return self.call("POST", "/auth/login", {"identifier": identifier, "password": password})

    def register(self, username, email, password):
        return self.call("POST", "/auth/register", {"username": username, "email": email, "password": password})

    def me(self):
        return self.call("GET", "/auth/me", timeout=30)

    def logout(self):
        return self.call("POST", "/auth/logout", {}, timeout=30)


# v0.21 ultimately instantiates base.API inside the inherited constructor.
v021.base.API = AuthAPI


class App(v021.App):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.api.token = str(self.cfg.get("access_token") or "")
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
        # /auth/me returns only account; login/register also return access_token.
        token = str(result.get("access_token") or self.api.token or "")
        account = result.get("account") or {}
        username = str(account.get("username") or "").strip()
        if not token or not username:
            self.api.token = ""
            self.cfg.pop("access_token", None)
            v021.base.save_cfg(self.cfg)
            self.login_status.set("Saved session is no longer valid. Please sign in again.")
            return
        self.api.token = token
        self.user = username
        self.cfg.update(
            access_token=token,
            profile_id=username,
            login_identifier=str(account.get("email") or username),
        )
        v021.base.save_cfg(self.cfg)
        if hasattr(self, "login") and self.login.winfo_exists():
            self.login.destroy()
        self._build_main()
        self.show("chat")
        self.health()
        self.refresh("messages")
        self.refresh("options")
        if result.get("verification_required"):
            messagebox.showinfo("JANUS", "Account created/signed in. Email verification is still required when mail delivery is configured.")

    # Legacy profile selection must not bypass authenticated account identity.
    def enter_profile(self):
        self.sign_in()

    def switch_profile(self):
        self.logout_account()

    def logout_account(self):
        token_present = bool(self.api.token)
        if token_present:
            try:
                self.api.logout()
            except Exception:
                pass
        self.api.token = ""
        self.user = ""
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
        # Replace the legacy 'Switch profile' meaning with an authenticated logout.
        # A compact account action is also exposed in Settings for clarity.
        settings = self.pages.get("settings")
        if settings is not None:
            ttk.Separator(settings).pack(fill="x", pady=12)
            ttk.Button(settings, text="Sign out of JANUS", command=self.logout_account).pack(anchor="w")


if __name__ == "__main__":
    App().mainloop()
