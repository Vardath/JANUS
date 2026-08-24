from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_android_keeps_audio_acquisition_user_initiated_without_microphone_permission():
    manifest = text("android/app/src/main/AndroidManifest.xml")
    main = text("android/app/src/main/java/com/vardath/janus/MainActivity.java")
    assert "android.permission.RECORD_AUDIO" not in manifest
    assert "android.permission.CAMERA" not in manifest
    assert "Intent.ACTION_OPEN_DOCUMENT" in main
    assert 'i.setType("*/*")' in main


def test_audio_mime_is_classified_before_generic_extracted_document_text():
    chat = text("server_v2/chat.py")
    audio_at = chat.index('if mime.startswith("audio/")')
    generic_text_at = chat.index('text=str(row["extracted_text"] or "").strip()', audio_at)
    assert audio_at < generic_text_at
    assert "_audio_transcript(account_id,row)" in chat
    assert "SOURCE AUDIO" in chat


def test_audio_transcription_is_foreground_governed_cached_and_typed():
    chat = text("server_v2/chat.py")
    assert 'governance.permit(account_id, "audio_transcription", 0.004)' in chat
    assert 'JANUS_AUDIO_TRANSCRIBE_MODEL' in chat
    assert 'audio.transcriptions.create' in chat
    assert "UPDATE v2_files SET extracted_text=?" in chat
    assert "extraction_status='audio_transcribed'" in chat
    assert 'sensory_bus.ingest(\n            account_id, "audio"' in chat
    assert '"cached": True' in chat
    assert '"cached": False' in chat


def test_audio_transcription_does_not_add_ambient_device_permissions_or_background_capture():
    chat = text("server_v2/chat.py")
    manifest = text("android/app/src/main/AndroidManifest.xml")
    assert "MediaRecorder" not in chat
    assert "AudioRecord" not in chat
    assert "RECORD_AUDIO" not in manifest
    assert "CAMERA" not in manifest
    assert "background_audio" not in chat
