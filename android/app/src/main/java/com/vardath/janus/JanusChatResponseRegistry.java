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
    private static Context appContext;
    private JanusChatResponseRegistry() {}

    public static synchronized void init(Context context) {
        if (prefs != null || context == null) return;
        appContext = context.getApplicationContext();
        prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
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
            JSONObject root = new JSONObject(rawJson);
            JSONObject localCounsel = root.optJSONObject("local_core_counsel");
            if (localCounsel != null && localCounsel.length() > 0) {
                JanusRecursiveCoreBridge.applyAiCounsel(localCounsel);
                // The counsel remains distinct inside each recursive core. The outer
                // local society receives only a bounded notification that a revision
                // occurred, never the model's private reasoning trace.
                if (appContext != null) JanusLocalTypedSense.ingest(appContext, "peer", "recursive_ai_counsel",
                        "Per-core AI counsel returned for the local recursive JANUS society; each addressed core revised against its peers.");
            }
            remember(JanusChatPresentation.fromResponse(root, rawJson));
        } catch (Exception ignored) {}
    }

    /** Re-seed the bounded renderer registry from authoritative structured history. */
    public static synchronized void remember(JanusChatPresentation presentation) {
        if (presentation == null) return;
        if (presentation.reply.isBlank() && presentation.sources.isEmpty() && presentation.generatedImage == null) return;
        RECENT.removeIf(p -> !presentation.reply.isBlank() && presentation.reply.equals(p.reply));
        RECENT.addLast(presentation);
        while (RECENT.size() > MAX) RECENT.removeFirst();
        persist();
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

    /** Clear account-bound presentation metadata during sign-out/account transition. */
    public static synchronized void clear(Context context) {
        init(context);
        RECENT.clear();
        if (prefs != null) prefs.edit().remove(KEY).apply();
    }

    private static void persist() {
        if (prefs == null) return;
        JSONArray a = new JSONArray(); for (JanusChatPresentation p : RECENT) a.put(p.toJson());
        prefs.edit().putString(KEY, a.toString()).apply();
    }
}
