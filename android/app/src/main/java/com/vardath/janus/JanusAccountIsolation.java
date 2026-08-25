package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import java.io.File;
import java.lang.reflect.Field;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ScheduledExecutorService;

/**
 * Keeps device-local JANUS cognitive/chat state bound to one signed-in account.
 * Device-only appearance/runtime preferences survive account transitions.
 */
final class JanusAccountIsolation {
    private static final String BINDING_PREFS = "janus_account_binding";
    private static final String BINDING_KEY = "profile";
    private static final String RECURSIVE_PREFS = "janus_recursive_core_engine_v1";
    private static final String[] DEVICE_KEYS = new String[]{
            "theme_mode", "accent", "background_cycles_enabled",
            "observe_telemetry_enabled", "local_background_interval_seconds",
            JanusLanguageSettings.LANGUAGE_KEY, JanusLanguageSettings.SPEECH_KEY
    };

    private JanusAccountIsolation() {}

    static synchronized void beforeSaveSession(Context context, String newProfile) {
        Context app = context.getApplicationContext();
        String clean = newProfile == null ? "" : newProfile.trim();
        SharedPreferences binding = app.getSharedPreferences(BINDING_PREFS, Context.MODE_PRIVATE);
        String previous = binding.getString(BINDING_KEY, "");
        boolean switched = !previous.isBlank() && !clean.isBlank() && !previous.equals(clean);
        if (switched) {
            resetAccountBoundState(app);
            JanusLocalCoreRuntime runtime = JanusLocalCoreRuntime.get(app);
            runtime.start();
            JanusRecursiveCoreEngine.get(app).start(runtime);
        }
        if (!clean.isBlank()) binding.edit().putString(BINDING_KEY, clean).apply();
    }

    static synchronized void clearForSignOut(Context context) {
        Context app = context.getApplicationContext();
        resetAccountBoundState(app);
        app.getSharedPreferences(BINDING_PREFS, Context.MODE_PRIVATE).edit().remove(BINDING_KEY).apply();
    }

    private static void resetAccountBoundState(Context app) {
        // Stop first (which may checkpoint), then clear the account-bound nested state
        // so a stopped engine cannot immediately write the previous account back.
        JanusRecursiveCoreEngine.clearInstance();
        app.getSharedPreferences(RECURSIVE_PREFS, Context.MODE_PRIVATE).edit().clear().commit();
        stopAndDetachLocalRuntime();
        SharedPreferences prefs = app.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        Map<String, Object> keep = new LinkedHashMap<>();
        Map<String, ?> all = prefs.getAll();
        for (String key : DEVICE_KEYS) if (all.containsKey(key)) keep.put(key, all.get(key));
        prefs.edit().clear().commit();
        SharedPreferences.Editor restore = prefs.edit();
        for (Map.Entry<String, Object> entry : keep.entrySet()) put(restore, entry.getKey(), entry.getValue());
        restore.commit();
        JanusChatResponseRegistry.clear(app);
        deleteRecursively(new File(app.getCacheDir(), "shared_artifacts"));
    }

    private static void stopAndDetachLocalRuntime() {
        try {
            Field instanceField = JanusLocalCoreRuntime.class.getDeclaredField("instance");
            instanceField.setAccessible(true);
            Object runtime = instanceField.get(null);
            if (runtime != null) {
                Field schedulerField = JanusLocalCoreRuntime.class.getDeclaredField("scheduler");
                schedulerField.setAccessible(true);
                Object scheduler = schedulerField.get(runtime);
                if (scheduler instanceof ScheduledExecutorService) ((ScheduledExecutorService) scheduler).shutdownNow();
            }
            instanceField.set(null, null);
        } catch (Exception ignored) {}
    }

    private static void put(SharedPreferences.Editor editor, String key, Object value) {
        if (value instanceof String) editor.putString(key, (String) value);
        else if (value instanceof Boolean) editor.putBoolean(key, (Boolean) value);
        else if (value instanceof Integer) editor.putInt(key, (Integer) value);
        else if (value instanceof Long) editor.putLong(key, (Long) value);
        else if (value instanceof Float) editor.putFloat(key, (Float) value);
    }

    private static void deleteRecursively(File file) {
        if (file == null || !file.exists()) return;
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) for (File child : children) deleteRecursively(child);
        }
        try { file.delete(); } catch (Exception ignored) {}
    }
}
