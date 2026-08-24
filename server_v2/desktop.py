from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, Query

from . import auth, storage, topology
from .mind import mind

router = APIRouter()


def _account(authorization: Optional[str]):
    return auth.require_account(authorization)


def _runtime_payload(account_id: int) -> dict[str, Any]:
    rt = mind.status(account_id)
    online = int(rt.get("remote_clients") or 0)
    registered = int(rt.get("registered_clients") or 0)
    rt["topology"] = "1|3|7"
    rt["mechanical_topology"] = "7 → 2 → 1 → 1"
    rt["sync_state"] = "connected" if online else ("registered-offline" if registered else "awaiting-device")
    rt["interface_awake"] = rt.get("phase") == "wake"
    rt["interface_available"] = True
    cores = rt.get("cores") or {}
    for name, core in cores.items():
        core["processing_mode"] = "active" if rt.get("phase") == "wake" else "resting"
        core["awake"] = rt.get("phase") == "wake"
        core["pending_messages"] = 0
        core["last_output"] = str(core.get("summary") or "")
        canonical = "front" if name == "consensus" else name
        core["fano"] = topology.metadata(canonical)
        if name == "consensus":
            core["compatibility_alias"] = True
            core["alias_for"] = "front"
    return rt


@router.get("/desktop/runtime-cores")
def runtime_cores(authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization); rt = _runtime_payload(int(a["id"]))
    return {"profile": a["username"], "architecture": rt["architecture"], "conceptual_topology": "1|3|7", "mechanical_flow": rt["mechanical_flow"], "runtime": rt}


@router.get("/desktop/cores")
def cores(authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization); rt = _runtime_payload(int(a["id"]))
    # The compatibility alias remains available in runtime maps for old clients but
    # is omitted from the canonical core list so the product always displays 11.
    canonical = [core for name, core in rt["cores"].items() if name != "consensus"]
    return {
        "profile": a["username"], "architecture": rt["architecture"],
        "conceptual_topology": "1|3|7", "mechanical_flow": rt["mechanical_flow"],
        "cores": canonical, "core_count": 11, "fano_lines": topology.FANO_LINES,
        "legacy_aliases": {"consensus": "front"},
    }


@router.get("/desktop/memory")
def memory(limit: int = Query(default=80, ge=1, le=200), authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization); items = storage.list_memories(int(a["id"]), limit)
    for x in items:
        x["level"] = x.get("tier", "working")
        x["role"] = x.get("kind", "memory")
    return {"profile": a["username"], "items": items, "promotion_ladder": ["trace", "working", "episodic", "core"]}


@router.get("/desktop/activity")
def activity(limit: int = Query(default=80, ge=1, le=100), authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization)
    items = storage.rows("SELECT id,event_type,core_name AS source,core_name,mode,public_detail AS detail,created_at FROM v2_events WHERE account_id=? ORDER BY id DESC LIMIT ?", (int(a["id"]), limit))
    return {"profile": a["username"], "items": items}


@router.get("/desktop/core-observe")
def core_observe(
    mode: str = Query(default="all"), limit: int = Query(default=180, ge=1, le=500), core: str = Query(default="all"),
    authorization: Optional[str] = Header(default=None), username: str | None = None,
):
    a = _account(authorization); aid = int(a["id"]); args: list[Any] = [aid]; where = "account_id=?"
    if mode not in {"all", "thoughts", "interactions"}:
        where += " AND mode=?"; args.append(mode)
    elif mode == "interactions":
        where += " AND event_type LIKE '%interaction%'"
    elif mode == "thoughts":
        where += " AND event_type NOT LIKE '%interaction%'"
    if core != "all":
        if core == "consensus": core = "front"
        where += " AND core_name=?"; args.append(core)
    args.append(limit)
    items = storage.rows(f"SELECT id,core_name,event_type,mode,public_detail AS detail,created_at FROM v2_events WHERE {where} ORDER BY id DESC LIMIT ?", args)
    return {"profile": a["username"], "items": items, "externalizable_only": True}


@router.get("/desktop/observe")
def observe(authorization: Optional[str] = Header(default=None), username: str | None = None):
    return core_observe(mode="all", limit=180, core="all", authorization=authorization, username=username)


@router.get("/desktop/home")
def home(authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization); aid = int(a["id"]); rt = _runtime_payload(aid)
    unread = storage.one("SELECT count(*) n FROM v2_messages WHERE account_id=? AND state='unread'", (aid,))
    latest = storage.one("SELECT event_type,public_detail AS detail,created_at FROM v2_events WHERE account_id=? ORDER BY id DESC LIMIT 1", (aid,))
    return {
        "profile": a["username"], "status": "Active" if rt["phase"] == "wake" else "Dormant",
        "architecture": "11-core 1|3|7", "conceptual_topology": "1|3|7", "mechanical_flow": rt["mechanical_flow"],
        "unread_messages": int(unread["n"] if unread else 0), "latest_activity": dict(latest) if latest else None,
        "background_interval_minutes": 15, "core_phase": rt["phase"], "core_runtime": rt,
        "external_api_budget_used_by_core_cycle": 0, "messaging_action": True,
    }


@router.get("/desktop/settings")
def settings(authorization: Optional[str] = Header(default=None), username: str | None = None):
    a = _account(authorization)
    return {
        "profile": a["username"], "background_interval_minutes": 15, "wake_seconds": mind.wake_seconds, "sleep_seconds": mind.sleep_seconds,
        "server_background_model_calls": 0, "paid_background_reflection": False, "sync_policy": "selective-no-overwrite",
        "identity_core_protected": True, "background_multi_core_image_generation": False,
        "conceptual_topology": "1|3|7", "mechanical_flow": "7 -> 2 -> 1 -> 1", "front_core": "front",
    }
