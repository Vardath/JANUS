"""Quarterly JANUS maintenance review.

This is deliberately advisory. It never edits code, installs packages, changes
configuration, or spends model/API budget. Every ~90 days it records a bounded
technical snapshot and can email the owner asking for a human + ChatGPT review.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
import json
import os
import platform
import smtplib
import sqlite3
import threading
import time
from typing import Optional

DB_PATH = os.getenv("JANUS_DB_PATH", "/data/janus.sqlite3")
INTERVAL_DAYS = max(30, int(os.getenv("JANUS_MAINTENANCE_INTERVAL_DAYS", "90")))
OWNER_EMAIL = os.getenv("JANUS_MAINTENANCE_OWNER_EMAIL", "").strip()
CHECK_SECONDS = max(3600, int(os.getenv("JANUS_MAINTENANCE_CHECK_SECONDS", "21600")))


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS janus_maintenance_review(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              due_reason TEXT NOT NULL,
              report_json TEXT NOT NULL,
              notification_attempted INTEGER NOT NULL DEFAULT 0,
              notification_sent INTEGER NOT NULL DEFAULT 0,
              notification_error TEXT
            );
            """
        )


def _last_review() -> Optional[dict]:
    _init_db()
    with _db() as c:
        r = c.execute("SELECT * FROM janus_maintenance_review ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def due_now(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    last = _last_review()
    if not last:
        return True
    dt = _parse_iso(str(last.get("created_at") or ""))
    return not dt or now - dt >= timedelta(days=INTERVAL_DAYS)


def _smtp_send(subject: str, body: str) -> tuple[bool, str]:
    if not OWNER_EMAIL:
        return False, "JANUS_MAINTENANCE_OWNER_EMAIL not configured"
    host = os.getenv("JANUS_SMTP_HOST", "").strip()
    user = os.getenv("JANUS_SMTP_USER", "").strip()
    password = os.getenv("JANUS_SMTP_PASSWORD", "")
    sender = os.getenv("JANUS_SMTP_FROM", "").strip() or user
    if not host or not sender:
        return False, "SMTP host/from not configured"
    port = int(os.getenv("JANUS_SMTP_PORT", "587"))
    use_tls = os.getenv("JANUS_SMTP_TLS", "1").strip().lower() not in {"0", "false", "no"}
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = OWNER_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            if use_tls:
                s.starttls()
            if user:
                s.login(user, password)
            s.send_message(msg)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:300]}"


def build_report(runtime=None, reason: str = "quarterly") -> dict:
    status = {}
    try:
        status = runtime.status() if runtime is not None else {}
    except Exception as exc:
        status = {"runtime_status_error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    cores = status.get("cores") if isinstance(status, dict) else {}
    cycles = [int((v or {}).get("cycle_count", 0) or 0) for v in (cores or {}).values()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "advisory_only": True,
        "automatic_code_changes_allowed": False,
        "automatic_dependency_upgrades_allowed": False,
        "external_model_api_calls_used": 0,
        "review_request": "Review JANUS with the owner and ChatGPT before applying maintenance, patches, dependency upgrades, architecture changes, or new model/API capabilities.",
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "architecture": status.get("architecture") if isinstance(status, dict) else None,
        "topology": status.get("topology") if isinstance(status, dict) else None,
        "phase": status.get("phase") if isinstance(status, dict) else None,
        "persistent_storage": status.get("persistent_storage") if isinstance(status, dict) else None,
        "server_core_cycle_range": [min(cycles), max(cycles)] if cycles else None,
        "remote_clients": status.get("remote_clients") if isinstance(status, dict) else None,
        "checks_requested": [
            "Review Python, FastAPI, Android/Gradle, iOS/Xcode and Windows packaging dependencies for supported stable upgrades.",
            "Review OpenAI model/API capabilities, pricing and deprecations before changing configured models.",
            "Review Render/runtime platform changes and persistent-storage assumptions.",
            "Review authentication/OAuth and platform security guidance.",
            "Run regression/build workflows and device smoke tests before deployment.",
            "Preserve JANUS identity/safety boundaries, forward-only 7->2->1->1 routing and selective sync semantics unless deliberately redesigned."
        ],
    }


def run_review(runtime=None, reason: str = "quarterly") -> dict:
    _init_db()
    report = build_report(runtime, reason)
    subject = "JANUS quarterly maintenance review requested"
    body = (
        "JANUS has reached its scheduled maintenance review point.\n\n"
        "No code, dependency, model, API, or configuration change has been made automatically.\n"
        "Please review JANUS with ChatGPT before proceeding with upgrades or patches.\n\n"
        + json.dumps(report, indent=2, ensure_ascii=False)
    )
    sent, error = _smtp_send(subject, body)
    with _db() as c:
        c.execute(
            "INSERT INTO janus_maintenance_review(created_at,due_reason,report_json,notification_attempted,notification_sent,notification_error) VALUES(?,?,?,?,?,?)",
            (report["generated_at"], reason, json.dumps(report), 1, 1 if sent else 0, error or None),
        )
    return {"report": report, "notification_sent": sent, "notification_error": error or None}


def status() -> dict:
    last = _last_review()
    next_due = None
    if last:
        dt = _parse_iso(str(last.get("created_at") or ""))
        if dt:
            next_due = (dt + timedelta(days=INTERVAL_DAYS)).isoformat()
    return {
        "enabled": True,
        "interval_days": INTERVAL_DAYS,
        "owner_email_configured": bool(OWNER_EMAIL),
        "due": due_now(),
        "next_due_at": next_due,
        "last_review": last,
        "automatic_changes": False,
        "automatic_model_api_calls": False,
    }


def install(app, runtime) -> None:
    _init_db()
    if getattr(app.state, "janus_maintenance_review_installed", False):
        return
    app.state.janus_maintenance_review_installed = True

    @app.on_event("startup")
    async def _start_maintenance_review_loop():
        def loop():
            while True:
                try:
                    if due_now():
                        run_review(runtime, "scheduled-quarterly")
                except Exception:
                    pass
                time.sleep(CHECK_SECONDS)
        threading.Thread(target=loop, name="janus-maintenance-review", daemon=True).start()
