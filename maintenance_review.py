"""Quarterly JANUS maintenance and upgrade proposal system.

Advisory by design: JANUS may inspect its own runtime metadata, persist a proposal,
prepare an owner email/message and request a human + ChatGPT review. It must never
edit protected code, install packages, switch models, change configuration or deploy
upgrades on its own.
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
OWNER_PROFILE = os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE", "").strip()
CHECK_SECONDS = max(3600, int(os.getenv("JANUS_MAINTENANCE_CHECK_SECONDS", "21600")))


def _db():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
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
              email_subject TEXT,
              email_body TEXT,
              notification_attempted INTEGER NOT NULL DEFAULT 0,
              notification_sent INTEGER NOT NULL DEFAULT 0,
              notification_error TEXT,
              owner_message_created INTEGER NOT NULL DEFAULT 0,
              review_state TEXT NOT NULL DEFAULT 'awaiting_owner_review',
              acknowledged_at TEXT
            );
            """
        )
        cols = {r[1] for r in c.execute("PRAGMA table_info(janus_maintenance_review)")}
        additions = {
            "email_subject": "TEXT",
            "email_body": "TEXT",
            "owner_message_created": "INTEGER NOT NULL DEFAULT 0",
            "review_state": "TEXT NOT NULL DEFAULT 'awaiting_owner_review'",
            "acknowledged_at": "TEXT",
        }
        for name, ddl in additions.items():
            if name not in cols:
                c.execute(f"ALTER TABLE janus_maintenance_review ADD COLUMN {name} {ddl}")


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


def _owner_message(report_id: int, report: dict) -> bool:
    """Put the review request in JANUS Messages when an owner profile is configured."""
    if not OWNER_PROFILE:
        return False
    try:
        detail = json.dumps({
            "message_type": "Follow-up",
            "text": (
                "JANUS maintenance review is due. I prepared a read-only upgrade/security proposal "
                "for us to review together before any code, dependency, model, API or deployment change. "
                f"Maintenance report #{report_id} is awaiting owner review."
            ),
            "source": "maintenance_review",
            "origin": "scheduled-quarterly",
            "review_id": report_id,
            "requires_owner_approval": True,
            "automatic_changes": False,
            "deployed_commit": report.get("deployed_commit"),
        }, ensure_ascii=False)
        with _db() as c:
            c.execute(
                "INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                (OWNER_PROFILE, "proactive_message", detail, datetime.now(timezone.utc).isoformat()),
            )
        return True
    except Exception:
        return False


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
        "proposal_kind": "maintenance_upgrade_review",
        "review_state": "awaiting_owner_review",
        "advisory_only": True,
        "owner_approval_required": True,
        "chatgpt_review_requested": True,
        "automatic_code_changes_allowed": False,
        "automatic_dependency_upgrades_allowed": False,
        "automatic_model_switches_allowed": False,
        "automatic_deployment_allowed": False,
        "external_model_api_calls_used": 0,
        "review_request": "Review JANUS with the owner and ChatGPT before applying maintenance, patches, dependency upgrades, architecture changes, model/API changes, or deployment changes.",
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "architecture": status.get("architecture") if isinstance(status, dict) else None,
        "topology": status.get("topology") if isinstance(status, dict) else None,
        "phase": status.get("phase") if isinstance(status, dict) else None,
        "persistent_storage": status.get("persistent_storage") if isinstance(status, dict) else None,
        "server_core_cycle_range": [min(cycles), max(cycles)] if cycles else None,
        "remote_clients": status.get("remote_clients") if isinstance(status, dict) else None,
        "review_sections": [
            {"area": "security", "request": "Review authentication/OAuth, secrets, dependency advisories, account isolation, file handling and platform security guidance."},
            {"area": "runtime", "request": "Review Python, FastAPI, database/persistence, Render runtime and supported platform versions."},
            {"area": "models_and_apis", "request": "Review OpenAI model/API capabilities, pricing, deprecations and replacement paths before changing configured models."},
            {"area": "clients", "request": "Review Android/Gradle and, when resumed, iOS/Xcode and Windows packaging dependencies for supported stable upgrades."},
            {"area": "architecture", "request": "Check 7->2->1->1 routing, selective federated sync, continuity governance, cost governor, background cognition and protected identity boundaries for regressions."},
            {"area": "tests", "request": "Run regression/build workflows, persistence/migration tests and representative device/server smoke tests before deployment."},
        ],
        "protected_invariants": [
            "No automatic protected-code modification or self-upgrade.",
            "No automatic dependency/model/API switch merely because a newer version exists.",
            "No whole-state local/global overwrite; preserve provenance and selective sync semantics.",
            "Preserve JANUS identity/safety boundaries unless deliberately redesigned with owner review.",
            "Maintenance findings are proposals and evidence, not authorization to act."
        ],
    }


