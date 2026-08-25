from __future__ import annotations

import calendar
import json
import os
import time
from typing import Any

from . import storage

CORE_NAMES = ("evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface")
RESEARCH_SCOPES = ("background_research", "foreground_web")


def init_schema() -> None:
    with storage.db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS v2_core_reliability(
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              core_name TEXT NOT NULL,
              consistency_score REAL NOT NULL DEFAULT 0.5,
              observations INTEGER NOT NULL DEFAULT 0,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY(account_id,core_name)
            );
            CREATE TABLE IF NOT EXISTS v2_bridge_authority(
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              specialist TEXT NOT NULL,
              hemisphere TEXT NOT NULL,
              weight REAL NOT NULL DEFAULT 0.5,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY(account_id,specialist,hemisphere)
            );
            CREATE TABLE IF NOT EXISTS v2_cost_ledger(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              scope TEXT NOT NULL,
              calls INTEGER NOT NULL DEFAULT 1,
              estimated_usd REAL NOT NULL DEFAULT 0,
              allowed INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_cost_account_time ON v2_cost_ledger(account_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS v2_continuity(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              kind TEXT NOT NULL DEFAULT 'thread',
              state TEXT NOT NULL DEFAULT 'open',
              priority INTEGER NOT NULL DEFAULT 50,
              title TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '',
              tags_json TEXT NOT NULL DEFAULT '[]',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_v2_continuity_account ON v2_continuity(account_id,state,priority DESC,id DESC);
            CREATE TABLE IF NOT EXISTS v2_continuity_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              item_id INTEGER NOT NULL REFERENCES v2_continuity(id) ON DELETE CASCADE,
              event_type TEXT NOT NULL,
              old_state TEXT,
              new_state TEXT,
              note TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v2_claim_evidence(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              claim_id INTEGER NOT NULL REFERENCES v2_claims(id) ON DELETE CASCADE,
              account_id INTEGER NOT NULL REFERENCES v2_accounts(id) ON DELETE CASCADE,
              evidence_kind TEXT NOT NULL,
              summary TEXT NOT NULL,
              source_uri TEXT NOT NULL DEFAULT '',
              result TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v2_background_state(
              account_id INTEGER PRIMARY KEY REFERENCES v2_accounts(id) ON DELETE CASCADE,
              last_message_at INTEGER NOT NULL DEFAULT 0,
              last_research_at INTEGER NOT NULL DEFAULT 0,
              last_maintenance_at INTEGER NOT NULL DEFAULT 0,
              last_self_assessment_at INTEGER NOT NULL DEFAULT 0,
              updated_at INTEGER NOT NULL
            );
            """
        )


def ensure_account(account_id: int) -> None:
    ts = storage.now()
    with storage.db() as c:
        for core in CORE_NAMES:
            c.execute(
                "INSERT OR IGNORE INTO v2_core_reliability(account_id,core_name,consistency_score,observations,updated_at) VALUES(?,?,?,?,?)",
                (int(account_id), core, 0.5, 0, ts),
            )
        defaults = {
            "evidence": (0.72,0.28), "logic": (0.72,0.28), "counterpoint": (0.68,0.32),
            "context": (0.32,0.68), "memory": (0.35,0.65), "novelty": (0.30,0.70), "safety": (0.50,0.50),
        }
        for specialist, (left,right) in defaults.items():
            for hemi, weight in (("left_hemisphere",left),("right_hemisphere",right)):
                c.execute(
                    "INSERT OR IGNORE INTO v2_bridge_authority(account_id,specialist,hemisphere,weight,updated_at) VALUES(?,?,?,?,?)",
                    (int(account_id), specialist, hemi, weight, ts),
                )
        c.execute("INSERT OR IGNORE INTO v2_background_state(account_id,updated_at) VALUES(?,?)", (int(account_id), ts))


def reliability(account_id: int) -> list[dict[str, Any]]:
    ensure_account(account_id)
    return storage.rows("SELECT core_name,consistency_score,observations,updated_at FROM v2_core_reliability WHERE account_id=? ORDER BY core_name", (int(account_id),))


def bridge_authority(account_id: int) -> list[dict[str, Any]]:
    ensure_account(account_id)
    return storage.rows("SELECT specialist,hemisphere,weight,updated_at FROM v2_bridge_authority WHERE account_id=? ORDER BY specialist,hemisphere", (int(account_id),))


def record_consistency(account_id: int, core_names: list[str], consistent: bool, strength: float = 1.0) -> None:
    ensure_account(account_id)
    target = 0.68 if consistent else 0.32
    alpha = min(0.08, max(0.005, 0.02 * float(strength)))
    ts = storage.now()
    with storage.db() as c:
        for core in core_names:
            row = c.execute("SELECT consistency_score,observations FROM v2_core_reliability WHERE account_id=? AND core_name=?", (int(account_id), core)).fetchone()
            if not row:
                continue
            old = float(row["consistency_score"])
            new = max(0.05, min(0.95, old + alpha * (target - old)))
            c.execute("UPDATE v2_core_reliability SET consistency_score=?,observations=observations+1,updated_at=? WHERE account_id=? AND core_name=?", (new, ts, int(account_id), core))


def adapt_bridge(account_id: int, specialist: str, hemisphere: str, direction: float) -> None:
    ensure_account(account_id)
    with storage.db() as c:
        row = c.execute("SELECT weight FROM v2_bridge_authority WHERE account_id=? AND specialist=? AND hemisphere=?", (int(account_id), specialist, hemisphere)).fetchone()
        if not row:
            return
        new = max(0.2, min(0.8, float(row["weight"]) + max(-0.02, min(0.02, direction))))
        c.execute("UPDATE v2_bridge_authority SET weight=?,updated_at=? WHERE account_id=? AND specialist=? AND hemisphere=?", (new, storage.now(), int(account_id), specialist, hemisphere))


def _month_window(now: int) -> tuple[int, int]:
    t = time.gmtime(now)
    start = calendar.timegm((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0))
    if t.tm_mon == 12:
        end = calendar.timegm((t.tm_year + 1, 1, 1, 0, 0, 0, 0, 0, 0))
    else:
        end = calendar.timegm((t.tm_year, t.tm_mon + 1, 1, 0, 0, 0, 0, 0, 0))
    return start, end


def _research_plan(account_id: int, now: int | None = None) -> dict[str, float]:
    now = storage.now() if now is None else int(now)
    start, end = _month_window(now)
    per_call = max(0.001, float(os.getenv("JANUS_RESEARCH_ESTIMATED_USD_PER_CALL", "0.01")))
    total_cap = max(0.0, float(os.getenv("JANUS_RESEARCH_MONTHLY_MAX_USD", "20")))
    autonomous_cap = min(total_cap, max(0.0, float(os.getenv("JANUS_AUTONOMOUS_RESEARCH_TARGET_USD", "10"))))
    rows = storage.rows(
        "SELECT scope,coalesce(sum(calls),0) calls FROM v2_cost_ledger WHERE account_id=? AND allowed=1 AND created_at>=? AND created_at<? AND scope IN ('background_research','foreground_web') GROUP BY scope",
        (int(account_id), start, end),
    )
    calls = {str(r["scope"]): int(r["calls"] or 0) for r in rows}
    background_calls = calls.get("background_research", 0)
    foreground_calls = calls.get("foreground_web", 0)
    background_usd = background_calls * per_call
    foreground_usd = foreground_calls * per_call
    total_usd = background_usd + foreground_usd
    return {
        "per_call_usd": per_call,
        "monthly_max_usd": total_cap,
        "autonomous_target_usd": autonomous_cap,
        "background_calls": float(background_calls),
        "foreground_calls": float(foreground_calls),
        "background_estimated_usd": background_usd,
        "foreground_estimated_usd": foreground_usd,
        "total_estimated_usd": total_usd,
        "remaining_total_usd": max(0.0, total_cap - total_usd),
        "remaining_autonomous_usd": max(0.0, autonomous_cap - background_usd),
    }


def cost_status(account_id: int) -> dict[str, Any]:
    start = storage.now() - 86400
    rows = storage.rows("SELECT scope,sum(calls) calls,sum(estimated_usd) usd,sum(CASE WHEN allowed=0 THEN calls ELSE 0 END) denied FROM v2_cost_ledger WHERE account_id=? AND created_at>? GROUP BY scope", (int(account_id), start))
    scopes = {r["scope"]: {"calls": int(r["calls"] or 0), "estimated_usd": float(r["usd"] or 0), "denied": int(r["denied"] or 0)} for r in rows}
    return {
        "mode": os.getenv("JANUS_COMPUTE_BUDGET", "balanced"),
        "today": scopes,
        "research_month": _research_plan(account_id),
        "background_daily_call_cap": int(os.getenv("JANUS_BACKGROUND_DAILY_CALL_CAP", "12")),
        "background_daily_token_cap": int(os.getenv("JANUS_BACKGROUND_DAILY_TOKEN_CAP", "20000")),
        "curiosity_daily_search_cap": int(os.getenv("JANUS_CURIOSITY_DAILY_SEARCH_CAP", "40")),
        "background_multi_core_image_generation": False,
    }


def permit(account_id: int, scope: str, estimated_usd: float = 0.0) -> bool:
    now = storage.now()
    day_start = now - 86400

    if scope in RESEARCH_SCOPES:
        plan = _research_plan(account_id, now)
        normalized_cost = float(plan["per_call_usd"])
        total_ok = plan["total_estimated_usd"] + normalized_cost <= plan["monthly_max_usd"] + 1e-9
        background_ok = True
        if scope == "background_research":
            background_ok = plan["background_estimated_usd"] + normalized_cost <= plan["autonomous_target_usd"] + 1e-9
            cap = int(os.getenv("JANUS_CURIOSITY_DAILY_SEARCH_CAP", "40"))
        else:
            cap = int(os.getenv("JANUS_FOREGROUND_DAILY_CALL_CAP", "500"))
        row = storage.one(
            "SELECT coalesce(sum(calls),0) n FROM v2_cost_ledger WHERE account_id=? AND scope=? AND allowed=1 AND created_at>?",
            (int(account_id), scope, day_start),
        )
        daily_ok = int(row["n"] if row else 0) < cap
        allowed = bool(total_ok and background_ok and daily_ok)
        storage.execute(
            "INSERT INTO v2_cost_ledger(account_id,scope,calls,estimated_usd,allowed,created_at) VALUES(?,?,?,?,?,?)",
            (int(account_id), scope, 1, normalized_cost, int(allowed), now),
        )
        return allowed

    if scope == "background_model":
        cap = int(os.getenv("JANUS_BACKGROUND_DAILY_CALL_CAP", "12"))
    elif scope == "image":
        cap = int(os.getenv("JANUS_IMAGE_DAILY_CAP", "20"))
    else:
        cap = int(os.getenv("JANUS_FOREGROUND_DAILY_CALL_CAP", "500"))
    row = storage.one("SELECT coalesce(sum(calls),0) n FROM v2_cost_ledger WHERE account_id=? AND scope=? AND allowed=1 AND created_at>?", (int(account_id), scope, day_start))
    allowed = int(row["n"] if row else 0) < cap
    storage.execute("INSERT INTO v2_cost_ledger(account_id,scope,calls,estimated_usd,allowed,created_at) VALUES(?,?,?,?,?,?)", (int(account_id), scope, 1, float(estimated_usd), int(allowed), now))
    return allowed


def continuity_list(account_id: int, open_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    where = "account_id=?" + (" AND state IN ('open','active','blocked')" if open_only else "")
    items = storage.rows(f"SELECT id,kind,state,priority,title,detail,tags_json,created_at,updated_at FROM v2_continuity WHERE {where} ORDER BY priority DESC,updated_at DESC LIMIT ?", (int(account_id), max(1,min(200,limit))))
    for x in items:
        x["tags"] = json.loads(x.pop("tags_json") or "[]")
    return items


def continuity_create(account_id: int, title: str, detail: str = "", kind: str = "thread", priority: int = 50, tags: list[str] | None = None) -> dict[str, Any]:
    ts = storage.now()
    item_id = storage.execute("INSERT INTO v2_continuity(account_id,kind,state,priority,title,detail,tags_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (int(account_id),kind,"open",max(0,min(100,int(priority))),title[:180],detail[:12000],json.dumps(tags or []),ts,ts))
    storage.execute("INSERT INTO v2_continuity_events(item_id,event_type,new_state,note,created_at) VALUES(?,?,?,?,?)", (item_id,"created","open","",ts))
    return continuity_get(account_id,item_id)


def continuity_get(account_id: int, item_id: int) -> dict[str, Any]:
    row = storage.one("SELECT id,kind,state,priority,title,detail,tags_json,created_at,updated_at FROM v2_continuity WHERE account_id=? AND id=?", (int(account_id),int(item_id)))
    if not row:
        raise KeyError(item_id)
    d = dict(row)
    d["tags"] = json.loads(d.pop("tags_json") or "[]")
    return d


def continuity_state(account_id: int, item_id: int, new_state: str, note: str = "") -> dict[str, Any]:
    allowed = {"open","active","blocked","deferred","done","closed"}
    if new_state not in allowed:
        raise ValueError("invalid continuity state")
    old = continuity_get(account_id,item_id)["state"]
    ts = storage.now()
    with storage.db() as c:
        c.execute("UPDATE v2_continuity SET state=?,updated_at=? WHERE account_id=? AND id=?", (new_state,ts,int(account_id),int(item_id)))
        c.execute("INSERT INTO v2_continuity_events(item_id,event_type,old_state,new_state,note,created_at) VALUES(?,?,?,?,?,?)", (int(item_id),"state",old,new_state,note[:4000],ts))
    return continuity_get(account_id,item_id)
