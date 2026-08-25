from __future__ import annotations

from typing import Any

from . import diagnostics, maintenance_issue_mirror, maintenance_request_file

_INSTALLED = False


def install() -> None:
    """Install the persistent append-ledger contract around diagnostics.

    Render SQLite remains authoritative. The JSONL ledger is the durable local
    Supervisor record. When explicitly configured, a private GitHub Issue receives a
    sanitized append-only mirror so ChatGPT Supervisor can retrieve requests through
    the connected GitHub account without giving JANUS source-code authority.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    original_record = diagnostics.record_request
    original_handoff = diagnostics.handoff_packet
    original_apply = diagnostics.apply_supervisor_decisions

    maintenance_issue_mirror.init_schema()

    def record_request(*args: Any, **kwargs: Any) -> dict[str, Any]:
        request = original_record(*args, **kwargs)
        try:
            maintenance_request_file.append_observation(
                request,
                created=int(request.get("occurrence_count") or 1) <= 1,
            )
        except Exception:
            # The SQLite request is authoritative; a ledger I/O problem must not prevent
            # JANUS from recording or surfacing a maintenance request.
            pass
        try:
            maintenance_issue_mirror.mirror_request(request)
        except Exception:
            # The private issue mirror is convenience/visibility only. It must never
            # become a dependency for JANUS request persistence or runtime operation.
            pass
        return request

    def handoff_packet(account_id: int, username: str = "") -> dict[str, Any]:
        packet = original_handoff(account_id, username)
        ledger = maintenance_request_file.status()
        command = maintenance_request_file.instructions().strip()
        original_text = str(packet.get("packet") or "")
        packet["packet"] = (
            "MANDATORY MAINTENANCE LEDGER COMMAND\n"
            "====================================\n"
            + command
            + "\n\nLEDGER STATUS: "
            + str(ledger)
            + "\n\n"
            + original_text
        )
        packet["maintenance_request_ledger"] = ledger
        packet["maintenance_runbook"] = "MAINTENANCE_PROCESS.md"
        packet["request_generation_mode"] = "append_only"
        packet["closed_request_cleanup"] = "remove implemented/disapproved only after Supervisor decisions"
        packet["private_supervisor_issue_mirror"] = maintenance_issue_mirror.status()
        return packet

    def apply_supervisor_decisions() -> dict[str, int]:
        result = dict(original_apply())
        try:
            reconciled = maintenance_request_file.reconcile_closed()
            result["ledger_removed"] = int(reconciled.get("removed") or 0)
            result["ledger_kept"] = int(reconciled.get("kept") or 0)
        except Exception:
            result["ledger_reconcile_failed"] = 1
        return result

    diagnostics.record_request = record_request
    diagnostics.handoff_packet = handoff_packet
    diagnostics.apply_supervisor_decisions = apply_supervisor_decisions

    # If the mirror was enabled after requests already existed, backfill every still-open
    # request once. Per-fingerprint occurrence tracking prevents restart spam.
    try:
        maintenance_issue_mirror.mirror_open_requests()
    except Exception:
        pass
