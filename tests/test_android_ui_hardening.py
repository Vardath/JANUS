from pathlib import Path

BASE = Path('android/app/src/main/java/com/vardath/janus')


def test_authoritative_build_is_native_and_patch_free():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' not in workflow
    assert 'python tools/patch_android_' not in workflow
    assert 'Verify authoritative native Android boundary' in workflow
    assert 'Verify v1.03 structured Chat and extracted screen ownership' in workflow
    assert not Path('android/app/src/main/assets/index.html').exists()


def test_android_v103_is_direct_native_product():
    text = Path('android/app/build.gradle').read_text(encoding='utf-8')
    assert "versionCode 103" in text
    assert "versionName '1.03'" in text
    assert 'extracted native Messages + read-only Observe screen ownership' in text
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    assert 'android.webkit.WebView' not in main
    assert 'JavascriptInterface' not in main


def test_native_ui_keeps_accessibility_and_safe_area_hardening():
    ui = (BASE / 'JanusUiPolish.java').read_text(encoding='utf-8')
    adaptive = (BASE / 'JanusAdaptiveUi.java').read_text(encoding='utf-8')
    for marker in ['WindowInsetsCompat.Type.systemBars()', 'setContentDescription']:
        assert marker in ui or marker in adaptive


def test_structured_chat_history_is_authoritative():
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    store = (BASE / 'JanusChatHistoryStore.java').read_text(encoding='utf-8')
    app = (BASE / 'JanusApplication.java').read_text(encoding='utf-8')
    assert 'JanusChatHistoryStore.append(this, "JANUS", reply, presentation)' in main
    assert 'JSONArray a = JanusChatHistoryStore.read(this)' in main
    assert 'chat_history_native_v2' in store
    assert 'migrateLegacyOnce' in store
    assert 'JanusChatV2Surface' not in app
    assert 'JanusChatHistoryBridge' not in app
    assert not (BASE / 'JanusChatV2Surface.java').exists()
    assert not (BASE / 'JanusChatHistoryBridge.java').exists()


def test_messages_and_observe_have_dedicated_native_owners():
    messages = BASE / 'JanusMessagesScreen.java'
    observe = BASE / 'JanusObserveScreen.java'
    assert messages.exists() and observe.exists()
    mt = messages.read_text(encoding='utf-8')
    ot = observe.read_text(encoding='utf-8')
    assert 'Owns native Messages presentation and message-state actions' in mt
    assert '/desktop/messages?username=' in mt
    assert 'Answer in Chat' in mt
    assert 'Read-only native Observe surface' in ot
    assert '/desktop/core-observe?username=' in ot
    assert 'Refresh snapshot' in ot


def test_fast_offline_chat_retry_is_complete_and_structured():
    queue = (BASE / 'JanusOfflineQueue.java').read_text(encoding='utf-8')
    worker_path = BASE / 'JanusQueueRetryWorker.java'
    assert worker_path.exists()
    worker = worker_path.read_text(encoding='utf-8')
    for marker in ['scheduleFastRetries', '8L, 25L, 60L', 'JanusQueueRetryWorker.class', 'JanusChatPresentation.fromResponse']:
        assert marker in queue
    for marker in ['class JanusQueueRetryWorker', 'JanusOfflineQueue.flush', 'pendingCount']:
        assert marker in worker
