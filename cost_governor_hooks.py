"""Install JANUS cost-governor scopes around paid/external calls.

This keeps the policy centralized without duplicating budget logic through every
feature. It wraps the OpenAI client aliases already imported by JANUS modules and
sets capability/profile context around chat, curiosity, vision and image paths.

Phase 2 degradation rule: provider failures are recorded for observability but do
not consume the estimated budget reservation. This prevents a provider outage or
malformed upstream response from cascading into artificial budget exhaustion.
"""
from __future__ import annotations

import functools
from typing import Any

from fastapi import Query

import cost_governor as budget

_installed=False

class BudgetDenied(RuntimeError):
    pass

def _failure_status(exc:Exception)->str:
    name=type(exc).__name__.lower(); msg=str(exc).lower()
    if "timeout" in name or "timeout" in msg or "timed out" in msg:return "timeout"
    if "json" in name or "decode" in name or "malformed" in msg or "invalid response" in msg:return "malformed"
    return "error"

def _failure_detail(exc:Exception)->str:
    return f"provider call failed: {type(exc).__name__}: {str(exc)[:700]}"

class _CallableProxy:
    def __init__(self, fn): self._fn=fn
    def __call__(self,*args,**kwargs):
        decision=budget.authorize_current()
        if not decision.get("allowed"):
            raise BudgetDenied(str(decision.get("reason") or "JANUS external-compute budget reached"))
        try:
            result=self._fn(*args,**kwargs)
        except Exception as exc:
            budget.record_current(model=str(kwargs.get("model") or ""),estimated_usd=0.0,status=_failure_status(exc),detail=_failure_detail(exc))
            raise
        budget.record_current(model=str(kwargs.get("model") or ""),response=result,status="complete")
        return result

class _AsyncCallableProxy:
    def __init__(self, fn): self._fn=fn
    async def __call__(self,*args,**kwargs):
        decision=budget.authorize_current()
        if not decision.get("allowed"):
            raise BudgetDenied(str(decision.get("reason") or "JANUS external-compute budget reached"))
        try:
            result=await self._fn(*args,**kwargs)
        except Exception as exc:
            budget.record_current(model=str(kwargs.get("model") or ""),estimated_usd=0.0,status=_failure_status(exc),detail=_failure_detail(exc))
            raise
        budget.record_current(model=str(kwargs.get("model") or ""),response=result,status="complete")
        return result

class _ResponsesProxy:
    def __init__(self, obj, async_mode=False):
        self._obj=obj; self.create=_AsyncCallableProxy(obj.create) if async_mode else _CallableProxy(obj.create)
    def __getattr__(self,n): return getattr(self._obj,n)

class _ImagesProxy:
    def __init__(self,obj,async_mode=False):
        self._obj=obj; self.generate=_AsyncCallableProxy(obj.generate) if async_mode else _CallableProxy(obj.generate)
    def __getattr__(self,n):return getattr(self._obj,n)

class _ClientProxy:
    def __init__(self, real, async_mode=False):
        self._real=real; self.responses=_ResponsesProxy(real.responses,async_mode)
        if hasattr(real,"images"): self.images=_ImagesProxy(real.images,async_mode)
    def __getattr__(self,n):return getattr(self._real,n)

def _replace_client(module,name,async_mode=False):
    original=getattr(module,name,None)
    if not original or getattr(original,"_janus_budget_proxy",False):return
    def factory(*args,**kwargs): return _ClientProxy(original(*args,**kwargs),async_mode)
    factory._janus_budget_proxy=True
    setattr(module,name,factory)

def _wrap_sync(module,name,profile_fn,capability_fn):
    fn=getattr(module,name,None)
    if not fn or getattr(fn,"_janus_budget_scope",False):return
    @functools.wraps(fn)
    def wrapped(*args,**kwargs):
        with budget.scope(profile_fn(*args,**kwargs),capability_fn(*args,**kwargs)):
            return fn(*args,**kwargs)
    wrapped._janus_budget_scope=True; setattr(module,name,wrapped)

def _wrap_async(module,name,profile_fn,capability_fn):
    fn=getattr(module,name,None)
    if not fn or getattr(fn,"_janus_budget_scope",False):return
    @functools.wraps(fn)
    async def wrapped(*args,**kwargs):
        with budget.scope(profile_fn(*args,**kwargs),capability_fn(*args,**kwargs)):
            return await fn(*args,**kwargs)
    wrapped._janus_budget_scope=True; setattr(module,name,wrapped)

def _wrap_chat_bridge(image_generation):
    original=getattr(image_generation,"install_chat_image_bridge",None)
    if not original or getattr(original,"_janus_cost_bridge",False):return
    @functools.wraps(original)
    def install_with_cost(app,interface_chat_module):
        result=original(app,interface_chat_module)
        route=next((r for r in app.router.routes if getattr(r,"path",None)=="/desktop/chat" and "POST" in getattr(r,"methods",set())),None)
        if route and not getattr(route.endpoint,"_janus_cost_chat_scope",False):
            base=route.endpoint
            app.router.routes[:]=[r for r in app.router.routes if r is not route]
            @app.post("/desktop/chat",tags=["desktop"])
            @functools.wraps(base)
            async def cost_scoped_chat(*args,**kwargs):
                payload=kwargs.get("payload") or (args[-1] if args and isinstance(args[-1],dict) else {})
                profile=str((payload or {}).get("profile_id") or (payload or {}).get("username") or "local-user")
                with budget.scope(profile,"chat"):
                    return await base(*args,**kwargs)
            cost_scoped_chat._janus_cost_chat_scope=True
        paths={getattr(r,"path","") for r in app.router.routes}
        if "/desktop/cost-status" not in paths:
            @app.get("/desktop/cost-status",tags=["desktop"])
            def cost_status(username:str=Query(...)):
                return {"ok":True,**budget.status(username)}
        app.state.janus_cost_governor_enabled=True
        return result
    install_with_cost._janus_cost_bridge=True
    image_generation.install_chat_image_bridge=install_with_cost

def install()->None:
    global _installed
    if _installed:return
    import curiosity_search, vision_analysis, image_generation, interface_chat

    _replace_client(curiosity_search,"OpenAI",False)
    _replace_client(vision_analysis,"AsyncOpenAI",True)
    _replace_client(image_generation,"AsyncOpenAI",True)
    _replace_client(interface_chat,"AsyncOpenAI",True)

    _wrap_sync(curiosity_search,"foreground_deliberate",lambda profile,message,*a,**k:profile,lambda *a,**k:"foreground_core")
    _wrap_sync(curiosity_search,"consult_core",lambda profile,*a,**k:profile,lambda profile,core,topic,use_web=False,mode="model",*a,**k:"background_web" if use_web else "background_model")
    _wrap_sync(curiosity_search,"_perform_search",lambda profile,*a,**k:profile,lambda *a,**k:"background_web")
    _wrap_async(vision_analysis,"assess_images",lambda account_id,*a,**k:f"acct-{int(account_id)}",lambda *a,**k:"vision")
    def img_profile(account,*a,**k):
        try:return str(account["username"] or account["email"] or f"acct-{account['id']}")
        except Exception:return "__unattributed__"
    _wrap_async(image_generation,"generate_for_account",img_profile,lambda *a,**k:"image")
    _wrap_chat_bridge(image_generation)
    _installed=True
