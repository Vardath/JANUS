package com.vardath.janus;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/**
 * Bridges the device-local deterministic society into the conversational request.
 * It reports persisted observable processing, not phenomenal/private consciousness.
 */
public final class JanusThoughtBridge {
    private JanusThoughtBridge() {}

    public static String augment(JanusLocalCoreRuntime runtime, String userMessage) {
        if (runtime == null || !asksAboutBackgroundActivity(userMessage)) return userMessage;
        try {
            JSONObject s = runtime.statusJson();
            JSONArray events = s.optJSONArray("observe_events");
            StringBuilder recent = new StringBuilder();
            int added = 0;
            if (events != null) {
                for (int i = events.length() - 1; i >= 0 && added < 8; i--) {
                    JSONObject e = events.optJSONObject(i);
                    if (e == null) continue;
                    String type = e.optString("event_type", "");
                    if (!("autonomous_pulse".equals(type) || "process_note".equals(type) || "phase".equals(type) || "maintenance".equals(type))) continue;
                    String detail = e.optString("detail", "").trim();
                    if (detail.isEmpty()) continue;
                    recent.append("- ").append(e.optString("core_name", "core")).append(": ").append(clip(detail, 360)).append('\n');
                    added++;
                }
            }
            String consensus = clip(s.optString("consensus", ""), 700);
            String face = clip(s.optString("interface", ""), 700);
            String context = "\n\n[DEVICE JANUS BACKGROUND-ACTIVITY CONTEXT]\n"
                    + "The Android local 11-core runtime reports phase=" + s.optString("phase", "unknown")
                    + ", running=" + s.optBoolean("running", false)
                    + ", background_cycles_enabled=" + s.optBoolean("background_cycles_enabled", false) + ".\n"
                    + "These are persisted deterministic local processing events with zero model/API calls. They may be described as what the local JANUS cores processed while the user was away, but do not describe them as an uninterrupted private stream of consciousness or phenomenal experience.\n"
                    + (recent.length() == 0 ? "Recent externalizable local activity: none retained.\n" : "Recent externalizable local activity:\n" + recent)
                    + (consensus.isEmpty() ? "" : "Current local consensus: " + consensus + "\n")
                    + (face.isEmpty() ? "" : "Current local interface state: " + face + "\n")
                    + "Answer the user's question using this device activity when relevant; distinguish local deterministic background processing from server/model activity.\n"
                    + "[END DEVICE JANUS CONTEXT]";
            return userMessage + context;
        } catch (Exception ignored) {
            return userMessage;
        }
    }

    static boolean asksAboutBackgroundActivity(String text) {
        String s = text == null ? "" : text.toLowerCase(Locale.ROOT);
        boolean away = s.contains("while i was away") || s.contains("while i was gone") || s.contains("since i left") || s.contains("in the background") || s.contains("background");
        boolean thought = s.contains("think") || s.contains("thinking") || s.contains("thought") || s.contains("doing") || s.contains("working on") || s.contains("processing") || s.contains("up to");
        return away && thought;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        s = s.trim();
        return s.length() <= max ? s : s.substring(0, max) + "…";
    }
}
