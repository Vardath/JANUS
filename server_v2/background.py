from __future__ import annotations

import calendar
import os
import random
import threading
import time

from . import governance, mailer, storage
from .mind import mind
from .recursive_background import tick as recursive_tick
from .sensory_bus import ingest as ingest_sense


class BackgroundCoordinator:
    """Low-duty coordinator for the clean server mind.

    Ordinary 11-core wake/sleep cycles and nested JANUS/Fano cycles stay local and
    zero-model/API. Every core may form bounded curiosity intentions on changed wake
    cycles. This coordinator chooses a small shared subset for external observation,
    then feeds findings back through the full seven -> hemispheres -> Front -> Interface
    sensory route so all cores can independently appraise the new material.

    Default research budget is US$20/month per account: US$10 autonomous curiosity
    and US$10 reserved for user-directed research. External observation is paced;
    internal reviewing, peer exchange and curiosity formation remain zero-cost.
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self.tick_seconds = max(60, int(os.getenv("JANUS_V2_BACKGROUND_TICK_SECONDS", "300")))

    @property
    def search_estimate_usd(self) -> float:
        return max(0.001, float(os.getenv("JANUS_RESEARCH_ESTIMATED_USD_PER_CALL", "0.01")))

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="janus-v2-background", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        time.sleep(10)
        while self._running:
            try:
                self.tick()
            except Exception:
                pass
            for _ in range(max(1, self.tick_seconds // 5)):
                if not self._running:
                    break
                time.sleep(5)

    def tick(self):
        accounts = storage.rows("SELECT id,username,created_at FROM v2_accounts ORDER BY id")
        for a in accounts:
            aid = int(a["id"])
            governance.ensure_account(aid)
            recursive_tick(mind, aid)
            state = storage.one("SELECT * FROM v2_background_state WHERE account_id=?", (aid,))
            if not state:
                continue
            now = storage.now()
            self._self_assess(aid, now, state)
            self._maintenance(aid, now, state)
            self._proactive_message(aid, now, state)
            self._curiosity(aid, now, state)

    def _touch(self, aid: int, field: str, value: int):
        allowed = {"last_message_at", "last_research_at", "last_maintenance_at", "last_self_assessment_at"}
        if field not in allowed:
            return
        with storage.db() as c:
            c.execute(
                f"UPDATE v2_background_state SET {field}=?,updated_at=? WHERE account_id=?",
                (value, storage.now(), aid),
            )

    def _self_assess(self, aid: int, now: int, state):
        if now - int(state["last_self_assessment_at"] or 0) < 6 * 3600:
            return
        rel = governance.reliability(aid)
        avg = sum(float(x["consistency_score"]) for x in rel) / len(rel) if rel else 0.5
        detail = (
            f"Functional self-assessment: historical downstream consistency calibration {avg:.3f}; "
            "recursive 1|3|7 society intact; this is not a truth score or consciousness claim."
        )
        storage.add_event(aid, "front", "self_assessment", detail, detail, "background")
        self._touch(aid, "last_self_assessment_at", now)

    def _is_maintenance_owner(self, aid: int) -> bool:
        configured = os.getenv("JANUS_MAINTENANCE_OWNER_PROFILE", "").strip()
        owner = storage.account_by_identifier(configured) if configured else storage.one(
            "SELECT * FROM v2_accounts ORDER BY id ASC LIMIT 1"
        )
        return bool(owner and int(owner["id"]) == int(aid))

    def _maintenance(self, aid: int, now: int, state):
        if not self._is_maintenance_owner(aid):
            return
        interval = 90 * 86400
        last = int(state["last_maintenance_at"] or 0)
        if not last:
            account = storage.account_by_id(aid)
            last = int(account["created_at"] or now) if account else now
            self._touch(aid, "last_maintenance_at", last)
            return
        if now - last < interval:
            return
        health = mind.status(aid)
        report = {
            "proposal_kind": "quarterly_manual_review",
            "summary": "Review JANUS models, APIs, Android/server protocol compatibility, cost settings and dependency/security updates.",
            "architecture": health.get("architecture"),
            "core_count": health.get("core_count"),
            "automatic_code_changes": False,
            "automatic_deploy": False,
            "required_action": "Owner and ChatGPT review before any code or deployment change.",
        }
        storage.execute(
            "INSERT INTO v2_maintenance(account_id,report_json,review_state,created_at) VALUES(?,?,?,?)",
            (aid, storage.jdump(report), "awaiting_owner_review", now),
        )
        storage.add_message(
            aid,
            "Maintenance",
            "A quarterly JANUS maintenance review is ready for manual owner review.",
            "maintenance",
        )
        account = storage.account_by_id(aid)
        if account:
            mailer.send(
                str(account["email"]),
                "JANUS quarterly maintenance review ready",
                "JANUS has prepared its quarterly maintenance review. No code, deployment, model or API changes have been made. Open JANUS Maintenance Review and work through the proposal with ChatGPT before approving manual work.",
            )
        self._touch(aid, "last_maintenance_at", now)

    def _proactive_message(self, aid: int, now: int, state):
        if os.getenv("JANUS_MESSAGE_QUEUE", "1") != "1":
            return
        if now - int(state["last_message_at"] or 0) < 12 * 3600:
            return
        item = storage.one(
            "SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active','blocked') ORDER BY priority DESC,updated_at DESC LIMIT 1",
            (aid,),
        )
        if item:
            text = f"I still have an open thread in mind: {item['title']}." + (
                f" {str(item['detail'])[:500]}" if item["detail"] else ""
            )
            mtype = "Follow-up"
        else:
            mem = storage.one(
                "SELECT content,tier FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic') ORDER BY updated_at DESC LIMIT 1",
                (aid,),
            )
            if not mem:
                return
            text = "A continuity note may be worth revisiting: " + str(mem["content"])[:650]
            mtype = "Memory"
        recent = storage.one(
            "SELECT 1 FROM v2_messages WHERE account_id=? AND detail=? AND created_at>?",
            (aid, text, now - 7 * 86400),
        )
        if recent:
            return
        storage.add_message(aid, mtype, text, "background")
        self._touch(aid, "last_message_at", now)

    def _month_window(self, now: int):
        t = time.gmtime(now)
        start = calendar.timegm((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0))
        if t.tm_mon == 12:
            end = calendar.timegm((t.tm_year + 1, 1, 1, 0, 0, 0, 0, 0, 0))
        else:
            end = calendar.timegm((t.tm_year, t.tm_mon + 1, 1, 0, 0, 0, 0, 0, 0))
        return start, end, calendar.monthrange(t.tm_year, t.tm_mon)[1]

    def _research_budget(self, aid: int, now: int):
        total = max(0.0, float(os.getenv("JANUS_RESEARCH_MONTHLY_MAX_USD", "20")))
        autonomous = min(
            total,
            max(0.0, float(os.getenv("JANUS_AUTONOMOUS_RESEARCH_TARGET_USD", "10"))),
        )
        start, end, days = self._month_window(now)
        rows = storage.rows(
            "SELECT scope,calls FROM v2_cost_ledger WHERE account_id=? AND allowed=1 AND created_at>=? AND created_at<? AND scope IN ('background_research','foreground_web')",
            (aid, start, end),
        )
        autonomous_calls = sum(int(r["calls"] or 0) for r in rows if r["scope"] == "background_research")
        all_calls = sum(int(r["calls"] or 0) for r in rows)
        per_call = self.search_estimate_usd
        autonomous_spend = autonomous_calls * per_call
        estimated_total_spend = all_calls * per_call
        elapsed_days = max(1.0, (now - start) / 86400.0)
        paced_allowance = autonomous * (min(float(days), elapsed_days) / float(days))
        return total, autonomous, autonomous_spend, estimated_total_spend, paced_allowance

    def _recent_core_intents(self, aid: int) -> list[dict]:
        return storage.rows(
            "SELECT core_name,detail,created_at FROM v2_events WHERE account_id=? AND event_type='curiosity_intent' ORDER BY id DESC LIMIT 88",
            (aid,),
        )

    def _choose_curiosity(self, aid: int):
        intents = self._recent_core_intents(aid)
        open_item = storage.one(
            "SELECT title,detail FROM v2_continuity WHERE account_id=? AND state IN ('open','active') ORDER BY priority DESC,updated_at DESC LIMIT 1",
            (aid,),
        )
        mem = storage.one(
            "SELECT content FROM v2_memories WHERE account_id=? AND tier IN ('core','episodic','working') ORDER BY RANDOM() LIMIT 1",
            (aid,),
        )
        roll = random.random()

        if intents and roll < 0.55:
            chosen = random.choice(intents[:44])
            return (
                "autonomous_core_intent",
                "Obtain one credible new outside observation, source, current development, counterexample, video/transcript lead, or piece of evidence that could help this JANUS core evaluate its material. "
                f"Requesting core={chosen['core_name']}. {str(chosen['detail'])[:900]}",
            )
        if open_item and roll < 0.72:
            return (
                "autonomous_relevant",
                f"Find one useful current development, source, counterexample or piece of evidence relevant to: {open_item['title']} {str(open_item['detail'])[:500]}",
            )
        if mem and roll < 0.86:
            return (
                "autonomous_adjacent",
                "Explore one useful but not necessarily obvious adjacent idea, field, source, pattern or development connected to: "
                + str(mem["content"])[:650],
            )
        if roll < 0.94:
            seed = str(mem["content"])[:400] if mem else "a potentially useful topic outside the current conversation"
            return (
                "autonomous_youtube",
                "Search specifically for a credible YouTube/video source or transcript lead that could expose JANUS to a useful explanation, demonstration, lecture, documentary, interview, experiment or opposing viewpoint. Prefer substantive sources over clickbait. Topic may be relevant or adjacent: "
                + seed,
            )
        seed = str(mem["content"])[:300] if mem else (
            "science, history, technology, culture, nature, mathematics or human knowledge"
        )
        return (
            "autonomous_random",
            "Make an exploratory observation/research hop. Prefer something surprising, credible and potentially useful rather than merely topical. It may be substantially unrelated to current conversation. Include a source JANUS can revisit. Starting seed only: "
            + seed,
        )

    def _curiosity(self, aid: int, now: int, state):
        if os.getenv("JANUS_CURIOSITY_WEB", "1") != "1":
            return
        min_gap = max(600, int(os.getenv("JANUS_CURIOSITY_MIN_GAP_SECONDS", "1200")))
        if now - int(state["last_research_at"] or 0) < min_gap:
            return
        total, target, auto_spend, total_spend, paced = self._research_budget(aid, now)
        per_call = self.search_estimate_usd
        if total_spend + per_call > total:
            return
        if auto_spend + per_call > target:
            return
        if auto_spend + per_call > paced and random.random() > 0.08:
            return
        if not governance.permit(aid, "background_research", per_call):
            return

        mode, query = self._choose_curiosity(aid)
        text, sources = mind.web_research(query, aid, governed=False)
        self._touch(aid, "last_research_at", now)
        if not text:
            return

        storage.execute(
            "INSERT INTO v2_research(account_id,mode,query,result,sources_json,useful,created_at) VALUES(?,?,?,?,?,?,?)",
            (aid, mode, query, text, storage.jdump(sources), None, now),
        )

        source_labels = []
        for src in (sources or [])[:8]:
            if isinstance(src, dict):
                label = str(src.get("url") or src.get("title") or src.get("source") or "")[:240]
                if label:
                    source_labels.append(label)
        metadata = {
            "research_mode": mode,
            "query": query[:1200],
            "sources": source_labels,
            "autonomous": True,
        }
        integrated = ingest_sense(
            aid,
            "web",
            "autonomous_research",
            text,
            salience=0.55,
            uncertainty=0.5,
            novelty=0.75 if mode in {"autonomous_random", "autonomous_youtube"} else 0.55,
            metadata=metadata,
            mode="background",
        )

        memory_text = (
            f"Autonomous research ({mode.removeprefix('autonomous_')}): {text[:1400]}"
            + (" Sources: " + " | ".join(source_labels[:4]) if source_labels else "")
        )
        try:
            storage.add_memory(
                aid,
                memory_text,
                tier="trace",
                kind="autonomous_research",
                salience=0.5,
            )
        except Exception:
            pass

        summary = f"Autonomous {mode.removeprefix('autonomous_')} observation entered the full JANUS sensory route: " + text[:650]
        storage.add_event(aid, "evidence", "background_research", summary, summary, "background")
        if integrated:
            storage.add_event(
                aid,
                "front",
                "autonomous_observation_integrated",
                "A new autonomous web observation was projected through all seven specialists, both hemispheres, Front and Interface; no automatic outward action was taken.",
                mode="background",
            )


background = BackgroundCoordinator()
