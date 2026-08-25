from __future__ import annotations

from typing import Any

from . import diagnostics, maintenance_request_file

_INSTALLED = False


def install() -> None:
    """Install the persistent append-ledger contract around diagnostics.

    Kept as a small integration layer so the diagnostics/request schema stays focused on
    structured state while the human/Supervisor JSONL ledger remains independently
    testable. Module-global function lookups inside diagnostics see these replacements.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    original_record = diagnostics.record_request
    original_handoff = diagnostics.handoff_packet
    original_apply = diagnostics.apply_supervisor_decisions

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
