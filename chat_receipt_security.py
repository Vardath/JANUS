"""Profile-bound chat idempotency receipt guard.

JANUS Android retries queued chat turns by client_message_id. The receipt table
uses that id as its primary key, so every cached response must additionally be
bound to the authenticated profile that first claimed it. This module replaces
the interface_chat receipt helpers after routes are installed; route functions
resolve these globals at call time.
"""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import HTTPException


def install(interface_chat_module) -> None:
    if getattr(interface_chat_module, "_profile_receipt_guard_installed", False):
        return
    interface_chat_module._profile_receipt_guard_installed = True

    def claim_message(client_message_id: str, profile: str):
        if not client_message_id:
            return None
        now = int(time.time())
        with interface_chat_module._receipt_db() as c:
            row = c.execute(
                "SELECT profile_id,status,response_json,updated_at FROM janus_chat_receipts WHERE client_message_id=?",
                (client_message_id,),
            ).fetchone()
            if row:
                stored_profile = str(row["profile_id"] or "")
                if stored_profile != profile:
                    # Never reveal or overwrite another account's cached result.
                    raise HTTPException(409, "client_message_id already belongs to another account")
                if row["status"] == "done" and row["response_json"]:
                    try:
                        return json.loads(row["response_json"])
                    except Exception:
                        pass
                if row["status"] == "processing" and now - int(row["updated_at"] or 0) <= 180:
                    return "processing"
                c.execute(
                    "UPDATE janus_chat_receipts SET status='processing',response_json=NULL,updated_at=? WHERE client_message_id=? AND profile_id=?",
                    (now, client_message_id, profile),
                )
                return None
            c.execute(
                "INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at) VALUES(?,?,'processing',NULL,?,?)",
                (client_message_id, profile, now, now),
            )
        return None

    def finish_message(client_message_id: str, profile: str, response: dict[str, Any]):
        if not client_message_id:
            return
        now = int(time.time())
        with interface_chat_module._receipt_db() as c:
            row = c.execute(
                "SELECT profile_id FROM janus_chat_receipts WHERE client_message_id=?",
                (client_message_id,),
            ).fetchone()
            if row and str(row["profile_id"] or "") != profile:
                return
            if row:
                c.execute(
                    "UPDATE janus_chat_receipts SET status='done',response_json=?,updated_at=? WHERE client_message_id=? AND profile_id=?",
                    (json.dumps(response), now, client_message_id, profile),
                )
            else:
                c.execute(
                    "INSERT INTO janus_chat_receipts(client_message_id,profile_id,status,response_json,created_at,updated_at) VALUES(?,?,'done',?,?,?)",
                    (client_message_id, profile, json.dumps(response), now, now),
                )

    interface_chat_module._claim_message = claim_message
    interface_chat_module._finish_message = finish_message
