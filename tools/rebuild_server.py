"""Reconstruct the legacy base server module from checked-in compressed fragments.

The modern JANUS app boots through bootstrap.py -> janus_dashboard.py -> dashboard_api.py,
but dashboard_api still extends the historical FastAPI base app defined by server.py.
Keeping reconstruction in one small script makes Render, Docker and CI use the same path.
"""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "server.py"


def rebuild() -> Path:
    parts = sorted(SRC.glob("server.py.gz.b64.*"))
    if not parts:
        raise SystemExit("No src/server.py.gz.b64.* fragments found")
    encoded = b"".join(p.read_bytes().strip() for p in parts)
    try:
        compressed = base64.b64decode(encoded, validate=True)
        source = gzip.decompress(compressed)
    except Exception as exc:
        raise SystemExit(f"Could not reconstruct server.py: {type(exc).__name__}: {exc}") from exc
    if b"FastAPI" not in source or b"app" not in source:
        raise SystemExit("Reconstructed server.py failed basic FastAPI sanity check")
    OUT.write_bytes(source)
    print(f"Rebuilt {OUT} from {len(parts)} fragments ({len(source)} bytes)")
    return OUT


if __name__ == "__main__":
    rebuild()
