package com.vardath.janus;

import org.json.JSONObject;

import java.util.ArrayDeque;
import java.util.Deque;

/** Small in-process handoff from the HTTP layer to native Chat presentation. */
public final class JanusChatResponseRegistry {
    private static final int MAX = 16;
    private static final Deque<JanusChatPresentation> RECENT = new ArrayDeque<>();
    private JanusChatResponseRegistry() {}

    public static synchronized void capture(String rawJson) {
        try {
            JanusChatPresentation presentation = JanusChatPresentation.fromResponse(new JSONObject(rawJson), rawJson);
            if (presentation.reply.isBlank() && presentation.sources.isEmpty()) return;
            RECENT.addLast(presentation);
            while (RECENT.size() > MAX) RECENT.removeFirst();
        } catch (Exception ignored) {}
    }

    public static synchronized JanusChatPresentation consumeForReply(String reply) {
        if (reply == null) return null;
        JanusChatPresentation match = null;
        for (JanusChatPresentation p : RECENT) {
            if (reply.trim().startsWith(p.reply.trim()) || p.reply.trim().startsWith(reply.trim())) match = p;
        }
        if (match != null) RECENT.remove(match);
        return match;
    }
}