def _email_for(report: dict) -> tuple[str, str]:
    subject = "JANUS maintenance review requested — approval required before changes"
    sections = "\n".join(f"- {x['area']}: {x['request']}" for x in report.get("review_sections", []))
    body = (
        "JANUS has reached its scheduled maintenance review point.\n\n"
        "No code, dependency, model, API, configuration, or deployment change has been made automatically.\n"
        "Please review this proposal with ChatGPT before deciding whether to apply any maintenance or upgrades.\n\n"
        f"Deployed commit: {report.get('deployed_commit')}\n"
        f"Python: {report.get('python')}\n"
        f"Runtime phase: {report.get('phase')}\n"
        f"Persistence reported: {report.get('persistent_storage')}\n\n"
        "Requested review:\n" + sections + "\n\n"
        "Required decision: approve, modify, defer, or reject each proposed maintenance action.\n"
        "JANUS remains advisory until that review occurs.\n"
    )
    return subject, body


def run_review(runtime=None, reason: str = "quarterly") -> dict:
    _init_db()
    report = build_report(runtime, reason)
    subject, body = _email_for(report)
    sent, error = _smtp_send(subject, body)
    with _db() as c:
        cur = c.execute(
            """INSERT INTO janus_maintenance_review(
                created_at,due_reason,report_json,email_subject,email_body,
                notification_attempted,notification_sent,notification_error,
                owner_message_created,review_state
            ) VALUES(?,?,?,?,?,?,?,?,0,'awaiting_owner_review')""",
            (report["generated_at"], reason, json.dumps(report), subject, body, 1, 1 if sent else 0, error or None),
        )
        review_id = int(cur.lastrowid)
    owner_message = _owner_message(review_id, report)
    if owner_message:
        with _db() as c:
            c.execute("UPDATE janus_maintenance_review SET owner_message_created=1 WHERE id=?", (review_id,))
    return {
        "review_id": review_id,
        "report": report,
        "email_subject": subject,
        "email_body": body,
        "notification_sent": sent,
        "notification_error": error or None,
        "owner_message_created": owner_message,
        "requires_owner_approval": True,
        "automatic_changes": False,
    }


def acknowledge(review_id: int, state: str = "reviewed") -> dict:
    """Record owner/admin disposition only; this never performs maintenance."""
    allowed = {"reviewed", "approved_for_manual_work", "deferred", "rejected"}
    state = str(state or "reviewed").strip().lower()
    if state not in allowed:
        raise ValueError("invalid maintenance review state")
    _init_db(); stamp = datetime.now(timezone.utc).isoformat()
    with _db() as c:
        row = c.execute("SELECT id FROM janus_maintenance_review WHERE id=?", (int(review_id),)).fetchone()
        if not row:
            raise KeyError("maintenance review not found")
        c.execute("UPDATE janus_maintenance_review SET review_state=?,acknowledged_at=? WHERE id=?", (state, stamp, int(review_id)))
    return {"review_id": int(review_id), "review_state": state, "acknowledged_at": stamp, "automatic_changes": False}


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
        "owner_profile_configured": bool(OWNER_PROFILE),
        "due": due_now(),
        "next_due_at": next_due,
        "last_review": last,
        "automatic_changes": False,
        "automatic_model_api_calls": False,
        "owner_approval_required": True,
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
