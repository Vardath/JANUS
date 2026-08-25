from __future__ import annotations

import json

from server_v2.front_serialization_guard import serializable_front_state
from server_v2.senses import Appraisal


def main() -> None:
    front = {
        "core": "front",
        "posture": "explore",
        "summary": "bounded Front stream",
        "appraisal": Appraisal(confidence=0.7, salience=0.8, uncertainty=0.3),
    }
    safe = serializable_front_state(front)
    assert isinstance(safe["appraisal"], dict), safe
    encoded = json.dumps(safe, ensure_ascii=False)
    assert '"confidence"' in encoded
    print("Front Appraisal serialization boundary OK")


if __name__ == "__main__":
    main()
