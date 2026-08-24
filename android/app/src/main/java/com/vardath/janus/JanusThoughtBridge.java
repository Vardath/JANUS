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
                    + "These are persisted deterministic local processing events with zero model/API calls. They are real app-side JANUS processing between messages. Describe what the cores actually processed when asked, rather than claiming that no background thinking/processing occurred. Do not describe this as phenomenal consciousness or an uninterrupted private stream of consciousness.\n"
                    + (recent.length() == 0 ? "Recent externalizable local activity: none retained.\n" : "Recent externalizable local activity:\n" + recent)
                    + (fano.length() == 0 ? "" : "Current Fano attention orientations used by the local cores:\n" + fano)
                    + (front.isEmpty() ? "" : "Current local Front appraisal/intention state: " + front + "\n")
                    + (frontAppraisal == null ? "" : "Front control appraisal: " + frontAppraisal.toString() + "\n")
                    + (face.isEmpty() ? "" : "Current local interface state: " + face + "\n")
                    + (interfaceAppraisal == null ? "" : "Interface control appraisal: " + interfaceAppraisal.toString() + "\n")
                    + "The seven Fano directions are computational attention lenses and home roles: d1 Evidence/truth-grounding; d2 Safety/valence-welfare; d3 Counterpoint/significance-conflict; d4 Context/pattern-relationship; d5 Logic/understanding-model; d6 Novelty/possibility-imagination; d7 Memory/continuity-experience. Both hemispheres receive all seven. Left emphasizes logic, constraint and explicit causal consistency; Right emphasizes imagination, association, alternatives and gestalt. Front integrates them into bounded appraisal/intention, and Interface chooses expression/action. These are control semantics, not evidence that Fano mathematics proves any external claim.\n"
                    + "Answer the user's question from this device activity. If there was activity, summarize its actual topics/results and, when useful, mention which attention orientations or appraisal dimensions dominated. Distinguish deterministic local-core processing from server/model activity.\n"
                    + "[END DEVICE JANUS CONTEXT]";
            return userMessage + context;
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
