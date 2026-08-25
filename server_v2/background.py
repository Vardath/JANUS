from __future__ import annotations

import calendar
import os
import random
import threading
import time

from . import governance, mailer, storage
from .mind import mind
from .recursive_background import tick as recursive_tick


class BackgroundCoordinator:
    """Low-duty coordinator for the clean server mind.

    Ordinary 11-core wake/sleep cycles and nested JANUS/Fano cycles stay local and
    zero-model/API. Cores may continuously form curiosity intentions; this coordinator
    executes only a bounded shared subset as external research.

    Default research budget is US$20/month per account: US$10 autonomous curiosity
    and US$10 reserved for user-directed research. The autonomous half targets about
    1,000 web-search calls/month at the current US$0.01/search planning estimate.
    The hard total ceiling is never intentionally exceeded by background curiosity.
    """

    SEARCH_ESTIMATE_USD = 0.01

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self.tick_seconds = max(60, int(os.getenv("JANUS_V2_BACKGROUND_TICK_SECONDS", "300")))

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="janus-v2-background", daemon=True)
        self._thread.start()

    def stop(self): self._running = False

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
            recursive_tick(mind, aid)
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
        detail = f"Functional self-assessment: historical downstream consistency calibration {avg:.3f}; recursive 1|3|7 society intact; this is not a truth score or consciousness claim."
        storage.add_event(aid,"front","self_assessment",detail,detail,"background")
        self._touch(aid,"last_self_assessment_at",now)

    def _is_maintenance_owner(self, aid: int) -> bool:
        configured=os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE","").strip()
        owner=storage.account_by_identifier(configured) if configured else storage.one("SELECT * FROM v2_accounts ORDER BY id ASC LIMIT 1")
        return bool(owner and int(owner["id"])==int(aid))

    def _maintenance(self, aid: int, now: int, state):
        if not self._is_maintenance_owner(aid): return
        interval = 90 * 86400
        last = int(state["last_maintenance_at"] or 0)
        if not last:
            account = storage.account_by_id(aid)
            last = int(account["created_at"] or now) if account else now
            self._touch(aid,"last_maintenance_at",last); return
        if now - last < interval: return
        health = mind.status(aid)
        report = {"proposal_kind":"quarterly_manual_review","summary":"Review JANUS models, APIs, Android/server protocol compatibility, cost settings and dependency/security updates.","architecture":health.get("architecture"),"core_count":health.get("core_count"),"automatic_code_changes":False,"automatic_deploy":False,"required_action":"Owner and ChatGPT review before any code or deployment change."}
        storage.execute("INSERT INTO v2_maintenance(account_id,report_json,review_state,created_at) VALUES(?,?,?,?)", (aid,storage.jdump(report),"awaiting_owner_review",now))
        storage.add_message(aid,"Maintenance","A quarterly JANUS maintenance review is ready for manual owner review.","maintenance")
        account=storage.account_by_id(aid)
        if account: mailer.send(str(account["email"]),"JANUS quarterly maintenance review ready","JANUS has prepared its quarterly maintenance review. No code, deployment, model or API changes have been made. Open JANUS Maintenance Review and work through the proposal with ChatGPT before approving manual work.")
        self._touch(aid,"last_maintenance_at",now)

    def _proactive_message(self, aid: int, now: int, state):
        if os.getenv("JANUS_MESSAGE_QUEUE","1") != "1" or now - int(state["last_message_at"] or 0) < 12 * 3600: return
        item = storage.one("SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active','blocked') ORDER BY priority DESC,updated_at DESC LIMIT 1", (aid,))
        if item:
            text = f"I still have an open thread in mind: {item['title']}." + (f" {str(item['detail'])[:500]}" if item["detail"] else ""); mtype="Follow-up"
        else:
            mem = storage.one("SELECT content,tier FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic') ORDER BY updated_at DESC LIMIT 1", (aid,))
            if not mem: return
            text="A continuity note may be worth revisiting: "+str(mem["content"])[:650]; mtype="Memory"
        if storage.one("SELECT 1 FROM v2_messages WHERE account_id=? AND detail=? AND created_at>?", (aid,text,now-7*86400)): return
        storage.add_message(aid,mtype,text,"background"); self._touch(aid,"last_message_at",now)

    def _month_window(self, now: int):
        t=time.gmtime(now); start=calendar.timegm((t.tm_year,t.tm_mon,1,0,0,0,0,0,0))
        if t.tm_mon==12: end=calendar.timegm((t.tm_year+1,1,1,0,0,0,0,0,0))
        else: end=calendar.timegm((t.tm_year,t.tm_mon+1,1,0,0,0,0,0,0))
        return start,end,calendar.monthrange(t.tm_year,t.tm_mon)[1]

    def _research_budget(self, aid: int, now: int):
        total=max(0.0,float(os.getenv("JANUS_RESEARCH_MONTHLY_MAX_USD","20")))
        autonomous=min(total,max(0.0,float(os.getenv("JANUS_AUTONOMOUS_RESEARCH_TARGET_USD","10"))))
        start,end,days=self._month_window(now)
        rows=storage.rows("SELECT mode FROM v2_research WHERE account_id=? AND created_at>=? AND created_at<?",(aid,start,end))
        autonomous_calls=sum(1 for r in rows if str(r["mode"]).startswith("autonomous_"))
        all_calls=len(rows)
        autonomous_spend=autonomous_calls*self.SEARCH_ESTIMATE_USD
        estimated_total_spend=all_calls*self.SEARCH_ESTIMATE_USD
        # Pace autonomous use across the month. Unused allowance carries forward,
        # so JANUS can research more after quiet periods without exceeding the target.
        elapsed_days=max(1.0,(now-start)/86400.0)
        paced_allowance=autonomous*(min(float(days),elapsed_days)/float(days))
        return total,autonomous,autonomous_spend,estimated_total_spend,paced_allowance

    def _choose_curiosity(self, aid: int):
        open_item=storage.one("SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active') ORDER BY priority DESC,updated_at DESC LIMIT 1",(aid,))
        mem=storage.one("SELECT content FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic') ORDER BY RANDOM() LIMIT 1",(aid,))
        roll=random.random()
        if open_item and roll < 0.65:
            return "autonomous_relevant",f"Find one useful current development, source, counterexample or piece of evidence relevant to: {open_item['title']} {str(open_item['detail'])[:500]}"
        if mem and roll < 0.90:
            return "autonomous_adjacent","Explore one useful but not necessarily obvious adjacent idea, field, source, pattern or development connected to: "+str(mem["content"])[:650]
        seed=str(mem["content"])[:300] if mem else "science, history, technology, culture, nature, mathematics or human knowledge"
        return "autonomous_random","Make an exploratory research hop. Prefer something surprising, credible and potentially useful rather than merely topical. It may be unrelated. Starting seed only: "+seed

    def _curiosity(self, aid: int, now: int, state):
        if os.getenv("JANUS_CURIOSITY_WEB","1") != "1": return
        # Wake/review can occur every few minutes, but paid searches are paced separately.
        min_gap=max(600,int(os.getenv("JANUS_CURIOSITY_MIN_GAP_SECONDS","1200")))
        if now-int(state["last_research_at"] or 0)<min_gap: return
        total,target,auto_spend,total_spend,paced=self._research_budget(aid,now)
        if total_spend+self.SEARCH_ESTIMATE_USD>total: return
        if auto_spend+self.SEARCH_ESTIMATE_USD>target: return
        # Normally stay near the $10/month autonomous trajectory. A small stochastic
        # chance prevents clockwork behavior while still guaranteeing occasional wandering.
        if auto_spend+self.SEARCH_ESTIMATE_USD>paced and random.random()>0.08: return
        if not governance.permit(aid,"background_research",self.SEARCH_ESTIMATE_USD): return
        mode,query=self._choose_curiosity(aid)
        text,sources=mind.web_research(query,aid,governed=False)
        self._touch(aid,"last_research_at",now)
        if not text: return
        storage.execute("INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",(aid,mode,query,text,storage.jdump(sources),None,now))
        summary=f"Autonomous {mode.removeprefix('autonomous_')} research found: "+text[:700]
        # Evidence records provenance; all recursive cores see the retained society state
        # on subsequent wake passes and independently appraise what matters to retain.
        storage.add_event(aid,"evidence","background_research",summary,summary,"background")


background=BackgroundCoordinator()
