"""Conservative per-source rate limits and Android auth compatibility for JANUS.

The original Android interface predates the current auth response shape. Keep the
server tolerant of that client while retaining the current canonical API for new
clients. State is intentionally process-local: Render is currently a single-
instance service, and limits reset harmlessly on deployment.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse, Response

LIMITS = {
    "/auth/login": (int(os.getenv("JANUS_LOGIN_RATE_LIMIT", "20")), 10 * 60),
    "/auth/register": (int(os.getenv("JANUS_REGISTER_RATE_LIMIT", "10")), 60 * 60),
    "/auth/forgot-password": (int(os.getenv("JANUS_RECOVERY_RATE_LIMIT", "10")), 60 * 60),
    "/auth/resend-verification": (int(os.getenv("JANUS_RECOVERY_RATE_LIMIT", "10")), 60 * 60),
    "/auth/reset-password": (int(os.getenv("JANUS_RESET_RATE_LIMIT", "20")), 60 * 60),
    "/auth/verify-email": (int(os.getenv("JANUS_VERIFY_RATE_LIMIT", "20")), 60 * 60),
    "/auth/google": (int(os.getenv("JANUS_GOOGLE_RATE_LIMIT", "30")), 10 * 60),
}

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
MAX_TRACKED_KEYS = 5000
_AUTH_SESSION_PATHS = {"/auth/login", "/auth/register", "/auth/google"}


def _source_key(request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:96]
    client = getattr(request, "client", None)
    return str(getattr(client, "host", "unknown"))[:96]


async def _normalize_legacy_android_request(request) -> None:
    if request.method.upper() != "POST" or request.url.path != "/auth/login":
        return
    try:
        body = await request.body()
        if not body:
            return
        data = json.loads(body)
        if isinstance(data, dict) and "identifier" not in data and data.get("identity"):
            data["identifier"] = data.pop("identity")
            request._body = json.dumps(data, separators=(",", ":")).encode("utf-8")
    except Exception:
        return


async def _legacy_android_response(response, path: str):
    if path not in _AUTH_SESSION_PATHS or response.status_code >= 400:
        return response
    body = b""
    try:
        chunks = [chunk async for chunk in response.body_iterator]
        body = b"".join(chunks)
        data = json.loads(body or b"{}")
        if not isinstance(data, dict):
            raise ValueError("non-object auth response")
        account = data.get("account") if isinstance(data.get("account"), dict) else {}
        username = account.get("username") or data.get("username") or data.get("profile_id")
        account_id = account.get("id") or data.get("account_id") or data.get("user_id")
        if username:
            data.setdefault("username", username)
            data.setdefault("profile_id", username)
        if account_id is not None:
            data.setdefault("account_id", account_id)
            data.setdefault("user_id", account_id)
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "transfer-encoding"}}
        return Response(content=payload, status_code=response.status_code, headers=headers, media_type="application/json", background=response.background)
    except Exception:
        try:
            headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "transfer-encoding"}}
            return Response(content=body, status_code=response.status_code, headers=headers, media_type=response.media_type, background=response.background)
        except Exception:
            return response


def install(app) -> None:
    @app.middleware("http")
    async def janus_auth_rate_limit(request, call_next):
        await _normalize_legacy_android_request(request)

        spec = LIMITS.get(request.url.path) if request.method.upper() == "POST" else None
        if spec:
            limit, window = spec
            if limit > 0:
                now = time.monotonic()
                key = (request.url.path, _source_key(request))
                q = _hits[key]
                cutoff = now - window
                while q and q[0] < cutoff:
                    q.popleft()
                if len(q) >= limit:
                    retry_after = max(1, int(window - (now - q[0])))
                    return JSONResponse(status_code=429, headers={"Retry-After": str(retry_after)}, content={"detail": "Too many authentication attempts. Please try again later."})
                q.append(now)

                if len(_hits) > MAX_TRACKED_KEYS:
                    for old_key in list(_hits.keys())[: max(1, len(_hits) - MAX_TRACKED_KEYS)]:
                        if old_key != key:
                            _hits.pop(old_key, None)

        response = await call_next(request)
        return await _legacy_android_response(response, request.url.path)
