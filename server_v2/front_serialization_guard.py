from __future__ import annotations

import json
from typing import Any

from .conscious_mind import ConsciousStreamJanusMind


def serializable_front_state(front_state: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded Front state in JSON-safe form for model prompting.

    Front intentionally carries an Appraisal object internally. The model boundary must
    externalize that object with as_dict() before json.dumps; otherwise production Chat
    raises TypeError before the governed model call begins.
    """
    public = dict(front_state or {})
    appraisal = public.get("appraisal")
    if hasattr(appraisal, "as_dict"):
        public["appraisal"] = appraisal.as_dict()
    # Fail here during tests/startup integration if a future Front field is not JSON-safe.
    json.dumps(public, ensure_ascii=False)
    return public


def install() -> None:
    original = ConsciousStreamJanusMind._deliberate_one_call
    if getattr(original, "_janus_front_serialization_safe", False):
        return

    def wrapped(self, *args, **kwargs):
        positional = list(args)
        if "front_state" in kwargs:
            kwargs = dict(kwargs)
            kwargs["front_state"] = serializable_front_state(kwargs.get("front_state") or {})
        elif positional:
            positional[-1] = serializable_front_state(positional[-1])
        return original(self, *positional, **kwargs)

    wrapped._janus_front_serialization_safe = True
    ConsciousStreamJanusMind._deliberate_one_call = wrapped
