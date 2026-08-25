package com.vardath.janus;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Iterator;
import java.util.Locale;

/**
 * Bridges the device-local deterministic society into the conversational request.
 * It reports persisted observable processing, not phenomenal/private consciousness.
 */
public final class JanusThoughtBridge {
    private static final String RECURSIVE_START = "[LOCAL RECURSIVE JANUS CORE STATES]";
    private static final String RECURSIVE_END = "[END LOCAL RECURSIVE JANUS CORE STATES]";
    private JanusThoughtBridge() {}

    public static String augment(JanusLocalCoreRuntime runtime, String userMessage) {
        if (runtime == null) return userMessage;
        try {
            // Ordinary foreground Chat always receives a bounded snapshot from the
            // complete JANUS/Fano processor living inside each of the eleven local
            // top-level cores. This is externalizable state, never private CoT.
            JSONObject recursive = JanusRecursiveCoreEngine.getFromRuntime(runtime).foreground(userMessage);
            String recursiveContext = "\n\n" + RECURSIVE_START + "\n"
                    + clip(recursive.toString(), 24000) + "\n" + RECURSIVE_END;

            if (!asksAboutBackgroundActivity(userMessage)) return userMessage + recursiveContext;

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

            StringBuilder fano = new StringBuilder();
            JSONObject cores = s.optJSONObject("cores");
            if (cores != null) {
                Iterator<String> names = cores.keys();
                while (names.hasNext()) {
                    String name = names.next();
                    JSONObject core = cores.optJSONObject(name);
                    JSONObject fs = core == null ? null : core.optJSONObject("fano");
                    if (fs == null) continue;
                    fano.append("- ").append(name).append(": d").append(fs.optInt("active_direction", 0))
                            .append(" ").append(fs.optString("active_orientation", "unknown"))
                            .append(", salience ").append(fs.optLong("active_salience_percent", 0L)).append("%\n");
                }
            }

            String front = clip(s.optString("front", s.optString("consensus", "")), 900);
            String face = clip(s.optString("interface", ""), 900);
            JSONObject frontAppraisal = s.optJSONObject("front_appraisal");
            JSONObject interfaceAppraisal = s.optJSONObject("interface_appraisal");
            String context = "\n\n[DEVICE JANUS BACKGROUND-ACTIVITY CONTEXT]\n"
                    + "The Android local 11-core runtime reports phase=" + s.optString("phase", "unknown")
                    + ", running=" + s.optBoolean("running", false)
                    + ", background_cycles_enabled=" + s.optBoolean("background_cycles_enabled", false) + ".\n"
                    + "Each of these eleven outer cores now also owns a persistent internal seven-position JANUS/Fano processor. The nested processors revise against peer-core conclusions in deterministic background cycles with zero model/API calls.\n"
                    + "These are persisted deterministic local processing events with zero model/API calls. They are real app-side JANUS processing between messages. Describe what the cores actually processed when asked, rather than claiming that no background thinking/processing occurred. Do not describe this as phenomenal consciousness or an uninterrupted private stream of consciousness.\n"
                    + (recent.length() == 0 ? "Recent externalizable local activity: none retained.\n" : "Recent externalizable local activity:\n" + recent)
                    + (fano.length() == 0 ? "" : "Current outer Fano attention orientations used by the local cores:\n" + fano)
                    + (front.isEmpty() ? "" : "Current local Front appraisal/intention state: " + front + "\n")
                    + (frontAppraisal == null ? "" : "Front control appraisal: " + frontAppraisal.toString() + "\n")
                    + (face.isEmpty() ? "" : "Current local interface state: " + face + "\n")
                    + (interfaceAppraisal == null ? "" : "Interface control appraisal: " + interfaceAppraisal.toString() + "\n")
                    + "The outer seven specialist names are dispositions, not missing faculties. Inside every top-level core the same internal Fano faculties are available: d1 truth, d2 valence, d3 significance, d4 pattern, d5 understanding, d6 possibility and d7 continuity. Evidence can imagine and remember; Novelty can test evidence; Front and Interface can inspect risk and grounding.\n"
                    + "Answer the user's question from this device activity. Distinguish deterministic local-core processing from server/model activity.\n"
                    + "[END DEVICE JANUS CONTEXT]";
            return userMessage + context + recursiveContext;
        } catch (Exception ignored) {
            return userMessage;
        }
    }

    static boolean asksAboutBackgroundActivity(String text) {
        String s = text == null ? "" : text.toLowerCase(Locale.ROOT).trim();
        boolean thought = s.contains("think") || s.contains("thinking") || s.contains("thought")
                || s.contains("doing") || s.contains("working on") || s.contains("processing")
                || s.contains("up to") || s.contains("considering") || s.contains("pondering");
        if (!thought) return false;

        boolean away = s.contains("while i was away") || s.contains("while i was gone")
                || s.contains("since i left") || s.contains("since we spoke") || s.contains("since we talked")
                || s.contains("between messages") || s.contains("between chats") || s.contains("between conversations")
                || s.contains("in the background") || s.contains("background") || s.contains("while idle");
        if (away) return true;

        return s.matches(".*\\b(what|anything|any)\\b.*\\b(thinking|thoughts?)\\b.*")
                && !s.matches(".*\\bthink about\\b.+");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        s = s.trim();
        return s.length() <= max ? s : s.substring(0, max) + "…";
    }
}
