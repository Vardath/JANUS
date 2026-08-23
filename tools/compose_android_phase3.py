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
    'id="janusUiRecovery"',
]

JAVA_MARKERS = [
    'pickFile()',
    'ACTION_CREATE_DOCUMENT',
    'ACTION_SEND',
]

EXPECTED_VERSION_CODE = 71
EXPECTED_VERSION_NAME = "0.71"


def run_patch(path: str) -> None:
    print(f"[compose] {path}")
    subprocess.run([sys.executable, path], cwd=ROOT, check=True)


def current_text() -> tuple[str, str, str]:
    html = (ROOT / "android/app/src/main/assets/index.html").read_text(encoding="utf-8")
    java = (ROOT / "android/app/src/main/java/com/vardath/janus/MainActivity.java").read_text(encoding="utf-8")
    gradle = (ROOT / "android/app/build.gradle").read_text(encoding="utf-8")
    return html, java, gradle


def already_consolidated() -> bool:
    html, java, _ = current_text()
    return all(marker in html for marker in HTML_MARKERS) and all(marker in java for marker in JAVA_MARKERS)


def verify() -> None:
    html, java, gradle = current_text()
    missing = [marker for marker in HTML_MARKERS if marker not in html]
    missing += [marker for marker in JAVA_MARKERS if marker not in java]
    if f"versionCode {EXPECTED_VERSION_CODE}" not in gradle or f"versionName '{EXPECTED_VERSION_NAME}'" not in gradle:
        missing.append(f"Android v{EXPECTED_VERSION_NAME} version identity")
    if missing:
        raise SystemExit("Phase 3 composition verification failed; missing: " + ", ".join(missing))
    print(f"[compose] Android Phase 3 composition verified for v{EXPECTED_VERSION_NAME}")


def main() -> int:
    if already_consolidated():
        print("[compose] Android source is already hard-coded/consolidated; no patch scripts will run")
        verify()
        return 0
    for patch in PATCHES:
        run_patch(patch)
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
