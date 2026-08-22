"""Conservative contradiction/revision governance for JANUS continuity.

Only explicit user language can mutate continuity state automatically. Ambiguous or
low-confidence references are returned as candidates for clarification rather than
silently rewriting history. Historical items remain auditable in the ledger.
"""
from __future__ import annotations

import re
from typing import Any

import continuity_ledger as ledger

_STOP={"the","and","that","this","with","from","have","has","had","was","were","are","been","being","you","your","me","my","we","our","they","their","it","its","a","an","of","to","in","on","for","as","at","by","or","but","if","then","than","so","do","did","does","about","into","out","up","down","can","could","would","should","will","just","also","old","earlier","previous"}


def _tokens(text:str)->set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9_-]{2,}",str(text or "").lower()) if w not in _STOP}


def _target_text(message:str)->str:
    text=" ".join(str(message or "").split()).strip()
    # Remove common lifecycle commands so matching focuses on the actual subject.
    patterns=(
        r"\b(?:mark|set|consider|treat)\b", r"\b(?:as|is|was|has been|have been)\b",
        r"\b(?:done|finished|complete|completed|resolved|wrong|false|contradicted|defer|deferred|pause|paused|reopen|resume|superseded|replaced|cancelled|canceled)\b",
        r"\b(?:we|i)\s+(?:finished|completed|resolved|deferred|reopened|cancelled|canceled|replaced)\b",
    )
    for p in patterns:
        text=re.sub(p," ",text,flags=re.I)
    return " ".join(text.split()).strip(" .,:;!?-—")


def classify(message:str)->dict[str,Any]|None:
    """Classify explicit lifecycle intent; return None for ordinary discussion."""
    m=" ".join(str(message or "").lower().split())
    if not m:return None
    rules=(
        ("reopened", (r"\breopen\b",r"\bresume\b",r"\bopen .* again\b",r"\bnot finished after all\b")),
        ("superseded", (r"\bsupersed(?:e|ed)\b",r"\breplace(?:d)?\b.*\bwith\b",r"\buse .* instead\b")),
        ("contradicted", (r"\b(?:that|this|it|idea|hypothesis|claim|approach).{0,30}\b(?:is|was) (?:wrong|false|contradicted)\b",r"\bwe (?:disproved|falsified|contradicted)\b")),
        ("deferred", (r"\bdefer\b",r"\bput .* on hold\b",r"\bpark .* for now\b",r"\bpause .* for now\b")),
        ("cancelled", (r"\bcancel(?:led)?\b",r"\bdrop .* entirely\b",r"\bwe are not doing\b")),
        ("completed", (r"\b(?:done|finished|completed)\b",r"\bwe (?:finished|completed)\b",r"\bthat(?:'s| is) complete\b")),
        ("resolved", (r"\bresolved\b",r"\bquestion (?:is|was) answered\b",r"\bwe settled\b")),
    )
    for state,patterns in rules:
        if any(re.search(p,m,re.I) for p in patterns):
            return {"state":state,"target":_target_text(message),"message":message}
    return None


def rank_matches(profile_id:str,target:str,limit:int=5)->list[dict[str,Any]]:
    items=ledger.list_items(profile_id,open_only=False,limit=300)
    q=_tokens(target)
    ranked=[]
    for item in items:
        text=f"{item.get('title','')} {item.get('detail','')}"
        toks=_tokens(text)
        overlap=len(q & toks)
        union=max(1,len(q|toks))
        score=(overlap/max(1,len(q)))*0.7 + (overlap/union)*0.3 if q else 0.0
        # Prefer currently open work when the user's statement is about finishing/defering/etc.
        if item.get("state") in ledger.OPEN_STATES: score+=0.08
        ranked.append((score,int(item["id"]),item))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return [{**x[2],"match_score":round(x[0],3)} for x in ranked[:max(1,limit)]]


def apply_explicit_update(profile_id:str,message:str)->dict[str,Any]:
    """Apply only high-confidence explicit lifecycle updates.

    Generic pronoun-only commands and weak matches are never applied automatically.
    They produce candidate matches so the Interface can ask/reflect rather than guess.
    """
    intent=classify(message)
    if not intent:return {"recognized":False,"applied":False}
    state=str(intent["state"]); target=str(intent.get("target") or "")
    q=_tokens(target)
    candidates=rank_matches(profile_id,target,5)
    best=candidates[0] if candidates else None
    second=candidates[1] if len(candidates)>1 else None
    pronounish=not q or target.lower() in {"it","that","this","that one","this one","the old one","old one"}
    confident=bool(best and not pronounish and best["match_score"]>=0.52 and (not second or best["match_score"]-second["match_score"]>=0.10))
    if not confident:
        return {"recognized":True,"applied":False,"requested_state":state,"target":target,"candidates":candidates[:3],"reason":"ambiguous-or-low-confidence"}
    item_id=int(best["id"])
    updated=ledger.transition(profile_id,item_id,state,note=f"Explicit user lifecycle statement: {message[:1200]}")
    return {"recognized":True,"applied":True,"requested_state":state,"target":target,"item":updated,"candidates":candidates[:1]}


def currentness_context(profile_id:str,query:str="",limit:int=20)->str:
    """Explain authoritative current/closed states for retrieval and Interface use."""
    items=ledger.list_items(profile_id,open_only=False,limit=200)
    q=_tokens(query)
    if q:
        scored=[]
        for x in items:
            toks=_tokens(f"{x.get('title','')} {x.get('detail','')}")
            ov=len(q&toks)
            if ov: scored.append((ov,x))
        scored.sort(key=lambda p:(p[0],p[1].get("updated_at","")),reverse=True)
        items=[x for _,x in scored[:limit]]
    else:
        items=items[:limit]
    if not items:return "No matching continuity-state records."
    lines=["Continuity currentness (authoritative lifecycle metadata; history is preserved):"]
    for x in items:
        lines.append(f"- #{x['id']} [{x['kind']}:{x['state']}] {x['title']}")
    return "\n".join(lines)
