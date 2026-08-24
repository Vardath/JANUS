from __future__ import annotations

import os
import threading
import time

from . import governance, mailer, storage
from .mind import mind


class BackgroundCoordinator:
    """Low-duty coordinator for the clean server mind.

    Ordinary 11-core wake/sleep cycles remain deterministic and zero-API. This
    coordinator separately handles bounded curiosity research, useful proactive
    messages, functional self-assessment records and owner-gated maintenance.
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self.tick_seconds = max(60, int(os.getenv("JANUS_V2_BACKGROUND_TICK_SECONDS", "300")))

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="janus-v2-background", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        time.sleep(10)
        while self._running:
            try: self.tick()
            except Exception: pass
            for _ in range(max(1, self.tick_seconds // 5)):
                if not self._running: break
                time.sleep(5)

    def tick(self):
        accounts = storage.rows("SELECT id,username,created_at FROM v2_accounts ORDER BY id")
        for a in accounts:
            aid = int(a["id"])
            governance.ensure_account(aid)
            state = storage.one("SELECT * FROM v2_background_state WHERE account_id=?", (aid,))
            if not state: continue
            now = storage.now()
            self._self_assess(aid, now, state)
            self._maintenance(aid, now, state)
            self._proactive_message(aid, now, state)
            self._curiosity(aid, now, state)

    def _touch(self, aid: int, field: str, value: int):
        allowed = {"last_message_at","last_research_at","last_maintenance_at","last_self_assessment_at"}
        if field not in allowed: return
        with storage.db() as c:
            c.execute(f"UPDATE v2_background_state SET {field}=?,updated_at=? WHERE account_id=?", (value,storage.now(),aid))

    def _self_assess(self, aid: int, now: int, state):
        if now - int(state["last_self_assessment_at"] or 0) < 6 * 3600: return
        rel = governance.reliability(aid)
        avg = sum(float(x["consistency_score"]) for x in rel)/len(rel) if rel else 0.5
        detail = f"Functional self-assessment: historical downstream consistency calibration {avg:.3f}; architecture intact at 7 -> 2 -> 1 -> 1; this is not a truth score or consciousness claim."
        storage.add_event(aid,"consensus","self_assessment",detail,detail,"background")
        self._touch(aid,"last_self_assessment_at",now)

    def _is_maintenance_owner(self, aid: int) -> bool:
        configured=os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE","").strip()
        if configured:
            owner=storage.account_by_identifier(configured)
        else:
            owner=storage.one("SELECT * FROM v2_accounts ORDER BY id ASC LIMIT 1")
        return bool(owner and int(owner["id"])==int(aid))

    def _maintenance(self, aid: int, now: int, state):
        if not self._is_maintenance_owner(aid): return
        interval = 90 * 86400
        last = int(state["last_maintenance_at"] or 0)
        if not last:
            account = storage.account_by_id(aid)
            last = int(account["created_at"] or now) if account else now
            self._touch(aid,"last_maintenance_at",last)
            return
        if now - last < interval: return
        health = mind.status(aid)
        report = {
            "proposal_kind":"quarterly_manual_review",
            "summary":"Review JANUS models, APIs, Android/server protocol compatibility, cost settings and dependency/security updates.",
            "architecture":health.get("architecture"),
            "core_count":health.get("core_count"),
            "automatic_code_changes":False,
            "automatic_deploy":False,
            "required_action":"Owner and ChatGPT review before any code or deployment change.",
        }
        storage.execute("INSERT INTO v2_maintenance(account_id,report_json,review_state,created_at) VALUES(?,?,?,?)", (aid,storage.jdump(report),"awaiting_owner_review",now))
        storage.add_message(aid,"Maintenance","A quarterly JANUS maintenance review is ready for manual owner review.","maintenance")
        account=storage.account_by_id(aid)
        if account:
            mailer.send(str(account["email"]),"JANUS quarterly maintenance review ready","JANUS has prepared its quarterly maintenance review. No code, deployment, model or API changes have been made. Open JANUS Maintenance Review and work through the proposal with ChatGPT before approving manual work.")
        self._touch(aid,"last_maintenance_at",now)

    def _proactive_message(self, aid: int, now: int, state):
        if os.getenv("JANUS_MESSAGE_QUEUE","1") != "1": return
        if now - int(state["last_message_at"] or 0) < 12 * 3600: return
        item = storage.one("SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active','blocked') ORDER BY priority DESC,updated_at DESC LIMIT 1", (aid,))
        if item:
            text = f"I still have an open thread in mind: {item['title']}." + (f" {str(item['detail'])[:500]}" if item["detail"] else "")
            mtype = "Follow-up"
        else:
            mem = storage.one("SELECT content,tier FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic') ORDER BY updated_at DESC LIMIT 1", (aid,))
            if not mem: return
            text = "A continuity note may be worth revisiting: " + str(mem["content"])[:650]
            mtype = "Memory"
        recent = storage.one("SELECT 1 FROM v2_messages WHERE account_id=? AND detail=? AND created_at>?", (aid,text,now-7*86400))
        if recent: return
        storage.add_message(aid,mtype,text,"background")
        self._touch(aid,"last_message_at",now)

    def _curiosity(self, aid: int, now: int, state):
        if os.getenv("JANUS_CURIOSITY_WEB","1") != "1": return
        min_gap = max(3600, int(os.getenv("JANUS_CURIOSITY_MIN_GAP_SECONDS","7200")))
        if now - int(state["last_research_at"] or 0) < min_gap: return
        if not governance.permit(aid,"background_research",0.002): return
        open_item = storage.one("SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active') ORDER BY priority DESC,updated_at DESC LIMIT 1", (aid,))
        if open_item:
            query = f"Find one useful current development relevant to this JANUS continuity thread: {open_item['title']} {str(open_item['detail'])[:500]}"
            mode = "relevant"
        else:
            mem = storage.one("SELECT content FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic') ORDER BY updated_at DESC LIMIT 1", (aid,))
            if not mem: return
            query = "Find one useful current development connected to this durable context: " + str(mem["content"])[:700]
            mode = "adjacent"
        text, sources = mind.web_research(query, aid, governed=False)
        if not text:
            self._touch(aid,"last_research_at",now)
            return
        storage.execute("INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)", (aid,mode,query,text,storage.jdump(sources),None,now))
        summary = "Background research found a potentially useful update: " + text[:700]
        storage.add_event(aid,"evidence","background_research",summary,summary,"background")
        self._touch(aid,"last_research_at",now)


background = BackgroundCoordinator()
