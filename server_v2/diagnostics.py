from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import storage

DECISION_FILE = Path(__file__).with_name("supervisor_decisions.json")
FAILURE_MARKERS = (
    "unable to", "cannot ", "can't ", "not configured", "not available", "unsupported",
    "not supported", "failed this turn", "call failed", "budget has been reached",
    "could not", "is unavailable", "not implemented", "missing capability",
)


def init_schema() -> None:
    with storage.db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS v2_chat_history_full(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              client_message_id TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_chat_history_full_account ON v2_chat_history_full(account_id,id ASC);

            CREATE TABLE IF NOT EXISTS v2_capability_requests(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              fingerprint TEXT NOT NULL,
              capability TEXT NOT NULL,
              title TEXT NOT NULL,
              detail TEXT NOT NULL,
              evidence TEXT NOT NULL DEFAULT '',
              severity TEXT NOT NULL DEFAULT 'normal',
              state TEXT NOT NULL DEFAULT 'awaiting_supervisor_review',
              occurrence_count INTEGER NOT NULL DEFAULT 1,
              supervisor_decision TEXT,
              decision_reason TEXT NOT NULL DEFAULT '',
              implementation_state TEXT NOT NULL DEFAULT 'not_started',
              implemented_version TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              UNIQUE(account_id,fingerprint)
            );
            CREATE INDEX IF NOT EXISTS idx_v2_capability_requests_account_state ON v2_capability_requests(account_id,state,id DESC);

            CREATE TABLE IF NOT EXISTS v2_supervisor_sync(
              decision_key TEXT PRIMARY KEY,
              applied_at INTEGER NOT NULL
            );
            """
        )


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split()).strip()


def _fingerprint(capability: str, title: str, detail: str) -> str:
    seed = f"{_norm(capability)}|{_norm(title)}|{_norm(detail)[:500]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def record_chat_turn(account_id: int, user_message: str, reply: str, client_message_id: str = "") -> None:
    aid = int(account_id)
    cid = str(client_message_id or "")[:128]
    with storage.db() as c:
        if cid:
            exists = c.execute(
                "SELECT 1 FROM v2_chat_history_full WHERE account_id=? AND client_message_id=? AND role='user' LIMIT 1",
                (aid, cid),
            ).fetchone()
            if exists:
                return
        ts = storage.now()
        c.execute(
            "INSERT INTO v2_chat_history_full(account_id,role,content,client_message_id,created_at) VALUES(?,?,?,?,?)",
            (aid, "user", str(user_message or "")[:100000], cid, ts),
        )
        c.execute(
            "INSERT INTO v2_chat_history_full(account_id,role,content,client_message_id,created_at) VALUES(?,?,?,?,?)",
            (aid, "assistant", str(reply or "")[:100000], cid, ts),
        )


def record_request(account_id: int, capability: str, title: str, detail: str, evidence: str = "", severity: str = "normal") -> dict[str, Any]:
    aid = int(account_id)
    cap = (capability or "general").strip()[:120]
    title = " ".join((title or "Capability gap").split())[:240]
    detail = " ".join((detail or "JANUS detected a capability or reliability gap.").split())[:8000]
    evidence = str(evidence or "")[:12000]
    sev = severity if severity in {"low", "normal", "high", "critical"} else "normal"
    fp = _fingerprint(cap, title, detail)
    now = storage.now()
    created = False
    with storage.db() as c:
        row = c.execute("SELECT * FROM v2_capability_requests WHERE account_id=? AND fingerprint=?", (aid, fp)).fetchone()
        if row:
            count = int(row["occurrence_count"] or 1) + 1
            state = str(row["state"] or "awaiting_supervisor_review")
            # A re-observed failure after implementation re-opens the request for review.
            if state == "implemented":
                state = "awaiting_supervisor_review"
            c.execute(
                "UPDATE v2_capability_requests SET occurrence_count=?,evidence=?,severity=?,state=?,updated_at=? WHERE id=?",
                (count, evidence or str(row["evidence"] or ""), sev, state, now, int(row["id"])),
            )
            req_id = int(row["id"])
        else:
            cur = c.execute(
                "INSERT INTO v2_capability_requests(account_id,fingerprint,capability,title,detail,evidence,severity,state,occurrence_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (aid, fp, cap, title, detail, evidence, sev, "awaiting_supervisor_review", 1, now, now),
            )
            req_id = int(cur.lastrowid)
            created = True
    if created:
        storage.add_message(
            aid,
            "capability_request",
            f"JANUS diagnosed a maintenance/capability request.\n\n{title}\nCapability: {cap}\nSeverity: {sev}\n\n{detail}\n\nThis request is queued for ChatGPT Supervisor review. JANUS cannot approve, edit, install, change models/APIs, or deploy itself.",
            "janus-diagnostics",
        )
        storage.add_event(aid, "safety", "capability_request", title, title, "foreground")
    return get_request(aid, req_id) or {"id": req_id, "fingerprint": fp}


def get_request(account_id: int, request_id: int) -> dict[str, Any] | None:
    row = storage.one("SELECT * FROM v2_capability_requests WHERE account_id=? AND id=?", (int(account_id), int(request_id)))
    return dict(row) if row else None


def list_requests(account_id: int, include_closed: bool = True, limit: int = 200) -> list[dict[str, Any]]:
    where = "account_id=?" if include_closed else "account_id=? AND state NOT IN ('implemented','disapproved')"
    return storage.rows(
        f"SELECT id,fingerprint,capability,title,detail,evidence,severity,state,occurrence_count,supervisor_decision,decision_reason,implementation_state,implemented_version,created_at,updated_at FROM v2_capability_requests WHERE {where} ORDER BY CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'normal' THEN 2 ELSE 1 END DESC,id DESC LIMIT ?",
        (int(account_id), max(1, min(500, int(limit)))),
    )


def inspect_chat(account_id: int, user_message: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    reply = str(result.get("reply") or "")
    low = reply.lower()
    findings: list[dict[str, Any]] = []
    marker = next((m for m in FAILURE_MARKERS if m in low), "")
    if marker:
        capability = "chat_or_provider"
        if "budget" in low:
            capability = "cost_governor"
        elif "model" in low or "openai" in low:
            capability = "foreground_model"
        elif "image" in low:
            capability = "image_generation"
        elif "web" in low or "research" in low:
            capability = "foreground_research"
        findings.append(record_request(
            account_id,
            capability,
            "Chat encountered an unavailable or failed capability",
            f"While handling the user's request, JANUS reported a limitation containing '{marker}'. The failure should be audited to determine whether it is expected policy, configuration, a transient provider fault, or an app/server defect.",
            evidence=f"USER: {user_message}\nJANUS: {reply}",
            severity="high" if "failed" in marker or "not configured" in marker else "normal",
        ))

    # Explicit self-report convention available to future cores/tools without exposing chain-of-thought.
    for item in result.get("capability_requests") or []:
        if not isinstance(item, dict):
            continue
        findings.append(record_request(
            account_id,
            str(item.get("capability") or "general"),
            str(item.get("title") or "JANUS capability request"),
            str(item.get("detail") or item.get("reason") or "JANUS reported a capability gap."),
            evidence=str(item.get("evidence") or ""),
            severity=str(item.get("severity") or "normal"),
        ))
    return findings


def full_history(account_id: int) -> list[dict[str, Any]]:
    return storage.rows(
        "SELECT id,role,content,client_message_id,created_at FROM v2_chat_history_full WHERE account_id=? ORDER BY id ASC",
        (int(account_id),),
    )


def handoff_packet(account_id: int, username: str = "") -> dict[str, Any]:
    reqs = list_requests(account_id, include_closed=True, limit=500)
    history = full_history(account_id)
    open_reqs = [r for r in reqs if r.get("state") not in {"implemented", "disapproved"}]
    lines = [
        "JANUS -> CHATGPT SUPERVISOR HANDOFF",
        "",
        "COMMAND TO CHATGPT SUPERVISOR:",
        "Review the private GitHub repository Vardath/JANUS thoroughly and review this complete server-retained JANUS chat history. Audit the current Android app and server against each JANUS capability/failure request below. Approve or disapprove each request independently. Implement only approved changes. Preserve owner control: JANUS must not edit its own code, install packages, change model/API configuration, approve maintenance, or deploy itself. Run regression tests, Java compile/APK assembly where Android is affected, server/protocol/auth/maintenance audits where relevant, update private repo progress/audit records, and update server_v2/supervisor_decisions.json with each approval/disapproval, reason, implementation state, and implemented version so JANUS can report the outcome to the owner in Messages.",
        "",
        f"PROFILE: {username or account_id}",
        f"OPEN REQUESTS: {len(open_reqs)} | TOTAL RECORDED REQUESTS: {len(reqs)} | RETAINED CHAT TURNS: {len(history)}",
        "",
        "=== CAPABILITY / FAILURE REQUESTS ===",
    ]
    if not reqs:
        lines.append("(none yet)")
    for r in reqs:
        lines.extend([
            f"REQUEST #{r['id']} [{r['state']}] severity={r['severity']} occurrences={r['occurrence_count']}",
            f"Capability: {r['capability']}",
            f"Title: {r['title']}",
            f"Detail: {r['detail']}",
            f"Evidence: {r.get('evidence') or '(none)'}",
            f"Supervisor decision: {r.get('supervisor_decision') or '(pending)'}",
            f"Decision reason: {r.get('decision_reason') or '(none)'}",
            f"Implementation: {r.get('implementation_state') or 'not_started'} {r.get('implemented_version') or ''}".strip(),
            "",
        ])
    lines.append("=== COMPLETE SERVER-RETAINED JANUS CHAT HISTORY ===")
    if not history:
        lines.append("(No complete server-side history predates this feature. History is complete from v1.08 deployment onward.)")
    for h in history:
        role = str(h.get("role") or "unknown").upper()
        lines.append(f"\n[{role}] {h.get('content') or ''}")
    packet = "\n".join(lines)
    return {
        "profile": username,
        "requests": reqs,
        "open_request_count": len(open_reqs),
        "history_count": len(history),
        "history_complete_since_feature_install": True,
        "packet": packet,
        "automatic_chatgpt_injection": False,
        "handoff_method": "copy_or_share_under_owner_control",
    }


def apply_supervisor_decisions() -> dict[str, int]:
    """Synchronize repo-authored ChatGPT Supervisor decisions after deployment.

    ChatGPT updates supervisor_decisions.json while implementing approved work in the
    private repo. The deployed server consumes those records and messages the owner.
    """
    if not DECISION_FILE.exists():
        return {"applied": 0, "ignored": 0}
    try:
        payload = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"applied": 0, "ignored": 1}
    entries = payload.get("decisions") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return {"applied": 0, "ignored": 1}
    applied = ignored = 0
    for d in entries:
        if not isinstance(d, dict):
            ignored += 1
            continue
        key = str(d.get("decision_key") or d.get("id") or "").strip()
        if not key:
            ignored += 1
            continue
        if storage.one("SELECT 1 FROM v2_supervisor_sync WHERE decision_key=?", (key,)):
            continue
        request_id = int(d.get("request_id") or 0)
        fp = str(d.get("fingerprint") or "")
        decision = str(d.get("decision") or "").lower()
        if decision not in {"approved", "disapproved", "deferred"}:
            ignored += 1
            continue
        account_id = int(d.get("account_id") or 0)
        row = None
        if account_id and request_id:
            row = storage.one("SELECT * FROM v2_capability_requests WHERE account_id=? AND id=?", (account_id, request_id))
        elif request_id:
            row = storage.one("SELECT * FROM v2_capability_requests WHERE id=?", (request_id,))
        elif fp:
            row = storage.one("SELECT * FROM v2_capability_requests WHERE fingerprint=? ORDER BY id DESC LIMIT 1", (fp,))
        if not row:
            ignored += 1
            continue
        aid = int(row["account_id"])
        reason = str(d.get("reason") or "")[:8000]
        impl = str(d.get("implementation_state") or ("implemented" if decision == "approved" else "not_applicable"))[:80]
        version = str(d.get("implemented_version") or "")[:80]
        state = "implemented" if decision == "approved" and impl == "implemented" else ("disapproved" if decision == "disapproved" else "deferred")
        with storage.db() as c:
            c.execute(
                "UPDATE v2_capability_requests SET supervisor_decision=?,decision_reason=?,implementation_state=?,implemented_version=?,state=?,updated_at=? WHERE id=?",
                (decision, reason, impl, version, state, storage.now(), int(row["id"])),
            )
            c.execute("INSERT INTO v2_supervisor_sync(decision_key,applied_at) VALUES(?,?)", (key, storage.now()))
        storage.add_message(
            aid,
            "supervisor_decision",
            f"ChatGPT Supervisor decision for request #{int(row['id'])}: {decision.upper()}\n\n{row['title']}\n\nReason: {reason or '(no reason recorded)'}\nImplementation: {impl}{(' · '+version) if version else ''}\n\nJANUS itself did not make or execute this decision.",
            "chatgpt-supervisor",
        )
        applied += 1
    return {"applied": applied, "ignored": ignored}
