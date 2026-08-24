package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayDeque;
import java.util.Deque;

/** Bounded Chat presentation handoff with restart persistence for source/image metadata. */
public final class JanusChatResponseRegistry {
    private static final int MAX = 16;
    private static final String PREFS = "janus_chat_presentation_v095";
    private static final String KEY = "recent";
    private static final Deque<JanusChatPresentation> RECENT = new ArrayDeque<>();
    private static SharedPreferences prefs;
    private JanusChatResponseRegistry() {}

    public static synchronized void init(Context context) {
        if (prefs != null || context == null) return;
        prefs = context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONArray a = new JSONArray(prefs.getString(KEY, "[]"));
            for (int i = Math.max(0, a.length() - MAX); i < a.length(); i++) {
                JSONObject x = a.optJSONObject(i); if (x != null) RECENT.addLast(JanusChatPresentation.fromStored(x));
            }
        } catch (Exception ignored) {}
    }

    public static synchronized void capture(Context context, String rawJson) { init(context); capture(rawJson); }

    public static synchronized void capture(String rawJson) {
        try {
            JanusChatPresentation presentation = JanusChatPresentation.fromResponse(new JSONObject(rawJson), rawJson);
            if (presentation.reply.isBlank() && presentation.sources.isEmpty() && presentation.generatedImage == null) return;
            RECENT.addLast(presentation);
            while (RECENT.size() > MAX) RECENT.removeFirst();
            persist();
        } catch (Exception ignored) {}
    }

    /** Non-destructive lookup so source and image renderers can share the same presentation. */
    public static synchronized JanusChatPresentation findForReply(String reply) {
        if (reply == null) return null;
        JanusChatPresentation match = null;
        String needle = reply.trim();
        for (JanusChatPresentation p : RECENT) {
            String candidate = p.reply.trim();
            if (!needle.isEmpty() && (needle.startsWith(candidate) || candidate.startsWith(needle))) match = p;
        }
        return match;
    }

    /** Backward-compatible alias retained for the source renderer. */
    public static synchronized JanusChatPresentation consumeForReply(String reply) { return findForReply(reply); }

    private static void persist() {
        if (prefs == null) return;
        JSONArray a = new JSONArray(); for (JanusChatPresentation p : RECENT) a.put(p.toJson());
        prefs.edit().putString(KEY, a.toString()).apply();
    }
}
