"""Step 8: conservative decision layer for JANUS explanatory visuals.

The Interface may nominate one visual in its existing Chat turn, but this module
independently decides whether an *automatic* render is actually justified before
any image-generation spend occurs. Explicit user image requests are never blocked
by this explanatory gate and remain subject to the existing image budget/safety
policy.
"""
from __future__ import annotations

import re
from typing import Any

# Topics where a static visual often carries information that prose alone does not.
VISUAL_DOMAINS = re.compile(
    r"\b(diagram|geometry|geometric|topolog(?:y|ical)|spatial|layout|architecture|"
    r"pipeline|flow|network|graph|map|circuit|lattice|projection|symmetr(?:y|ies)|"
    r"coordinate|orientation|cross[- ]?section|layer|hierarch(?:y|ical)|timeline|"
    r"comparison|compare|relationship|interconnection|structure)\b",
    re.I,
)
# Automatic visuals are specifically inappropriate for these common cases.
NO_AUTO = re.compile(
    r"\b(server status|diagnostic|telemetry|heartbeat|login|password|billing|cost status|"
    r"workflow|build status|error code|maintenance status|hello|thanks|thank you)\b",
    re.I,
)
EXPLANATION_WORDS = re.compile(
    r"\b(explain|understand|show how|works|relationship|connect|structure|arrange|"
    r"difference|compare|visuali[sz]e|where|how)\b",
    re.I,
)


def assess(message: str, reply: str, prompt: str | None) -> dict[str, Any]:
    """Return a zero-cost, inspectable recommendation for an automatic visual."""
    message = str(message or "").strip()
    reply = str(reply or "").strip()
    prompt = str(prompt or "").strip()
    combined = f"{message}\n{reply}\n{prompt}"
    reasons: list[str] = []
    score = 0

    if not prompt:
        return {"show": False, "score": 0, "reason": "no_interface_nomination", "reasons": []}
    if NO_AUTO.search(message):
        return {"show": False, "score": 0, "reason": "routine_or_operational_topic", "reasons": ["operational topic"]}
    if VISUAL_DOMAINS.search(combined):
        score += 3; reasons.append("visual/spatial domain")
    if EXPLANATION_WORDS.search(message):
        score += 1; reasons.append("user seeks explanation")
    # A visual should support a substantive explanation, not decorate a short answer.
    if len(reply) >= 650:
        score += 1; reasons.append("substantive explanation")
    if len(prompt) >= 50:
        score += 1; reasons.append("specific visual brief")
    # Very short/simple user turns should not trigger an unsolicited image merely
    # because the model happened to emit a marker.
    if len(message) < 18 and not VISUAL_DOMAINS.search(message):
        score -= 2; reasons.append("short/simple request")

    show = score >= 4
    return {
        "show": show,
        "score": score,
        "reason": "material_explanatory_value" if show else "insufficient_explanatory_value",
        "reasons": reasons,
    }


def install(image_generation_module) -> None:
    """Patch only the automatic-nomination boundary; renderer/cost logic is untouched."""
    if getattr(image_generation_module, "_janus_visual_explanation_installed", False):
        return
    original = image_generation_module.maybe_generate_for_chat

    async def governed(profile: str, message: str, reply: str):
        # Explicit requests continue through the existing Stage-1 implementation.
        if image_generation_module.explicit_image_request(message):
            clean, result = await original(profile, message, reply)
            if isinstance(result, dict):
                result.setdefault("visual_decision", {"show": True, "reason": "explicit_user_request"})
            return clean, result

        clean, nominated = image_generation_module.extract_visual_nomination(reply)
        if not nominated:
            return clean, None
        decision = assess(message, clean, nominated)
        if not decision["show"]:
            # The hidden marker is stripped even when rendering is declined.
            return clean, {"generated": False, "reason": "visual nomination declined", "visual_decision": decision}
        account = image_generation_module._account_by_profile(profile)
        if not account:
            return clean, None
        result = await image_generation_module.generate_for_account(
            account, nominated, origin="auto", quality="medium"
        )
        if isinstance(result, dict):
            result["visual_decision"] = decision
        return clean, result

    image_generation_module.maybe_generate_for_chat = governed
    image_generation_module._janus_visual_explanation_installed = True
