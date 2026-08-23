from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

PATCHES = [
    "tools/patch_android_file_attachments.py",
    "tools/patch_android_artifacts.py",
    "tools/patch_android_artifact_export.py",
    "tools/patch_android_research_workspace.py",
    "tools/patch_android_maintenance_review.py",
    "tools/patch_android_research_provenance.py",
    "tools/patch_android_protocol_capabilities.py",
    "tools/patch_android_ui_hardening.py",
    "tools/patch_android_runtime_cores_v068.py",
]

HTML_MARKERS = [
    'id="attachBtn"',
    'Artifacts',
    'Download / Export',
    'Share',
    'Research workspace',
    'Maintenance review',
    'Background research',
    'Compatibility',
    'id="themeMode"',
    'id="themeAccent"',
]

JAVA_MARKERS = [
    'pickFile()',
    'ACTION_CREATE_DOCUMENT',
    'ACTION_SEND',
]


def run_patch(path: str) -> None:
    print(f"[compose] {path}")
    subprocess.run([sys.executable, path], cwd=ROOT, check=True)


def verify() -> None:
    html = (ROOT / "android/app/src/main/assets/index.html").read_text(encoding="utf-8")
    java = (ROOT / "android/app/src/main/java/com/vardath/janus/MainActivity.java").read_text(encoding="utf-8")
    gradle = (ROOT / "android/app/build.gradle").read_text(encoding="utf-8")

    missing = [marker for marker in HTML_MARKERS if marker not in html]
    missing += [marker for marker in JAVA_MARKERS if marker not in java]
    if "versionCode 70" not in gradle or "versionName '0.70'" not in gradle:
        missing.append("Android v0.70 version identity")
    if missing:
        raise SystemExit("Phase 3 composition verification failed; missing: " + ", ".join(missing))

    print("[compose] Android Phase 3 composition verified")


def main() -> int:
    for patch in PATCHES:
        run_patch(patch)
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
