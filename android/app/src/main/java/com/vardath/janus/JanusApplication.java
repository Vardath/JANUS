package com.vardath.janus;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;

/** Application bootstrap for the authoritative native JANUS Android rebuild. */
public class JanusApplication extends Application {
    private static final String BOOT_PREFS = "janus_native_rebuild_bootstrap";
    private static final String CLEAN_MARKER = "v082_clean_client_initialized";

    @Override public void onCreate() {
        super.onCreate();
        SharedPreferences boot = getSharedPreferences(BOOT_PREFS, Context.MODE_PRIVATE);
        if (!boot.getBoolean(CLEAN_MARKER, false)) {
            getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE).edit().clear().commit();
            boot.edit().putBoolean(CLEAN_MARKER, true).commit();
        }
        JanusChatResponseRegistry.init(this);
        JanusChatHistoryStore.install(this);

        registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks() {
            private void install(Activity activity) {
                JanusChatHistoryBridge.prepare(activity);
                JanusUiPolish.install(activity);
                JanusProductPolish.install(activity);
                JanusScreenStatePolish.install(activity);
                JanusFeaturePolish.install(activity);
                JanusReplyContextPolish.install(activity);
                JanusSourcePolish.install(activity);
                JanusGeneratedImagePolish.install(activity);
                JanusAdaptiveUi.install(activity);
                JanusChatHistoryBridge.capture(activity);
            }
            @Override public void onActivityCreated(Activity activity, Bundle state) { install(activity); }
            @Override public void onActivityStarted(Activity activity) {}
            @Override public void onActivityResumed(Activity activity) { install(activity); }
            @Override public void onActivityPaused(Activity activity) { JanusChatHistoryBridge.capture(activity); }
            @Override public void onActivityStopped(Activity activity) { JanusChatHistoryBridge.capture(activity); }
            @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) { JanusChatHistoryBridge.capture(activity); }
            @Override public void onActivityDestroyed(Activity activity) { JanusChatHistoryBridge.capture(activity); }
        });

        JanusLocalCoreRuntime.get(this).start();
    }
}
