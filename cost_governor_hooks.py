"""Install Step-4 cost-governor scopes around JANUS paid/external calls.

This keeps the policy centralized without duplicating budget logic through every
feature.  It wraps the OpenAI client aliases already imported by JANUS modules and
sets capability/profile context around chat, curiosity, vision and image paths.
"""
from __future__ import annotations

import functools
import inspect
from typing import Any

import cost_governor as budget

_installed=False

class BudgetDenied(RuntimeError):
    pass

class _CallableProxy:
    def __init__(self, fn, model_getter=None): self._fn=fn; self._model_getter=model_getter
    def __call__(self,*args,**kwargs):
        decision=budget.authorize_current()
        if not decision.get("allowed"):
            raise BudgetDenied(str(decision.get("reason") or "JANUS external-compute budget reached"))
        try:
            result=self._fn(*args,**kwargs)
        except Exception:
            budget.record_current(model=str(kwargs.get("model") or ""),status="error",detail="provider call raised before completion")
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
        except Exception:
            budget.record_current(model=str(kwargs.get("model") or ""),status="error",detail="provider call raised before completion")
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
    _installed=True
