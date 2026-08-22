"""Server integration for the JANUS project/question continuity ledger."""
from __future__ import annotations

import inspect
from typing import Any
from fastapi import HTTPException, Query

import continuity_ledger as ledger


def _profile(payload: dict[str, Any]) -> str:
    return str(payload.get("profile_id") or payload.get("username") or "").strip()


def install(app):
    ledger.ensure_schema()

    # Wrap the current chat endpoint after deliberation_tasks has wrapped it. This
    # binds explicit "ponder/keep thinking" commitments to a durable ledger item.
    routes=[r for r in app.router.routes if getattr(r,"path",None)=="/desktop/chat" and "POST" in getattr(r,"methods",set())]
    if routes:
        old=routes[-1]; base=old.endpoint
        app.router.routes=[r for r in app.router.routes if r is not old]

        @app.post("/desktop/chat",tags=["desktop"])
        async def desktop_chat_with_continuity(payload:dict[str,Any]):
            result=base(payload)
            if inspect.isawaitable(result): result=await result
            if not isinstance(result,dict): return result
            profile=_profile(payload) or str(result.get("profile") or "local-user")
            task=result.get("deliberation_task")
            if isinstance(task,dict) and str(task.get("topic") or "").strip():
                item=ledger.upsert_open(
                    profile,"question",str(task["topic"]),
                    detail="User explicitly asked JANUS to keep thinking about this across later cycles.",
                    state="investigating",priority=75,source="deliberation",
                    tags=("deliberation",f"task:{task.get('id','unknown')}")
                )
                result["continuity_item"]={"id":item["id"],"kind":item["kind"],"state":item["state"],"title":item["title"]}
            result["open_continuity_count"]=len(ledger.list_items(profile,open_only=True,limit=500))
            return result

    @app.get("/desktop/continuity",tags=["desktop"])
    def continuity_list(username:str=Query(...),open_only:bool=Query(default=False),kind:str|None=Query(default=None),limit:int=Query(default=100,ge=1,le=500)):
        try: items=ledger.list_items(username,open_only=open_only,kind=kind,limit=limit)
        except ValueError as exc: raise HTTPException(400,str(exc))
        return {"profile":username,"items":items,"open_count":len(ledger.list_items(username,open_only=True,limit=500)),"states":sorted(ledger.STATES),"kinds":sorted(ledger.KINDS)}

    @app.post("/desktop/continuity",tags=["desktop"])
    def continuity_create(payload:dict[str,Any]):
        profile=_profile(payload)
        if not profile: raise HTTPException(400,"profile_id required")
        try:
            item=ledger.create_item(profile,str(payload.get("kind") or "task"),str(payload.get("title") or ""),str(payload.get("detail") or ""),state=str(payload.get("state") or "proposed"),priority=int(payload.get("priority") or 50),parent_id=payload.get("parent_id"),supersedes_id=payload.get("supersedes_id"),source=str(payload.get("source") or "user"),tags=payload.get("tags") or ())
        except (ValueError,TypeError) as exc: raise HTTPException(400,str(exc))
        return {"ok":True,"item":item}

    @app.post("/desktop/continuity/{item_id}/state",tags=["desktop"])
    def continuity_state(item_id:int,payload:dict[str,Any]):
        profile=_profile(payload)
        if not profile: raise HTTPException(400,"profile_id required")
        try: item=ledger.transition(profile,item_id,str(payload.get("state") or ""),str(payload.get("note") or ""))
        except KeyError: raise HTTPException(404,"continuity item not found")
        except ValueError as exc: raise HTTPException(400,str(exc))
        return {"ok":True,"item":item}

    @app.get("/desktop/continuity/{item_id}/events",tags=["desktop"])
    def continuity_events(item_id:int,username:str=Query(...),limit:int=Query(default=100,ge=1,le=500)):
        try: ledger.get_item(username,item_id)
        except KeyError: raise HTTPException(404,"continuity item not found")
        return {"profile":username,"item_id":item_id,"events":ledger.events(username,item_id,limit)}

    return app
