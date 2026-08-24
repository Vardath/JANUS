from __future__ import annotations

"""Narrow JANUS-owned maintenance submission boundary.

This module deliberately exposes only validated maintenance-record operations. It has
no GitHub client, repository path, shell/process execution, package management,
configuration mutation, decision-writing, or deployment primitive. JANUS runtime and
clients may submit observations here; Supervisor/source changes remain outside this
boundary and under owner control.
"""

from typing import Any

from . import diagnostics

_ALLOWED_SEVERITY = {"low", "normal", "high", "critical"}
_MAX_CAPABILITY = 120
_MAX_TITLE = 240
_MAX_DETAIL = 8000
_MAX_EVIDENCE = 12000


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def submit(account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist one externalizable diagnostic request; perform no maintenance action."""
    capability = _text(payload.get("capability") or payload.get("kind") or "client_or_tool", _MAX_CAPABILITY)
    title = _text(payload.get("title") or "JANUS detected a client/tool failure", _MAX_TITLE)
    detail = _text(payload.get("detail") or payload.get("error") or "A JANUS client or tool reported a failure point.", _MAX_DETAIL)
    evidence = str(payload.get("evidence") or "")[:_MAX_EVIDENCE]
    severity = str(payload.get("severity") or "normal").lower()
    if severity not in _ALLOWED_SEVERITY:
        severity = "normal"
    return diagnostics.record_request(
        int(account_id), capability, title, detail, evidence=evidence, severity=severity
    )


def boundary_status() -> dict[str, Any]:
    return {
        "storage_channel": "validated_server_database",
        "source_repository_credentials_exposed_to_janus": False,
        "arbitrary_repository_read": False,
        "arbitrary_repository_write": False,
        "arbitrary_file_write": False,
        "shell_or_process_execution": False,
        "package_install": False,
        "configuration_mutation": False,
        "maintenance_self_approval": False,
        "self_deploy": False,
        "owner_supervisor_authorization_required": True,
    }
