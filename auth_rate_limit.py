"""Conservative per-source rate limits for JANUS public auth endpoints.

This protects login and recovery endpoints from simple brute-force/spam without
changing normal account behavior. State is intentionally process-local: Render is
currently a single-instance service, and limits reset harmlessly on deployment.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from fastapi.responses import JSONResponse

# path -> (max requests, window seconds)
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


def _source_key(request) -> str:
    # Render/proxies normally set X-Forwarded-For. Keep only the first address and
    # bound its length; fall back to the socket peer if unavailable.
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:96]
    client = getattr(request, "client", None)
    return str(getattr(client, "host", "unknown"))[:96]


def install(app) -> None:
    @app.middleware("http")
    async def janus_auth_rate_limit(request, call_next):
        spec = LIMITS.get(request.url.path) if request.method.upper() == "POST" else None
        if not spec:
            return await call_next(request)

        limit, window = spec
        if limit <= 0:
            return await call_next(request)

        now = time.monotonic()
        key = (request.url.path, _source_key(request))
        q = _hits[key]
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            retry_after = max(1, int(window - (now - q[0])))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"detail": "Too many authentication attempts. Please try again later."},
            )
        q.append(now)

        # Bound memory even under source-address churn.
        if len(_hits) > MAX_TRACKED_KEYS:
            for old_key in list(_hits.keys())[: max(1, len(_hits) - MAX_TRACKED_KEYS)]:
                if old_key != key:
                    _hits.pop(old_key, None)
        return await call_next(request)
