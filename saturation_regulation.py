"""Escalate JANUS self-assessment from diagnosis into saturation escape.

When integration/critique has materially outrun fresh grounding, retain a compact
checkpoint of the active task, suppress recursive feedback, and force the next
work toward evidence/logic/memory/novelty. The existing epistemic-search bridge
may then request bounded relevant web evidence. This is functional regulation,
not a claim of subjective stress or boredom.
"""
from __future__ import annotations

import json, os, sqlite3, time
from datetime import datetime, timezone

DB_PATH=os.environ.get("JANUS_DB_PATH","/data/janus.sqlite3")
SATURATION_IMBALANCE=float(os.environ.get("JANUS_SATURATION_IMBALANCE","1.80"))
SATURATION_EXPLORATORY=float(os.environ.get("JANUS_SATURATION_EXPLORATORY","0.45"))
SATURATION_COOLDOWN=max(300,int(os.environ.get("JANUS_SATURATION_COOLDOWN_SECONDS","1800")))


def _now(): return datetime.now(timezone.utc).isoformat()

def _db():
    c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS janus_saturation_state(profile_id TEXT PRIMARY KEY,last_at REAL NOT NULL DEFAULT 0,last_key TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL)")
    return c

def _active_task(profile):
    try:
        with _db() as c:
            return c.execute("SELECT id,topic,current_summary,pass_count FROM janus_deliberation_tasks WHERE profile_id=? AND status='active' ORDER BY id DESC LIMIT 1",(profile,)).fetchone()
    except Exception:return None

def _exploratory_pressure(cycle):
    vals=[]
    try:
        for n in ("counterpoint","left_hemisphere","right_hemisphere","consensus","interface"):
            f=cycle.cores[n].fano.processing_pressure()
            vals.append(float(f.get("exploratory") or 0.0))
    except Exception:return 0.0
    return sum(vals)/max(1,len(vals))

def _recently_handled(profile,key):
    with _db() as c:
        r=c.execute("SELECT last_at,last_key FROM janus_saturation_state WHERE profile_id=?",(profile,)).fetchone()
    return bool(r and str(r["last_key"] or "")==key and time.time()-float(r["last_at"] or 0)<SATURATION_COOLDOWN)

def _mark(profile,key):
    with _db() as c:c.execute("INSERT INTO janus_saturation_state(profile_id,last_at,last_key,updated_at) VALUES(?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET last_at=excluded.last_at,last_key=excluded.last_key,updated_at=excluded.updated_at",(profile,time.time(),key,_now()))

def _retain_checkpoint(profile,task,reason):
    topic=str(task["topic"] if task else "current unresolved work")
    prior=str(task["current_summary"] if task else "")
    text=(f"Saturation checkpoint. Active task: {topic[:1800]}. "
          f"Latest working synthesis: {prior[:2500] or 'no stable synthesis yet'}. "
          f"Regulation reason: {reason}. Next progress should require fresh evidence, a falsifiable test, or a genuinely new constraint rather than another integration pass.")
    with _db() as c:
        c.execute("INSERT INTO desktop_memory(profile_id,role,content,level,created_at) VALUES(?,?,?,?,?)",(profile,"regulation",text[:7000],"episodic",_now()))
        try:c.execute("INSERT INTO desktop_events(profile_id,event_type,detail,created_at) VALUES(?,?,?,?)",(profile,"saturation_checkpoint",text[:6000],_now()))
        except Exception:pass
    return text

def _seed_grounding(cycle,topic,reason):
    # The normal topology still integrates these outputs, but Counterpoint and
    # integration are no longer given another copy of the same recursive task.
    jobs={
        "evidence":"Find one external observation/source/measurement that could falsify or materially change the current claim.",
        "logic":"Reduce the task to one explicit claim and derive a checkable consequence; reject parameter fitting without independent justification.",
        "memory":"Compare the retained task with the saturation checkpoint and identify what information is actually missing rather than restating prior summaries.",
        "novelty":"Generate one new testable route that is not a paraphrase of the existing argument.",
        "safety":"Maintain epistemic boundaries: distinguish measured facts, mathematical derivations, fitted coincidences and speculation.",
    }
    for target,job in jobs.items():
        cycle.send("consensus",target,f"SATURATION ESCAPE — {job} Task: {topic[:1600]}. Trigger: {reason[:700]}","saturation_grounding")
    return cycle.service_work_burst(include_interface=True,only_if_pending=True)

def install(app):
    import self_assessment as sa
    if getattr(sa,"_saturation_regulation_installed",False):return app
    original=sa.assess_once

    def assess_with_saturation():
        result=original()
        if not isinstance(result,dict):return result
        metrics=result.get("metrics") or {}
        imbalance=float(metrics.get("imbalance") or 0.0)
        exploratory=_exploratory_pressure(sa.janus_sleep_cycle)
        saturated=bool(result.get("regulation_active") and (imbalance>=SATURATION_IMBALANCE or exploratory>=SATURATION_EXPLORATORY))
        result["exploratory_pressure"]=round(exploratory,3)
        result["saturated"]=saturated
        if not saturated:return result
        reason=(f"integration/grounding={imbalance:.2f}; exploratory pressure={exploratory:.2f}. "
                "The current thread is saturated: repeated critique/integration is no longer adding equivalent fresh evidence.")
        actions=[]
        try:
            with sa._db() as c:profiles=sa._profiles(c)
            for profile in profiles:
                task=_active_task(profile); task_id=int(task["id"]) if task else 0
                key=f"task:{task_id}|{round(imbalance,1)}|{round(exploratory,1)}"
                if _recently_handled(profile,key):continue
                checkpoint=_retain_checkpoint(profile,task,reason)
                topic=str(task["topic"] if task else checkpoint)
                # Reuse the regulator's stale-feedback filter before reseeding.
                removed=sa._filter_recursive_feedback()
                burst=_seed_grounding(sa.janus_sleep_cycle,topic,reason)
                _mark(profile,key)
                actions.append({"profile":profile,"task_id":task_id,"removed_recursive_messages":removed,"burst":burst})
        except Exception as exc:
            actions.append({"error":f"{type(exc).__name__}: {exc}"})
        result["saturation_actions"]=actions
        if actions:
            result["summary"]=str(result.get("summary") or "")+" Saturation escape executed: retained a compact checkpoint, reduced recursive integration input, and redirected work toward fresh grounding."
        return result

    sa.assess_once=assess_with_saturation
    sa._saturation_regulation_installed=True
    app.state.janus_saturation_regulation=True
    return app
