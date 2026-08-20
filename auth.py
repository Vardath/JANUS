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


def _has_table(c, table):
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _has_column(c, table, column):
    return _has_table(c, table) and any(row[1] == column for row in c.execute(f"PRAGMA table_info({table})"))


def _preserve_legacy_table(c, table):
    """Move an incompatible legacy table aside without deleting user data."""
    if not _has_table(c, table):
        return
    base = f"{table}_legacy"
    name = base
    n = 2
    while _has_table(c, name):
        name = f"{base}_{n}"
        n += 1
    c.execute(f'ALTER TABLE "{table}" RENAME TO "{name}"')


def init_auth_db():
    with _db() as c:
        # Stage 1: ensure the account table exists before any dependent tables.
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                disabled INTEGER NOT NULL DEFAULT 0
            )
        """)

        if not _has_column(c, "accounts", "google_sub"):
            c.execute("ALTER TABLE accounts ADD COLUMN google_sub TEXT")
        if not _has_column(c, "accounts", "email_verified"):
            c.execute("ALTER TABLE accounts ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        if not _has_column(c, "accounts", "updated_at"):
            # SQLite requires a default when adding a NOT NULL column to an
            # existing table. Backfill from created_at immediately afterwards.
            c.execute("ALTER TABLE accounts ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")
            c.execute("UPDATE accounts SET updated_at=created_at WHERE updated_at=0")

        # Stage 2: old JANUS builds used different auth/session token schemas.
        # Preserve incompatible tables instead of dropping them, then create the
        # current schema. This is safe for Render's persistent SQLite disk.
        if _has_table(c, "sessions") and not _has_column(c, "sessions", "account_id"):
            _preserve_legacy_table(c, "sessions")
        if _has_table(c, "auth_tokens") and not _has_column(c, "auth_tokens", "account_id"):
            _preserve_legacy_table(c, "auth_tokens")

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token_hash TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                purpose TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                used_at INTEGER
            )
        """)

        # Stage 3: create indexes only after migrations have guaranteed columns.
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_auth_tokens_account ON auth_tokens(account_id,purpose)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_google_sub ON accounts(google_sub) WHERE google_sub IS NOT NULL")


def _hash_password(password):
    salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"

def _verify_password(password,encoded):
    try:
        alg,iterations,salt_hex,digest_hex=encoded.split("$",3)
        if alg!="pbkdf2_sha256": return False
        digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),int(iterations)); return hmac.compare_digest(digest.hex(),digest_hex)
    except Exception: return False

def _token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
def _new_session(c,account_id):
    token=secrets.token_urlsafe(48); now=int(time.time()); c.execute("INSERT INTO sessions(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",(_token_hash(token),account_id,now,now+SESSION_TTL)); return token

def _new_action_token(c,account_id,purpose,ttl):
    token=secrets.token_urlsafe(40); now=int(time.time()); c.execute("DELETE FROM auth_tokens WHERE account_id=? AND purpose=? AND used_at IS NULL",(account_id,purpose)); c.execute("INSERT INTO auth_tokens(token_hash,account_id,purpose,created_at,expires_at) VALUES(?,?,?,?,?)",(_token_hash(token),account_id,purpose,now,now+ttl)); return token

def _smtp_ready(): return bool(os.getenv("JANUS_SMTP_HOST") and os.getenv("JANUS_SMTP_FROM"))
def _send_email(to_addr,subject,body):
    if not _smtp_ready(): return False
    host=os.environ["JANUS_SMTP_HOST"]; port=int(os.getenv("JANUS_SMTP_PORT","587")); user=os.getenv("JANUS_SMTP_USER",""); password=os.getenv("JANUS_SMTP_PASSWORD","")
    msg=EmailMessage(); msg["From"]=os.environ["JANUS_SMTP_FROM"]; msg["To"]=to_addr; msg["Subject"]=subject; msg.set_content(body); context=ssl.create_default_context()
    with smtplib.SMTP(host,port,timeout=20) as smtp:
        smtp.ehlo()
        if os.getenv("JANUS_SMTP_TLS","1")=="1": smtp.starttls(context=context); smtp.ehlo()
        if user: smtp.login(user,password)
        smtp.send_message(msg)
    return True

def _send_verification(c,account_id,email):
    token=_new_action_token(c,account_id,"verify_email",VERIFY_TTL); return _send_email(email,"Verify your JANUS email",f"Your JANUS email verification code is:\n\n{token}\n\nThis code expires in 24 hours.")

