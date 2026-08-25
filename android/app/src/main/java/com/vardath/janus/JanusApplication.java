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
        SharedPreferences boot = getSharedPreferences(BOOT_PREFS, Context.MODE_PRIVATE);
        if (!boot.getBoolean(RC1_MIGRATION_MARKER, false)) boot.edit().putBoolean(RC1_MIGRATION_MARKER, true).apply();
        JanusChatResponseRegistry.init(this);
        JanusChatHistoryStore.install(this);

        registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks() {
            private void install(Activity activity) {
                // Stability-first shell. MainActivity owns the actual product screens.
                // High-frequency global-layout presentation layers are temporarily disabled
                // because several of them walk and mutate the same hierarchy while detail
                // screens are being created. Keep only system chrome, Back navigation,
                // diagnostics and the governed maintenance handoff.
                JanusSystemChrome.install(activity);
                JanusNavigationPolish.install(activity);
                JanusMaintenanceSupervisorPolish.install(activity);
            }
            @Override public void onActivityCreated(Activity activity, Bundle state) { install(activity); }
            @Override public void onActivityStarted(Activity activity) {}
            @Override public void onActivityResumed(Activity activity) { install(activity); JanusSystemChrome.apply(activity); JanusClientDiagnostics.flushPending(activity); }
            @Override public void onActivityPaused(Activity activity) {}
            @Override public void onActivityStopped(Activity activity) {}
            @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}
            @Override public void onActivityDestroyed(Activity activity) {}
        });

        JanusLocalCoreRuntime runtime = JanusLocalCoreRuntime.get(this);
        runtime.start();
        JanusRecursiveCoreEngine.get(this).start(runtime);
    }
}
