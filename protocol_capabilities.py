"""JANUS protocol/capability negotiation.

This endpoint is intentionally public and contains only product compatibility facts.
It lets clients discover what the deployed server actually supports before exposing
or invoking optional workflows. No account data, secrets, internal reasoning or
private diagnostics are returned.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/protocol", tags=["protocol"])

PROTOCOL_VERSION = 1
MIN_ANDROID_VERSION = os.getenv("JANUS_MIN_ANDROID_VERSION", "0.69").strip() or "0.69"
RECOMMENDED_ANDROID_VERSION = os.getenv("JANUS_RECOMMENDED_ANDROID_VERSION", MIN_ANDROID_VERSION).strip() or MIN_ANDROID_VERSION


def _routes(request: Request) -> set[str]:
    return {str(getattr(route, "path", "")) for route in request.app.routes}


def _feature(routes: set[str], *paths: str) -> bool:
    return all(path in routes for path in paths)


def snapshot(request: Request) -> dict[str, Any]:
    routes = _routes(request)
    features = {
        "auth_password": _feature(routes, "/auth/register", "/auth/login"),
        "auth_google": "/auth/google" in routes,
        "attachments": _feature(routes, "/files/upload"),
        "artifact_workspace": _feature(routes, "/artifacts"),
        "research_workspace": _feature(routes, "/research/workspace"),
        "maintenance_review": _feature(routes, "/maintenance/status", "/maintenance/reviews/{review_id}/decision"),
        "research_provenance": _feature(routes, "/research-provenance/status"),
        "image_generation": _feature(routes, "/images/generate"),
        "inline_images": any(path.startswith("/images/{file_id}/inline") for path in routes),
        "background_multi_core_images": False,
        "protocol_negotiation": True,
    }
    return {
        "ok": True,
        "service": "janus-global-core",
        "protocol_version": PROTOCOL_VERSION,
        "protocol_compatibility": {"min": 1, "max": PROTOCOL_VERSION},
        "deployed_commit": os.getenv("RENDER_GIT_COMMIT", "unknown")[:40],
        "clients": {
            "android": {
                "minimum_version": MIN_ANDROID_VERSION,
                "recommended_version": RECOMMENDED_ANDROID_VERSION,
            }
        },
        "features": features,
        "safety_boundaries": {
            "whole_state_overwrite": False,
            "autonomous_code_changes": False,
            "autonomous_deployments": False,
            "background_image_generation": False,
        },
    }


@router.get("/capabilities")
def protocol_capabilities(request: Request):
    return snapshot(request)
