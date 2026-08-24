from __future__ import annotations

import os
import re
from typing import Any


def escalation_score(message: str, *, evidence: bool = False, web: bool = False, memory_count: int = 0, disagreement: float = 0.0) -> dict[str, Any]:
    """Cheap deterministic preflight for model escalation.

    This is not a truth score. It estimates how much integration effort may be
    useful from novelty, salience, uncertainty, conflict and local/cloud evidence.
    """
    text=(message or "").lower()
    uncertainty=sum(1 for x in ("maybe","uncertain","not sure","could be","might","unknown","why","how") if x in text)
    conflict=sum(1 for x in ("but","however","contradict","conflict","disagree","versus","vs ","or else") if x in text)
    salience=sum(1 for x in ("important","critical","urgent","security","privacy","money","legal","medical","production","deploy") if x in text)
    novelty=len(set(re.findall(r"[a-z0-9_-]{5,}",text)))
    length=min(1.0,len(message or "")/3500.0)
    raw=(min(1,uncertainty/3)*0.20 + min(1,conflict/3)*0.20 + min(1,salience/3)*0.18 + min(1,novelty/24)*0.14 + length*0.10 + (0.08 if evidence else 0) + (0.06 if web else 0) + min(0.04,memory_count*0.005) + min(0.12,max(0.0,float(disagreement))*0.12))
    score=max(0.0,min(1.0,raw))
    return {"score":round(score,4),"uncertainty":uncertainty,"conflict":conflict,"salience":salience,"novelty_terms":novelty,"evidence":evidence,"web":web,"memory_count":memory_count}


def choose_model(score: float) -> str:
    luna=os.getenv("JANUS_MODEL_LUNA","gpt-5.6-luna").strip() or "gpt-5.6-luna"
    terra=os.getenv("JANUS_MODEL_TERRA","gpt-5.6-terra").strip() or "gpt-5.6-terra"
    sol=os.getenv("JANUS_MODEL_SOL","gpt-5.6-sol").strip() or "gpt-5.6-sol"
    if score >= float(os.getenv("JANUS_SOL_ESCALATION_THRESHOLD","0.72")): return sol
    if score >= float(os.getenv("JANUS_TERRA_ESCALATION_THRESHOLD","0.42")): return terra
    return luna
