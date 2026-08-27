package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

/** Authoritative structured Chat history with one-way legacy migration and attachment metadata persistence. */
public final class JanusChatHistoryStore {
    public static final String LEGACY_KEY = "chat_history_native_v1";
    public static final String STRUCTURED_KEY = "chat_history_native_v2";
    private static final String MIGRATED_KEY = "chat_history_native_v2_migrated";
    private static final int MAX = 80;
    private static SharedPreferences prefs;
    private JanusChatHistoryStore() {}

    public static synchronized void install(Context context) {
        if (context == null || prefs != null) return;
        prefs = context.getApplicationContext().getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        migrateLegacyOnce();
    }

    public static synchronized JSONArray read(Context context) {
        install(context);
        try { return new JSONArray(prefs == null ? "[]" : prefs.getString(STRUCTURED_KEY, "[]")); }
        catch (Exception ignored) { return new JSONArray(); }
    }

    public static synchronized String structuredJson(Context context) { return read(context).toString(); }

    public static synchronized void append(Context context, String who, String body, JanusChatPresentation presentation) {
        append(context, who, body, presentation, null);
    }

    public static synchronized void append(Context context, String who, String body, JanusChatPresentation presentation, JSONArray attachments) {
        install(context);
        if (prefs == null) return;
        try {
            JSONArray current = read(context);
            JSONArray next = new JSONArray();
            int start = Math.max(0, current.length() - (MAX - 1));
            for (int i = start; i < current.length(); i++) next.put(current.get(i));
            JSONObject record = new JSONObject();
            record.put("schema", 3);
            record.put("who", who == null ? "JANUS" : who);
            record.put("body", presentation != null && "JANUS".equals(who) ? presentation.reply : (body == null ? "" : body));
            record.put("at", System.currentTimeMillis());
            if (presentation != null) record.put("presentation", presentation.toJson());
            if (attachments != null && attachments.length() > 0) record.put("attachments", attachments);
            next.put(record);
            prefs.edit().putString(STRUCTURED_KEY, next.toString()).apply();
        } catch (Exception ignored) {}
    }

    public static synchronized void clear(Context context) {
        install(context);
        if (prefs != null) prefs.edit().putString(STRUCTURED_KEY, "[]").apply();
    }

    private static void migrateLegacyOnce() {
        if (prefs == null || prefs.getBoolean(MIGRATED_KEY, false)) return;
        try {
            JSONArray existing = new JSONArray(prefs.getString(STRUCTURED_KEY, "[]"));
            if (existing.length() == 0) {
                JSONArray legacy = new JSONArray(prefs.getString(LEGACY_KEY, "[]"));
                JSONArray migrated = new JSONArray();
                int start = Math.max(0, legacy.length() - MAX);
                for (int i = start; i < legacy.length(); i++) {
                    JSONObject old = legacy.optJSONObject(i); if (old == null) continue;
                    String who = old.optString("who", "JANUS"); String body = old.optString("body", "");
                    JSONObject record = new JSONObject();
                    record.put("schema", 2); record.put("who", who); record.put("body", body); record.put("at", old.optLong("at", System.currentTimeMillis()));
                    if ("JANUS".equals(who)) {
                        JanusChatPresentation p = JanusChatResponseRegistry.findForReply(body);
                        if (p != null) { record.put("presentation", p.toJson()); record.put("body", p.reply); }
                    }
                    migrated.put(record);
                }
                prefs.edit().putString(STRUCTURED_KEY, migrated.toString()).apply();
            }
        } catch (Exception ignored) {}
        prefs.edit().putBoolean(MIGRATED_KEY, true).apply();
    }
}
