from __future__ import annotations

import os
import re
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from . import storage

ph = PasswordHasher()
GOOGLE_CLIENT_ID = os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")


def public_account(row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "email": str(row["email"]),
        "email_verified": bool(row["email_verified"]),
        "google_linked": bool(row["google_sub"]),
        "created_at": int(row["created_at"]),
    }


def hash_password(password: str) -> str:
    validate_password(password)
    return ph.hash(password)


def verify_password(encoded: str | None, password: str) -> bool:
    if not encoded:
        return False
    try:
        return bool(ph.verify(encoded, password))
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def validate_password(password: str) -> None:
    if len(password or "") < 12 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(400, "Password must be at least 12 characters and contain a letter and number")


def validate_username(username: str) -> str:
    value = (username or "").strip()
    if not USERNAME_RE.fullmatch(value):
        raise HTTPException(400, "Username must be 3-40 characters using letters, numbers, dot, dash or underscore")
    return value


def bearer(authorization: str | None) -> str:
    raw = (authorization or "").strip()
    return raw[7:].strip() if raw.lower().startswith("bearer ") else ""


def require_account(authorization: str | None = Header(default=None)):
    account = storage.account_for_session(bearer(authorization))
    if not account:
        raise HTTPException(401, "Valid JANUS session required")
    return account


def login(identifier: str, password: str) -> tuple[Any, str]:
    row = storage.account_by_identifier(identifier)
    if not row or not verify_password(row["password_hash"], password):
        raise HTTPException(401, "Invalid username/email or password")
    return row, storage.new_session(int(row["id"]))


def register(username: str, email: str, password: str) -> tuple[Any, str, str]:
    username = validate_username(username)
    email = (email or "").strip().lower()
    if "@" not in email or len(email) > 254:
        raise HTTPException(400, "Valid email required")
    if storage.account_by_identifier(username) or storage.account_by_identifier(email):
        raise HTTPException(409, "Username or email already exists")
    row = storage.create_account(username, email, hash_password(password))
    verify_token = storage.issue_auth_token(int(row["id"]), "verify_email", 86400)
    return row, storage.new_session(int(row["id"])), verify_token


def google_login(id_token_text: str) -> tuple[Any, str]:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google sign-in is not configured on the JANUS server")
    try:
        info = google_id_token.verify_oauth2_token(id_token_text, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as exc:
        raise HTTPException(401, f"Google identity token rejected: {type(exc).__name__}")
    sub = str(info.get("sub") or "").strip()
    email = str(info.get("email") or "").strip().lower()
    verified = bool(info.get("email_verified"))
    if not sub or not email:
        raise HTTPException(401, "Google identity token did not contain a usable account")
    with storage.db() as c:
        row = c.execute("SELECT * FROM v2_accounts WHERE google_sub=? OR lower(email)=lower(?) LIMIT 1", (sub, email)).fetchone()
    if row:
        if not row["google_sub"]:
            row = storage.update_account(int(row["id"]), google_sub=sub, email_verified=int(verified or bool(row["email_verified"])))
    else:
        base = re.sub(r"[^A-Za-z0-9_.-]+", "", email.split("@", 1)[0])[:28] or "janus-user"
        candidate = base
        n = 2
        while storage.account_by_identifier(candidate):
            candidate = f"{base[:24]}-{n}"
            n += 1
        row = storage.create_account(candidate, email, None, sub, verified)
    return row, storage.new_session(int(row["id"]))