def _unique_username(c,email,display_name=""):
    base=(display_name or email.split("@",1)[0] or "janus").strip().lower(); base=re.sub(r"[^a-z0-9._-]+","-",base).strip("-._")[:24] or "janus"
    if len(base)<3: base=(base+"janus")[:8]
    candidate,n=base,2
    while c.execute("SELECT 1 FROM accounts WHERE username=? COLLATE NOCASE",(candidate,)).fetchone(): suffix=str(n); candidate=f"{base[:32-len(suffix)-1]}-{suffix}"; n+=1
    return candidate


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    @field_validator("username")
    @classmethod
    def username_valid(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,32}",v): raise ValueError("Username must be 3-32 characters using letters, numbers, dot, underscore or hyphen")
        return v
    @field_validator("password")
    @classmethod
    def password_valid(cls,v):
        if len(v)<12 or len(v)>128: raise ValueError("Password must be 12-128 characters")
        if not (re.search(r"[A-Za-z]",v) and re.search(r"\d",v)): raise ValueError("Password must contain a letter and a number")
        return v
class LoginRequest(BaseModel): identifier: str; password: str
class GoogleRequest(BaseModel): id_token: str
class VerifyEmailRequest(BaseModel): token: str
class ResendVerificationRequest(BaseModel): email: EmailStr
class ForgotPasswordRequest(BaseModel): email: EmailStr
class ResetPasswordRequest(BaseModel): token: str; new_password: str
class DeleteAccountRequest(BaseModel): confirmation: str; current_password: Optional[str]=None


def _account_dict(row):
    return {"id":row["id"],"username":row["username"],"email":row["email"],"email_verified":bool(row["email_verified"]),"google_linked":bool(row["google_sub"]),"created_at":row["created_at"]}

def account_for_token(token):
    if not token: return None
    now=int(time.time())
    with _db() as c:
        return c.execute("SELECT a.* FROM sessions s JOIN accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>? AND a.disabled=0",(_token_hash(token),now)).fetchone()

def _bearer(authorization):
    if not authorization or not authorization.lower().startswith("bearer "): return None
    return authorization.split(" ",1)[1].strip()

def require_account(authorization):
    row=account_for_token(_bearer(authorization))
    if row is None: raise HTTPException(status_code=401,detail="Authentication required")
    return row


@router.post("/register")
def register(req:RegisterRequest):
    now=int(time.time())
    with _db() as c:
        try:
            cur=c.execute("INSERT INTO accounts(username,email,password_hash,created_at,updated_at,email_verified) VALUES(?,?,?,?,?,0)",(req.username.strip(),str(req.email).lower(),_hash_password(req.password),now,now)); account_id=cur.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409,detail="Username or email already exists")
        _send_verification(c,account_id,str(req.email).lower()); row=c.execute("SELECT * FROM accounts WHERE id=?",(account_id,)).fetchone(); token=_new_session(c,account_id)
    return {"ok":True,"access_token":token,"account":_account_dict(row),"verification_required":True,"email_delivery":_smtp_ready()}

@router.post("/login")
def login(req:LoginRequest):
    with _db() as c:
        row=c.execute("SELECT * FROM accounts WHERE (username=? COLLATE NOCASE OR email=? COLLATE NOCASE) AND disabled=0",(req.identifier.strip(),req.identifier.strip())).fetchone()
        if row is None or not _verify_password(req.password,row["password_hash"]): raise HTTPException(status_code=401,detail="Invalid username/email or password")
        token=_new_session(c,row["id"])
    return {"ok":True,"access_token":token,"account":_account_dict(row),"verification_required":not bool(row["email_verified"])}

