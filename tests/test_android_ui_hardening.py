from pathlib import Path

BASE = Path('android/app/src/main/java/com/vardath/janus')


def test_authoritative_build_is_native_and_patch_free():
    workflow = Path('.github/workflows/build-android.yml').read_text(encoding='utf-8')
    assert 'python tools/compose_android_phase3.py' not in workflow
    assert 'python tools/patch_android_' not in workflow
    assert 'Verify authoritative native Android boundary' in workflow
    assert 'Verify v1.08 governed self-diagnosis and Supervisor handoff' in workflow
    assert not Path('android/app/src/main/assets/index.html').exists()


def test_android_v110_is_direct_native_product():
    text = Path('android/app/build.gradle').read_text(encoding='utf-8')
    assert "versionCode 110" in text
    assert "versionName '1.10'" in text
    assert 'app-only appearance isolation' in text
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    assert 'android.webkit.WebView' not in main
    assert 'JavascriptInterface' not in main


def test_governed_supervisor_handoff_and_client_crash_replay_are_present():
    app = (BASE / 'JanusApplication.java').read_text(encoding='utf-8')
    api = (BASE / 'JanusApiClient.java').read_text(encoding='utf-8')
    crash = (BASE / 'JanusClientDiagnostics.java').read_text(encoding='utf-8')
    handoff = (BASE / 'JanusMaintenanceSupervisorPolish.java').read_text(encoding='utf-8')
    assert 'JanusClientDiagnostics.install(this)' in app
    assert 'JanusClientDiagnostics.flushPending(activity)' in app
    assert 'JanusMaintenanceSupervisorPolish.install(activity)' in app
    assert 'j.put("user_visible_message", message)' in api
    assert 'Thread.UncaughtExceptionHandler' in crash
    assert '/maintenance/diagnostics/report' in crash
    assert 'Copy handoff' in handoff
    assert 'Share to ChatGPT' in handoff
    assert '/maintenance/supervisor-handoff' in handoff
    assert 'Nothing is sent automatically' in handoff


def test_navigation_system_chrome_and_core_map_are_hardened():
    nav = (BASE / 'JanusNavigationPolish.java').read_text(encoding='utf-8')
    chrome = (BASE / 'JanusSystemChrome.java').read_text(encoding='utf-8')
    core_map = (BASE / 'JanusCoreMapView.java').read_text(encoding='utf-8')
    app = (BASE / 'JanusApplication.java').read_text(encoding='utf-8')
    manifest = Path('android/app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')
    assert 'enableOnBackInvokedCallback="true"' in manifest
    assert 'getOnBackInvokedDispatcher' in nav
    assert 'parent.performClick()' in nav
    assert '!"Chat".equals(selected)' in nav
    assert 'JanusNavigationPolish.install(activity)' in app
    assert 'JanusSystemChrome.install(activity)' in app
    assert 'theme_mode' not in chrome
    assert 'accent' not in chrome
    assert 'registerOnSharedPreferenceChangeListener' not in chrome
    assert 'setStatusBarColor' not in chrome
    assert 'setNavigationBarColor' not in chrome
    assert 'Configuration.UI_MODE_NIGHT_MASK' in chrome
    assert 'LAYER_TYPE_SOFTWARE' not in core_map
    assert 'setShadowLayer' not in core_map
    assert 'catch (Throwable ignored)' in core_map
    assert 'drawFallback' in core_map


def test_janus_theme_preferences_are_app_view_only():
    main = (BASE / 'MainActivity.java').read_text(encoding='utf-8')
    chrome = (BASE / 'JanusSystemChrome.java').read_text(encoding='utf-8')
    assert 'putString("theme_mode",mode)' in main
    assert 'putString("accent",accent)' in main
    assert 'backgroundColor()' in main
    assert 'surfaceColor()' in main
    assert 'accentColor()' in main
    assert 'theme_mode' not in chrome
    assert 'accent' not in chrome


def test_background_activity_bridge_and_active_fano_policy_remain_present():
    thought = (BASE / 'JanusThoughtBridge.java').read_text(encoding='utf-8')
    policy = (BASE / 'JanusFanoPolicy.java').read_text(encoding='utf-8')
    sense = (BASE / 'JanusSensePolicy.java').read_text(encoding='utf-8')
    runtime = (BASE / 'JanusLocalCoreRuntime.java').read_text(encoding='utf-8')
    api = (BASE / 'JanusApiClient.java').read_text(encoding='utf-8')
    assert '[DEVICE JANUS BACKGROUND-ACTIVITY CONTEXT]' in thought
    assert 'between messages' in thought
    assert 'Current Fano attention orientations' in thought
    assert 'JanusThoughtBridge.augment(JanusLocalCoreRuntime.get(appContext), message)' in api
    for marker in ['truth/grounding', 'valence/welfare', 'significance/conflict', 'pattern/context', 'understanding/model', 'possibility/imagination', 'continuity/experience']:
        assert marker in policy
    for marker in ['confidence', 'valence', 'salience', 'uncertainty', 'novelty', 'urgency', 'familiarity', 'risk', 'opportunity', 'conflict']:
        assert marker in sense
    assert 'JanusFanoPolicy.directive(direction)' in runtime
    assert 'active_orientation' in runtime
    assert 'active_salience_percent' in runtime


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
