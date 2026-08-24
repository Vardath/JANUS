package com.vardath.janus;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Transitional UI bridge that makes structured v2 Chat history authoritative
 * without requiring a risky wholesale rewrite of MainActivity.
 *
 * MainActivity may continue reading/writing the legacy preference during the
 * compatibility window; this bridge projects v2 into that view on entry and
 * captures new visible records back into v2. Rich JANUS presentation metadata
 * is preserved from the response registry whenever available.
 */
public final class JanusChatHistoryBridge {
    private static boolean syncing;
    private JanusChatHistoryBridge() {}

    public static synchronized void prepare(Activity activity) {
        if (activity == null || syncing) return;
        syncing = true;
        try {
            JSONArray v2 = JanusChatHistoryStore.read(activity);
            JSONArray visible = new JSONArray();
            for (int i = 0; i < v2.length(); i++) {
                JSONObject record = v2.optJSONObject(i);
                if (record == null) continue;
                JSONObject legacy = new JSONObject();
                legacy.put("who", record.optString("who", "JANUS"));
                legacy.put("body", record.optString("body", ""));
                legacy.put("at", record.optLong("at", System.currentTimeMillis()));
                visible.put(legacy);
            }
            prefs(activity).edit().putString(JanusChatHistoryStore.LEGACY_KEY, visible.toString()).apply();
        } catch (Exception ignored) {
        } finally { syncing = false; }
    }

    public static synchronized void capture(Activity activity) {
        if (activity == null || syncing) return;
        syncing = true;
        try {
            JSONArray visible = new JSONArray(prefs(activity).getString(JanusChatHistoryStore.LEGACY_KEY, "[]"));
            JSONArray current = JanusChatHistoryStore.read(activity);
            int start = Math.min(current.length(), visible.length());
            for (int i = start; i < visible.length(); i++) {
                JSONObject item = visible.optJSONObject(i);
                if (item == null) continue;
                String who = item.optString("who", "JANUS");
                String body = item.optString("body", "");
                JanusChatPresentation presentation = "JANUS".equals(who) ? JanusChatResponseRegistry.findForReply(body) : null;
                JanusChatHistoryStore.append(activity, who, body, presentation);
            }
        } catch (Exception ignored) {
        } finally { syncing = false; }
    }

    public static synchronized void clear(Activity activity) {
        if (activity == null) return;
        JanusChatHistoryStore.clear(activity);
        prefs(activity).edit().putString(JanusChatHistoryStore.LEGACY_KEY, "[]").apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
    }
}
