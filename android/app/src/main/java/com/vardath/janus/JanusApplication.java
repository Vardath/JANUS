package com.vardath.janus;

import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;

/** Application bootstrap for the authoritative native JANUS Android rebuild. */
public class JanusApplication extends Application {
    private static final String BOOT_PREFS = "janus_native_rebuild_bootstrap";
    private static final String CLEAN_MARKER = "v082_clean_client_initialized";

    @Override public void onCreate() {
        super.onCreate();

        // The rebuilt client intentionally does not inherit local state from the
        // broken WebView/patch-era applications. Server-owned account, memory and
        // continuity are recovered only after the user signs in successfully.
        SharedPreferences boot = getSharedPreferences(BOOT_PREFS, Context.MODE_PRIVATE);
        if (!boot.getBoolean(CLEAN_MARKER, false)) {
            getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE).edit().clear().commit();
            boot.edit().putBoolean(CLEAN_MARKER, true).commit();
        }

        JanusLocalCoreRuntime.get(this).start();
    }
}
