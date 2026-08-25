package com.vardath.janus;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;

/** Application bootstrap for the authoritative native JANUS Android rebuild. */
public class JanusApplication extends Application {
    private static final String BOOT_PREFS = "janus_native_rebuild_bootstrap";
    private static final String RC1_MIGRATION_MARKER = "v109_rc1_nondestructive_migration";

    @Override public void onCreate() {
        super.onCreate();
        JanusClientDiagnostics.install(this);

        // RC1 migration invariant: upgrades must preserve the existing JANUS account
        // session, local 11-core state, memories and user options. Historical rebuilds
        // used a one-time preference wipe here; that is intentionally retired.
        SharedPreferences boot = getSharedPreferences(BOOT_PREFS, Context.MODE_PRIVATE);
        if (!boot.getBoolean(RC1_MIGRATION_MARKER, false)) {
            boot.edit().putBoolean(RC1_MIGRATION_MARKER, true).apply();
        }

        JanusChatResponseRegistry.init(this);
        JanusChatHistoryStore.install(this);

        registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks() {
            private void install(Activity activity) {
                JanusUiPolish.install(activity);
                JanusSystemChrome.install(activity);
                JanusProductPolish.install(activity);
                JanusScreenStatePolish.install(activity);
                JanusFeaturePolish.install(activity);
                JanusLanguagePolish.install(activity);
                JanusReplyContextPolish.install(activity);
                JanusSourcePolish.install(activity);
                JanusGeneratedImagePolish.install(activity);
                JanusAdaptiveUi.install(activity);
                JanusNavigationPolish.install(activity);
                JanusMaintenanceSupervisorPolish.install(activity);
                JanusVoiceUiPolish.install(activity);
                JanusUiLocalizationPolish.install(activity);
            }
            @Override public void onActivityCreated(Activity activity, Bundle state) { install(activity); }
            @Override public void onActivityStarted(Activity activity) {}
            @Override public void onActivityResumed(Activity activity) {
                install(activity);
                JanusSystemChrome.apply(activity);
                JanusClientDiagnostics.flushPending(activity);
            }
            @Override public void onActivityPaused(Activity activity) {}
            @Override public void onActivityStopped(Activity activity) {}
            @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}
            @Override public void onActivityDestroyed(Activity activity) { JanusVoiceUiPolish.destroy(activity); }
        });

        JanusLocalCoreRuntime runtime = JanusLocalCoreRuntime.get(this);
        runtime.start();
        // Every outer local core owns a complete internal JANUS/Fano processor.
        // This nested background cognition is deterministic and makes zero API calls.
        JanusRecursiveCoreEngine.get(this).start(runtime);
    }
}
