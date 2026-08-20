import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(prefix="/auth", tags=["auth"])
DB_PATH = Path(os.getenv("JANUS_AUTH_DB") or os.getenv("JANUS_DB_PATH") or "janus_auth.db")
GOOGLE_CLIENT_ID = os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()
SESSION_TTL = 60 * 60 * 24 * 30
PBKDF2_ITERATIONS = 600_000


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _has_column(c: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in c.execute(f"PRAGMA table_info({table})"))


def init_auth_db():
    with _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                disabled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);
            """
        )
        if not _has_column(c, "accounts", "google_sub"):
            c.execute("ALTER TABLE accounts ADD COLUMN google_sub TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_google_sub ON accounts(google_sub) WHERE google_sub IS NOT NULL")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        alg, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_session(c: sqlite3.Connection, account_id: int) -> str:
    token = secrets.token_urlsafe(48)
    now = int(time.time())
    c.execute(
        "INSERT INTO sessions(token_hash, account_id, created_at, expires_at) VALUES(?,?,?,?)",
        (_token_hash(token), account_id, now, now + SESSION_TTL),
    )
    return token


def _unique_username(c: sqlite3.Connection, email: str, display_name: str = "") -> str:
    base = (display_name or email.split("@", 1)[0] or "janus").strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "-", base).strip("-._")[:24] or "janus"
    if len(base) < 3:
        base = (base + "janus")[:8]
    candidate = base
    n = 2
    while c.execute("SELECT 1 FROM accounts WHERE username=? COLLATE NOCASE", (candidate,)).fetchone():
        suffix = str(n)
        candidate = f"{base[:32-len(suffix)-1]}-{suffix}"
        n += 1
    return candidate


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        value = value.strip()
        if not 3 <= len(value) <= 32:
            raise ValueError("username must be 3-32 characters")
        if not all(ch.isalnum() or ch in "._-" for ch in value):
            raise ValueError("username may contain letters, numbers, dot, underscore and hyphen")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(value) > 256:
            raise ValueError("password is too long")
        return value


class LoginRequest(BaseModel):
    identity: str
    password: str


class TokenRequest(BaseModel):
    token: str


class GoogleLoginRequest(BaseModel):
    id_token: str


@router.post("/register")
def register(req: RegisterRequest):
    init_auth_db()
    username = req.username.strip()
    email = str(req.email).strip().lower()
    now = int(time.time())
    try:
        with _db() as c:
            cur = c.execute(
                "INSERT INTO accounts(username,email,password_hash,created_at) VALUES(?,?,?,?)",
                (username, email, _hash_password(req.password), now),
            )
            account_id = int(cur.lastrowid)
            token = _new_session(c, account_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email is already registered")
    return {"account_id": account_id, "username": username, "access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(req: LoginRequest):
    init_auth_db()
    identity = req.identity.strip()
    with _db() as c:
        row = c.execute(
            "SELECT id,username,password_hash,disabled FROM accounts WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE LIMIT 1",
            (identity, identity),
        ).fetchone()
        if not row or row["disabled"] or not _verify_password(req.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username/email or password")
        token = _new_session(c, int(row["id"]))
    return {"account_id": int(row["id"]), "username": row["username"], "access_token": token, "token_type": "bearer"}


@router.post("/google")
def google_login(req: GoogleLoginRequest):
    init_auth_db()
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on the server")
    try:
        claims = google_id_token.verify_oauth2_token(
            req.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google identity token")

    sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    verified = claims.get("email_verified") is True
    display_name = str(claims.get("name") or "").strip()
    if not sub or not email or not verified:
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    now = int(time.time())
    with _db() as c:
        row = c.execute("SELECT id,username,disabled FROM accounts WHERE google_sub=?", (sub,)).fetchone()
        if not row:
            row = c.execute("SELECT id,username,disabled,google_sub FROM accounts WHERE email=? COLLATE NOCASE", (email,)).fetchone()
            if row:
                existing_sub = row["google_sub"]
                if existing_sub and existing_sub != sub:
                    raise HTTPException(status_code=409, detail="This email is already linked to another Google identity")
                c.execute("UPDATE accounts SET google_sub=? WHERE id=?", (sub, int(row["id"])))
            else:
                username = _unique_username(c, email, display_name)
                cur = c.execute(
                    "INSERT INTO accounts(username,email,password_hash,created_at,google_sub) VALUES(?,?,?,?,?)",
                    (username, email, "google_only", now, sub),
                )
                row = c.execute("SELECT id,username,disabled FROM accounts WHERE id=?", (int(cur.lastrowid),)).fetchone()
        if row["disabled"]:
            raise HTTPException(status_code=403, detail="Account disabled")
        token = _new_session(c, int(row["id"]))
        account_id = int(row["id"])
        username = str(row["username"])

    return {
        "account_id": account_id,
        "username": username,
        "access_token": token,
        "token_type": "bearer",
        "provider": "google",
    }


@router.post("/logout")
def logout(req: TokenRequest):
    init_auth_db()
    with _db() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(req.token),))
    return {"ok": True}


def account_for_token(token: Optional[str]):
    if not token:
        return None
    init_auth_db()
    now = int(time.time())
    with _db() as c:
        row = c.execute(
            """
            SELECT a.id,a.username,a.email,s.expires_at
            FROM sessions s JOIN accounts a ON a.id=s.account_id
            WHERE s.token_hash=? AND s.expires_at>? AND a.disabled=0
            """,
            (_token_hash(token), now),
        ).fetchone()
    return dict(row) if row else None


init_auth_db()