@router.post("/google")
def google_auth(req:GoogleRequest):
    if not GOOGLE_CLIENT_ID: raise HTTPException(status_code=503,detail="Google sign-in is not configured")
    try:
        info=google_id_token.verify_oauth2_token(req.id_token,google_requests.Request(),GOOGLE_CLIENT_ID)
    except Exception:
        raise HTTPException(status_code=401,detail="Google identity token is invalid")
    sub=str(info.get("sub") or ""); email=str(info.get("email") or "").lower(); verified=bool(info.get("email_verified")); name=str(info.get("name") or "")
    if not sub or not email or not verified: raise HTTPException(status_code=401,detail="Google account did not provide a verified email")
    now=int(time.time())
    with _db() as c:
        row=c.execute("SELECT * FROM accounts WHERE google_sub=?",(sub,)).fetchone()
        if row is None:
            row=c.execute("SELECT * FROM accounts WHERE email=? COLLATE NOCASE",(email,)).fetchone()
            if row is None:
                username=_unique_username(c,email,name); random_password=_hash_password(secrets.token_urlsafe(48)); cur=c.execute("INSERT INTO accounts(username,email,password_hash,created_at,updated_at,google_sub,email_verified) VALUES(?,?,?,?,?,?,1)",(username,email,random_password,now,now,sub)); row=c.execute("SELECT * FROM accounts WHERE id=?",(cur.lastrowid,)).fetchone()
            else:
                if row["google_sub"] and row["google_sub"]!=sub: raise HTTPException(status_code=409,detail="Email is already linked to another Google account")
                c.execute("UPDATE accounts SET google_sub=?,email_verified=1,updated_at=? WHERE id=?",(sub,now,row["id"])); row=c.execute("SELECT * FROM accounts WHERE id=?",(row["id"],)).fetchone()
        if row["disabled"]: raise HTTPException(status_code=403,detail="Account is disabled")
        token=_new_session(c,row["id"])
    return {"ok":True,"access_token":token,"account":_account_dict(row),"verification_required":False}

@router.get("/me")
def me(authorization:Optional[str]=Header(default=None)):
    row=require_account(authorization); return {"ok":True,"account":_account_dict(row)}

@router.post("/verify-email")
def verify_email(req:VerifyEmailRequest):
    now=int(time.time()); digest=_token_hash(req.token.strip())
    with _db() as c:
        row=c.execute("SELECT * FROM auth_tokens WHERE token_hash=? AND purpose='verify_email' AND used_at IS NULL AND expires_at>?",(digest,now)).fetchone()
        if row is None: raise HTTPException(status_code=400,detail="Verification token is invalid or expired")
        c.execute("UPDATE accounts SET email_verified=1,updated_at=? WHERE id=?",(now,row["account_id"])); c.execute("UPDATE auth_tokens SET used_at=? WHERE token_hash=?",(now,digest))
    return {"ok":True}

@router.post("/resend-verification")
def resend_verification(req:ResendVerificationRequest):
    with _db() as c:
        row=c.execute("SELECT * FROM accounts WHERE email=? COLLATE NOCASE AND disabled=0",(str(req.email).lower(),)).fetchone()
        if row and not row["email_verified"]: _send_verification(c,row["id"],row["email"])
    return {"ok":True,"message":"If that account exists and needs verification, a message has been sent."}

@router.post("/forgot-password")
def forgot_password(req:ForgotPasswordRequest):
    with _db() as c:
        row=c.execute("SELECT * FROM accounts WHERE email=? COLLATE NOCASE AND disabled=0",(str(req.email).lower(),)).fetchone()
        if row:
            token=_new_action_token(c,row["id"],"reset_password",RESET_TTL); _send_email(row["email"],"Reset your JANUS password",f"Your JANUS password reset code is:\n\n{token}\n\nThis code expires in 30 minutes.")
    return {"ok":True,"message":"If that email exists, a reset message has been sent."}

@router.post("/reset-password")
def reset_password(req:ResetPasswordRequest):
    RegisterRequest.password_valid(req.new_password); now=int(time.time()); digest=_token_hash(req.token.strip())
    with _db() as c:
        row=c.execute("SELECT * FROM auth_tokens WHERE token_hash=? AND purpose='reset_password' AND used_at IS NULL AND expires_at>?",(digest,now)).fetchone()
        if row is None: raise HTTPException(status_code=400,detail="Reset token is invalid or expired")
        c.execute("UPDATE accounts SET password_hash=?,updated_at=? WHERE id=?",(_hash_password(req.new_password),now,row["account_id"])); c.execute("UPDATE auth_tokens SET used_at=? WHERE token_hash=?",(now,digest)); c.execute("DELETE FROM sessions WHERE account_id=?",(row["account_id"],))
    return {"ok":True}

@router.delete("/account")
def delete_account(req:DeleteAccountRequest,authorization:Optional[str]=Header(default=None)):
    row=require_account(authorization)
    if req.confirmation!="DELETE": raise HTTPException(status_code=400,detail="Type DELETE to confirm")
    if not row["google_sub"]:
        if not req.current_password or not _verify_password(req.current_password,row["password_hash"]): raise HTTPException(status_code=401,detail="Current password is required")
    with _db() as c: c.execute("DELETE FROM accounts WHERE id=?",(row["id"],))
    return {"ok":True,"deleted":True}


init_auth_db()
