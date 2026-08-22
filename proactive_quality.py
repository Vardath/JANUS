"""Quality control for JANUS autonomous/proactive Messages.

This module is intentionally deterministic and zero-API.  It prevents background
plumbing/telemetry from becoming a user notification and gives the paid promoter a
simple novelty/usefulness gate.  Explicit user-requested outbox items are not blocked
by this policy; it is for autonomous/background material.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_PROCESS = {
    "core","cores","cycle","cycles","routing","interface","consensus","hemisphere","hemispheres",
    "integration","integrating","grounding","telemetry","fano","projection","processing","process",
    "specialist","specialists","pipeline","runtime","counter","counters","phase","pending","pulse",
}
_SUBSTANCE_HINTS = {
    "because","therefore","suggests","evidence","source","result","found","finding","observed","compared",
    "difference","connection","question","test","measure","prediction","alternative","counterexample",
    "document","image","screenshot","research","study","paper","history","memory","report","web",
}
_TELEMETRY_PATTERNS = (
    r"\bcuriosity\s+0\.\d+", r"\btension\s+0\.\d+", r"\bconfidence\s+0\.\d+",
    r"\bsalience\s+0\.\d+", r"\bfano\s+d\d+", r"\b1\|3\|4\b", r"\bcycles?\s*[:=]?\s*\d+",
    r"\bshared terms?\s*:", r"\bnumeric check\s*:", r"\bmemory #\d+", r"\bpulse\s+\d+",
)


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(str(text or ""))}


def _message_text(detail: Any) -> str:
    raw = str(detail or "").strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return str(obj.get("text") or obj.get("message") or obj.get("result") or raw).strip()
    except Exception:
        pass
    return raw


def similarity(a: str, b: str) -> float:
    x, y = _tokens(a), _tokens(b)
    if not x or not y:
        return 0.0
    return len(x & y) / max(1, len(x | y))


def assess(text: str, recent_texts: Iterable[str] = ()) -> dict[str, Any]:
    """Return deterministic user-value score and reasons for autonomous text."""
    clean = " ".join(str(text or "").split()).strip()
    words = _tokens(clean)
    if not clean:
        return {"pass": False, "score": 0.0, "reasons": ["empty"], "telemetry_heavy": False, "max_similarity": 0.0}

    score = 0.25
    reasons: list[str] = []
    length = len(clean)
    if 90 <= length <= 1400:
        score += 0.18
    elif length < 45:
        score -= 0.25; reasons.append("too-short")
    elif length > 2600:
        score -= 0.12; reasons.append("too-long")

    substance = len(words & _SUBSTANCE_HINTS)
    if substance >= 2:
        score += min(0.22, 0.05 * substance)
    else:
        reasons.append("thin-subject-matter")

    process_count = len(words & _PROCESS)
    process_ratio = process_count / max(1, len(words))
    telemetry_hits = sum(1 for p in _TELEMETRY_PATTERNS if re.search(p, clean, re.I))
    telemetry_heavy = telemetry_hits >= 2 or process_ratio >= 0.19
    if telemetry_heavy:
        score -= min(0.48, 0.18 + telemetry_hits * 0.08 + process_ratio)
        reasons.append("process-or-telemetry-heavy")

    # A worthwhile unsolicited message should normally contain a concrete claim,
    # question, comparison or proposed test, not merely "I have been thinking".
    if "?" in clean:
        score += 0.08
    if any(k in clean.lower() for k in ("worth testing", "could test", "would distinguish", "i found", "new result", "one possibility", "this matters because", "i noticed that")):
        score += 0.10

    max_sim = 0.0
    for old in recent_texts:
        max_sim = max(max_sim, similarity(clean, _message_text(old)))
    if max_sim >= 0.72:
        score -= 0.38; reasons.append("near-duplicate")
    elif max_sim >= 0.52:
        score -= 0.18; reasons.append("repetitive")
    else:
        score += 0.06

    score = max(0.0, min(1.0, score))
    threshold = 0.50
    passed = score >= threshold and not telemetry_heavy and max_sim < 0.72
    if passed:
        reasons.append("user-value-threshold-met")
    return {
        "pass": passed,
        "score": round(score, 3),
        "reasons": reasons,
        "telemetry_heavy": telemetry_heavy,
        "max_similarity": round(max_sim, 3),
        "process_ratio": round(process_ratio, 3),
        "substance_terms": substance,
    }


def should_show_stored_message(detail: Any, source: str = "") -> bool:
    """Hide old/legacy autonomous telemetry spam while preserving explicit messages."""
    src = str(source or "").lower()
    if src.startswith("chat") or src in {"user", "manual"}:
        return True
    text = _message_text(detail)
    # Legacy automatic messages get the same minimum quality rule but no novelty
    # comparison because the listing layer should remain cheap.
    return bool(assess(text).get("pass"))
