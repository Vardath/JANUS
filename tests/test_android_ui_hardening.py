from pathlib import Path

BASE = Path('android/app/src/main/java/com/vardath/janus')


def test_authoritative_build_is_native_and_patch_free():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' not in workflow
    assert 'python tools/patch_android_' not in workflow
    assert 'Verify authoritative native Android boundary' in workflow
    assert 'Verify v1.05 navigation and thought bridge' in workflow
    assert not Path('android/app/src/main/assets/index.html').exists()


def test_android_v105_is_direct_native_product():
    text = Path('android/app/build.gradle').read_text(encoding='utf-8')
    assert "versionCode 105" in text
    assert "versionName '1.05'" in text
    assert 'native Back semantics + truthful device background-activity bridge' in text
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    assert 'android.webkit.WebView' not in main
    assert 'JavascriptInterface' not in main


def test_navigation_and_background_activity_bridge_are_present():
    nav = (BASE / 'JanusNavigationPolish.java').read_text(encoding='utf-8')
    thought = (BASE / 'JanusThoughtBridge.java').read_text(encoding='utf-8')
    api = (BASE / 'JanusApiClient.java').read_text(encoding='utf-8')
    app = (BASE / 'JanusApplication.java').read_text(encoding='utf-8')
    assert 'getOnBackInvokedDispatcher' in nav
    assert 'parent.performClick()' in nav
    assert '!"Chat".equals(selected)' in nav
    assert 'JanusNavigationPolish.install(activity)' in app
    assert '[DEVICE JANUS BACKGROUND-ACTIVITY CONTEXT]' in thought
    assert 'zero model/API calls' in thought
    assert 'uninterrupted private stream of consciousness' in thought
    assert 'JanusThoughtBridge.augment(JanusLocalCoreRuntime.get(appContext), message)' in api
    assert 'j.put("message", augmented)' in api
    assert not (BASE / 'JanusThoughtContextPolish.java').exists()


def test_native_ui_keeps_accessibility_and_safe_area_hardening():
    ui = (BASE / 'JanusUiPolish.java').read_text(encoding='utf-8')
    adaptive = (BASE / 'JanusAdaptiveUi.java').read_text(encoding='utf-8')
    for marker in ['WindowInsetsCompat.Type.systemBars()', 'setContentDescription']:
        assert marker in ui or marker in adaptive


def test_chat_decorators_are_idempotent_and_debounced():
    ui = (BASE / 'JanusUiPolish.java').read_text(encoding='utf-8')
    sources = (BASE / 'JanusSourcePolish.java').read_text(encoding='utf-8')
    images = (BASE / 'JanusGeneratedImagePolish.java').read_text(encoding='utf-8')
    reply = (BASE / 'JanusReplyContextPolish.java').read_text(encoding='utf-8')
    assert 'CHAT_ENHANCED' in ui
    assert 'BASE_POLISHED' in ui
    assert 'POLISH_DEBOUNCE_MS' in ui
    assert 'layout.setTag("janus-chat-enhanced")' not in ui
    assert 'child instanceof TextView && !(child instanceof Button)' in ui
    assert 'ENHANCED' in sources and 'MAIN.postDelayed(next, 220L)' in sources
    assert 'MAIN.postDelayed(next, 260L)' in images
    assert 'MAIN.postDelayed(next, 240L)' in reply


def test_structured_chat_history_is_authoritative():
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    store = (BASE / 'JanusChatHistoryStore.java').read_text(encoding='utf-8')
    assert 'JanusChatHistoryStore.append(this, "JANUS", reply, presentation)' in main
    assert 'JSONArray a = JanusChatHistoryStore.read(this)' in main
    assert 'chat_history_native_v2' in store
    assert 'migrateLegacyOnce' in store


def test_messages_and_observe_have_dedicated_native_owners():
    messages = BASE / 'JanusMessagesScreen.java'
    observe = BASE / 'JanusObserveScreen.java'
    assert messages.exists() and observe.exists()
    assert '/desktop/messages?username=' in messages.read_text(encoding='utf-8')
    assert '/desktop/core-observe?username=' in observe.read_text(encoding='utf-8')


def test_fast_offline_chat_retry_is_complete_and_structured():
    queue = (BASE / 'JanusOfflineQueue.java').read_text(encoding='utf-8')
    worker = (BASE / 'JanusQueueRetryWorker.java').read_text(encoding='utf-8')
    for marker in ['scheduleFastRetries', '8L, 25L, 60L', 'JanusQueueRetryWorker.class', 'JanusChatPresentation.fromResponse']:
        assert marker in queue
    for marker in ['class JanusQueueRetryWorker', 'JanusOfflineQueue.flush', 'pendingCount']:
        assert marker in worker
