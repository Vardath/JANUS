package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Migrates the legacy visible Chat history into structured records while MainActivity is
 * incrementally extracted. Source and generated-image metadata are retained when available.
 */
public final class JanusChatHistoryStore {
    public static final String LEGACY_KEY = "chat_history_native_v1";
    public static final String STRUCTURED_KEY = "chat_history_native_v2";
    private static final int MAX = 80;
    private static SharedPreferences prefs;
    private static SharedPreferences.OnSharedPreferenceChangeListener listener;
    private static boolean syncing;

    private JanusChatHistoryStore() {}

    public static synchronized void install(Context context) {
        if (context == null || prefs != null) return;
        prefs = context.getApplicationContext().getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        syncFromLegacy();
        listener = (p, key) -> {
            if (LEGACY_KEY.equals(key)) syncFromLegacy();
        };
        prefs.registerOnSharedPreferenceChangeListener(listener);
    }

    public static synchronized String structuredJson(Context context) {
        install(context);
        return prefs == null ? "[]" : prefs.getString(STRUCTURED_KEY, "[]");
    }

    private static synchronized void syncFromLegacy() {
        if (prefs == null || syncing) return;
        syncing = true;
        try {
            JSONArray legacy = new JSONArray(prefs.getString(LEGACY_KEY, "[]"));
            JSONArray next = new JSONArray();
            int start = Math.max(0, legacy.length() - MAX);
            for (int i = start; i < legacy.length(); i++) {
                JSONObject old = legacy.optJSONObject(i);
                if (old == null) continue;
                String who = old.optString("who", "JANUS");
                String body = old.optString("body", "");
                JSONObject record = new JSONObject();
                record.put("who", who);
                record.put("body", body);
                record.put("at", old.optLong("at", System.currentTimeMillis()));
                record.put("schema", 2);
                if ("JANUS".equals(who)) {
                    JanusChatPresentation presentation = JanusChatResponseRegistry.findForReply(body);
                    if (presentation != null) {
                        record.put("presentation", presentation.toJson());
                        record.put("body", presentation.reply);
                    }
                }
                next.put(record);
            }
            prefs.edit().putString(STRUCTURED_KEY, next.toString()).apply();
        } catch (Exception ignored) {
        } finally {
            syncing = false;
        }
    }
}
