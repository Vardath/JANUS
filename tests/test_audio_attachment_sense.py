from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_android_audio_is_explicit_push_to_talk_and_file_import_only():
    manifest = text("android/app/src/main/AndroidManifest.xml")
    main = text("android/app/src/main/java/com/vardath/janus/MainActivity.java")
    voice = text("android/app/src/main/java/com/vardath/janus/JanusDeviceVoice.java")
    ui = text("android/app/src/main/java/com/vardath/janus/JanusVoiceUiPolish.java")
    assert "android.permission.RECORD_AUDIO" in manifest
    assert "android.permission.CAMERA" not in manifest
    assert "Intent.ACTION_OPEN_DOCUMENT" in main
    assert 'i.setType("*/*")' in main
    assert "startPushToTalk" in voice
    assert "requestMicPermission" in voice
    assert "SpeechRecognizer.createOnDeviceSpeechRecognizer" in voice
    assert "send.performClick()" in ui
    assert "MediaRecorder" not in voice
    assert "AudioRecord" not in voice
    assert "Service" not in ui


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


def test_audio_paths_do_not_add_ambient_capture_or_camera_access():
    chat = text("server_v2/chat.py")
    voice = text("android/app/src/main/java/com/vardath/janus/JanusDeviceVoice.java")
    ui = text("android/app/src/main/java/com/vardath/janus/JanusVoiceUiPolish.java")
    manifest = text("android/app/src/main/AndroidManifest.xml")
    assert "MediaRecorder" not in chat
    assert "AudioRecord" not in chat
    assert "MediaRecorder" not in voice
    assert "AudioRecord" not in voice
    assert "startForegroundService" not in voice + ui
    assert "startService" not in voice + ui
    assert "CAMERA" not in manifest
    assert "background_audio" not in chat
