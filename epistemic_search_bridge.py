"""Bridge JANUS epistemic self-regulation to bounded relevant web curiosity.

A low-productivity self-assessment may request fresh external evidence. This does
not bypass curiosity daily caps; it only allows a shorter cooldown and forces the
search mode to remain relevant to the current unresolved work.
"""
from __future__ import annotations

import json
import os
import time


def _request_relevant(profile: str, reason: str):
    import curiosity_search as cs
    if not cs.ENABLED or not os.environ.get("OPENAI_API_KEY", "").strip():
        return None
    counts=cs._counts_today(profile)
    if counts.get("total",0)>=cs.DAILY_CAP or counts.get("relevant",0)>=cs.RELEVANT_CAP:
        return None
    # Self-regulation can search sooner than ordinary curiosity, but never more
    # often than once per quarter of the ordinary gap and never under 30 min.
    regulator_gap=max(1800, cs.MIN_GAP_SECONDS//4)
    if cs._seconds_since_last(profile)<regulator_gap:
        return None
    deliberation=cs._active_deliberation(profile)
    recent=cs._recent_user_text(profile,12)
    seed=deliberation or (recent[0] if recent else "the current unresolved JANUS reasoning task")
    query=("Find current, reliable external evidence that could resolve, falsify, or materially change this unresolved claim/task: " + seed[:1200])
    rationale=("JANUS self-assessment detected low epistemic productivity and requested fresh grounding. " + str(reason)[:700])
    stamp=cs._now()
    with cs._db() as c:
        cur=c.execute("INSERT INTO janus_curiosity_searches(profile_id,mode,query,rationale,status,created_at) VALUES(?,?,?,?, 'pending', ?)",(profile,"relevant",query[:3000],rationale[:1000],stamp))
        row_id=int(cur.lastrowid)
    key=f"{profile}:{row_id}"
    with cs._lock:
        if key in cs._inflight:return None
        cs._inflight.add(key)
    cs._event(profile,"curiosity_search_started",f"JANUS self-regulation requested a relevant web search. Why: {rationale} Query: {query[:1000]}")
    import threading
    t=threading.Thread(target=cs._perform,args=(profile,"relevant",query,rationale,row_id),daemon=True,name=f"janus-regulation-web-{row_id}")
    t.start()
    return {"id":row_id,"mode":"relevant","query":query,"rationale":rationale,"source":"epistemic_regulation"}


def install(app):
    import self_assessment as sa
    if getattr(sa,"_epistemic_search_bridge_installed",False):return app
    original=sa.assess_once

    def assessed_with_search():
        result=original()
        if not isinstance(result,dict) or not result.get("regulation_active"):
            return result
        reason=str(result.get("summary") or "low epistemic productivity")
        scheduled=[]
        try:
            with sa._db() as c:profiles=sa._profiles(c)
            for profile in profiles:
                item=_request_relevant(profile,reason)
                if item:scheduled.append(item)
        except Exception:
            pass
        result["regulation_searches"]=scheduled
        return result

    sa.assess_once=assessed_with_search
    sa._epistemic_search_bridge_installed=True
    app.state.janus_epistemic_search_bridge=True
    return app
