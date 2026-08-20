import hashlib
import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(prefix="/auth", tags=["auth"])
DB_PATH = Path(os.getenv("JANUS_AUTH_DB") or os.getenv("JANUS_DB_PATH") or "janus_auth.db")
GOOGLE_CLIENT_ID = os.getenv("JANUS_GOOGLE_CLIENT_ID", "").strip()
SESSION_TTL = 60 * 60 * 24 * 30
VERIFY_TTL = 60 * 60 * 24
RESET_TTL = 60 * 30
PBKDF2_ITERATIONS = 600_000


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _has_column(c, table, column):
    return any(row[1] == column for row in c.execute(f"PRAGMA table_info({table})"))


def init_auth_db():
    with _db() as c:
        c.executescript("""
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
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token_hash TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            purpose TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            used_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);
        CREATE INDEX IF NOT EXISTS idx_auth_tokens_account ON auth_tokens(account_id,purpose);
        """)
        if not _has_column(c, "accounts", "google_sub"):
            c.execute("ALTER TABLE accounts ADD COLUMN google_sub TEXT")
        if not _has_column(c, "accounts", "email_verified"):
            c.execute("ALTER TABLE accounts ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_google_sub ON accounts(google_sub) WHERE google_sub IS NOT NULL")


def _hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password, encoded):
    try:
        alg, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if alg != "pbkdf2_sha256": return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _new_session(c, account_id):
    token = secrets.token_urlsafe(48)
    now = int(time.time())
    c.execute("INSERT INTO sessions(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)", (_token_hash(token), account_id, now, now + SESSION_TTL))
    return token


def _new_action_token(c, account_id, purpose, ttl):
    token = secrets.token_urlsafe(40)
    now = int(time.time())
    c.execute("DELETE FROM auth_tokens WHERE account_id=? AND purpose=? AND used_at IS NULL", (account_id, purpose))
    c.execute("INSERT INTO auth_tokens(token_hash,account_id,purpose,created_at,expires_at) VALUES(?,?,?,?,?)", (_token_hash(token), account_id, purpose, now, now + ttl))
    return token


def _smtp_ready():
    return bool(os.getenv("JANUS_SMTP_HOST") and os.getenv("JANUS_SMTP_FROM"))


def _send_email(to_addr, subject, body):
    if not _smtp_ready():
        return False
    host = os.environ["JANUS_SMTP_HOST"]
    port = int(os.getenv("JANUS_SMTP_PORT", "587"))
    user = os.getenv("JANUS_SMTP_USER", "")
    password = os.getenv("JANUS_SMTP_PASSWORD", "")
    msg = EmailMessage()
    msg["From"] = os.environ["JANUS_SMTP_FROM"]
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.ehlo()
        if os.getenv("JANUS_SMTP_TLS", "1") == "1":
            smtp.starttls(context=context)
            smtp.ehlo()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)
    return True


def _send_verification(c, account_id, email):
    token = _new_action_token(c, account_id, "verify_email", VERIFY_TTL)
    return _send_email(email, "Verify your JANUS email", f"Your JANUS email verification code is:\n\n{token}\n\nThis code expires in 24 hours.")


def _unique_username(c, email, display_name=""):
    base = (display_name or email.split("@", 1)[0] or "janus").strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "-", base).strip("-._")[:24] or "janus"
    if len(base) < 3: base = (base + "janus")[:8]
    candidate, n = base, 2
    while c.execute("SELECT 1 FROM accounts WHERE username=? COLLATE NOCASE", (candidate,)).fetchone():
        suffix = str(n); candidate = f"{base[:32-len(suffix)-1]}-{suffix}"; n += 1
    return candidate


