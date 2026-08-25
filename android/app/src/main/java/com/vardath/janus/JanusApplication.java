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
                // Stability-first shell. The native MainActivity already owns all product screens.
                // Global-layout polishers previously walked and sometimes mutated the same live
                // hierarchy concurrently, which could terminate the Activity when detail screens
                // such as Cores, Memory and Settings were created. Keep only non-mutating chrome,
                // Back navigation and diagnostics until decoration is reintroduced through an
                // explicit render pass rather than ViewTreeObserver mutation.
                JanusSystemChrome.install(activity);
                JanusNavigationPolish.install(activity);
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