def _bearer(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        value = value.strip()
        if not 3 <= len(value) <= 32: raise ValueError("username must be 3-32 characters")
        if not all(ch.isalnum() or ch in "._-" for ch in value): raise ValueError("username may contain letters, numbers, dot, underscore and hyphen")
        return value
    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        if len(value) < 8: raise ValueError("password must be at least 8 characters")
        if len(value) > 256: raise ValueError("password is too long")
        return value


class LoginRequest(BaseModel): identity: str; password: str
class TokenRequest(BaseModel): token: str
class GoogleLoginRequest(BaseModel): id_token: str
class EmailRequest(BaseModel): email: EmailStr
class VerifyRequest(BaseModel): token: str
class ResetRequest(BaseModel):
    token: str
    new_password: str
    @field_validator("new_password")
    @classmethod
    def valid_password(cls, value):
        if len(value) < 8: raise ValueError("password must be at least 8 characters")
        if len(value) > 256: raise ValueError("password is too long")
        return value


@router.post("/register")
def register(req: RegisterRequest):
    init_auth_db(); username=req.username.strip(); email=str(req.email).strip().lower(); now=int(time.time())
    try:
        with _db() as c:
            cur=c.execute("INSERT INTO accounts(username,email,password_hash,created_at,email_verified) VALUES(?,?,?,?,0)", (username,email,_hash_password(req.password),now))
            account_id=int(cur.lastrowid); token=_new_session(c,account_id)
            try: delivered=_send_verification(c,account_id,email)
            except Exception: delivered=False
    except sqlite3.IntegrityError:
        raise HTTPException(409,"Username or email is already registered")
    return {"account_id":account_id,"username":username,"access_token":token,"token_type":"bearer","email_verified":False,"verification_email_sent":delivered}


@router.post("/login")
def login(req: LoginRequest):
    init_auth_db(); identity=req.identity.strip()
    with _db() as c:
        row=c.execute("SELECT id,username,password_hash,disabled,email_verified FROM accounts WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE LIMIT 1",(identity,identity)).fetchone()
        if not row or row["disabled"] or not _verify_password(req.password,row["password_hash"]): raise HTTPException(401,"Invalid username/email or password")
        token=_new_session(c,int(row["id"]))
    return {"account_id":int(row["id"]),"username":row["username"],"access_token":token,"token_type":"bearer","email_verified":bool(row["email_verified"])}


@router.post("/google")
def google_login(req: GoogleLoginRequest):
    init_auth_db()
    if not GOOGLE_CLIENT_ID: raise HTTPException(503,"Google sign-in is not configured on the server")
    try: claims=google_id_token.verify_oauth2_token(req.id_token,google_requests.Request(),GOOGLE_CLIENT_ID)
    except Exception: raise HTTPException(401,"Invalid Google identity token")
    sub=str(claims.get("sub") or "").strip(); email=str(claims.get("email") or "").strip().lower(); verified=claims.get("email_verified") is True; display_name=str(claims.get("name") or "").strip()
    if not sub or not email or not verified: raise HTTPException(401,"Google account email is not verified")
    now=int(time.time())
    with _db() as c:
        row=c.execute("SELECT id,username,disabled FROM accounts WHERE google_sub=?",(sub,)).fetchone()
        if not row:
            row=c.execute("SELECT id,username,disabled,google_sub FROM accounts WHERE email=? COLLATE NOCASE",(email,)).fetchone()
            if row:
                if row["google_sub"] and row["google_sub"]!=sub: raise HTTPException(409,"This email is already linked to another Google identity")
                c.execute("UPDATE accounts SET google_sub=?,email_verified=1 WHERE id=?",(sub,int(row["id"])))
            else:
                username=_unique_username(c,email,display_name)
                cur=c.execute("INSERT INTO accounts(username,email,password_hash,created_at,google_sub,email_verified) VALUES(?,?,?,?,?,1)",(username,email,"google_only",now,sub))
                row=c.execute("SELECT id,username,disabled FROM accounts WHERE id=?",(int(cur.lastrowid),)).fetchone()
        else:
            c.execute("UPDATE accounts SET email_verified=1 WHERE id=?",(int(row["id"]),))
        if row["disabled"]: raise HTTPException(403,"Account disabled")
        token=_new_session(c,int(row["id"])); account_id=int(row["id"]); username=str(row["username"])
    return {"account_id":account_id,"username":username,"access_token":token,"token_type":"bearer","provider":"google","email_verified":True}


@router.post("/forgot-password")
def forgot_password(req: EmailRequest):
    init_auth_db(); email=str(req.email).strip().lower()
    with _db() as c:
        row=c.execute("SELECT id,email FROM accounts WHERE email=? COLLATE NOCASE AND disabled=0",(email,)).fetchone()
        if row:
            token=_new_action_token(c,int(row["id"]),"reset_password",RESET_TTL)
            try: _send_email(row["email"],"Reset your JANUS password",f"Your JANUS password reset code is:\n\n{token}\n\nThis code expires in 30 minutes.")
            except Exception: pass
    return {"ok":True,"message":"If that email belongs to a JANUS account, a reset message has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetRequest):
    init_auth_db(); now=int(time.time())
    with _db() as c:
        row=c.execute("SELECT account_id FROM auth_tokens WHERE token_hash=? AND purpose='reset_password' AND used_at IS NULL AND expires_at>?",(_token_hash(req.token.strip()),now)).fetchone()
        if not row: raise HTTPException(400,"Invalid or expired reset code")
        account_id=int(row["account_id"])
        c.execute("UPDATE accounts SET password_hash=? WHERE id=?",(_hash_password(req.new_password),account_id))
        c.execute("UPDATE auth_tokens SET used_at=? WHERE token_hash=?",(now,_token_hash(req.token.strip())))
        c.execute("DELETE FROM sessions WHERE account_id=?",(account_id,))
    return {"ok":True,"message":"Password changed. Please sign in again."}


@router.post("/verify-email")
def verify_email(req: VerifyRequest):
    init_auth_db(); now=int(time.time()); th=_token_hash(req.token.strip())
    with _db() as c:
        row=c.execute("SELECT account_id FROM auth_tokens WHERE token_hash=? AND purpose='verify_email' AND used_at IS NULL AND expires_at>?",(th,now)).fetchone()
        if not row: raise HTTPException(400,"Invalid or expired verification code")
        c.execute("UPDATE accounts SET email_verified=1 WHERE id=?",(int(row["account_id"]),))
        c.execute("UPDATE auth_tokens SET used_at=? WHERE token_hash=?",(now,th))
    return {"ok":True,"email_verified":True}


@router.post("/resend-verification")
def resend_verification(authorization: Optional[str]=Header(default=None)):
    account=account_for_token(_bearer(authorization))
    if not account: raise HTTPException(401,"Valid JANUS session required")
    if account.get("email_verified"): return {"ok":True,"email_verified":True,"sent":False}
    with _db() as c:
        try: sent=_send_verification(c,int(account["id"]),account["email"])
        except Exception: sent=False
    return {"ok":True,"email_verified":False,"sent":sent}


@router.get("/me")
def me(authorization: Optional[str]=Header(default=None)):
    account=account_for_token(_bearer(authorization))
    if not account: raise HTTPException(401,"Valid JANUS session required")
    return account


@router.post("/logout")
def logout(req: TokenRequest):
    init_auth_db()
    with _db() as c: c.execute("DELETE FROM sessions WHERE token_hash=?",(_token_hash(req.token),))
    return {"ok":True}


def account_for_token(token: Optional[str]):
    if not token: return None
    init_auth_db(); now=int(time.time())
    with _db() as c:
        row=c.execute("SELECT a.id,a.username,a.email,a.email_verified,s.expires_at FROM sessions s JOIN accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>? AND a.disabled=0",(_token_hash(token),now)).fetchone()
    if not row: return None
    result=dict(row); result["email_verified"]=bool(result["email_verified"]); return result


init_auth_db()
