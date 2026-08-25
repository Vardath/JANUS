package com.vardath.janus;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.reflect.Field;
import java.util.Iterator;

/** Narrow access to the one Application-owned recursive engine instance. */
final class JanusRecursiveCoreBridge {
    private JanusRecursiveCoreBridge() {}

    static JSONObject foreground(JanusLocalCoreRuntime runtime, String message) {
        try {
            JanusRecursiveCoreEngine engine = existing();
            if (engine == null) return new JSONObject();
            return compact(engine.foreground(message));
        } catch (Exception ignored) {
            return new JSONObject();
        }
    }

    static void applyAiCounsel(JSONObject counsel) {
        try {
            JanusRecursiveCoreEngine engine = existing();
            if (engine != null) engine.applyAiCounsel(counsel);
        } catch (Exception ignored) {}
    }

    static void sense(String modality, String source, String content) {
        try {
            JanusRecursiveCoreEngine engine = existing();
            if (engine != null) engine.sense(modality, source, content);
        } catch (Exception ignored) {}
    }

    private static JanusRecursiveCoreEngine existing() throws Exception {
        Field f = JanusRecursiveCoreEngine.class.getDeclaredField("instance");
        f.setAccessible(true);
        Object value = f.get(null);
        return value instanceof JanusRecursiveCoreEngine ? (JanusRecursiveCoreEngine) value : null;
    }

    private static JSONObject compact(JSONObject full) throws Exception {
        JSONObject root = new JSONObject();
        root.put("recursive_core_engine", true);
        root.put("core_count", 11);
        root.put("internal_fano_positions_per_core", 7);
        JSONObject out = new JSONObject();
        JSONObject cores = full.optJSONObject("cores");
        if (cores != null) {
            Iterator<String> names = cores.keys();
            while (names.hasNext()) {
                String name = names.next();
                JSONObject in = cores.optJSONObject(name); if (in == null) continue;
                JSONObject x = new JSONObject();
                x.put("recursive_janus", true);
                x.put("ai_capable", true);
                x.put("outer_disposition", in.optString("outer_disposition", ""));
                x.put("active_direction", in.optInt("active_direction", 0));
                x.put("active_faculty", in.optString("active_faculty", "reference"));
                JSONArray weights = in.optJSONArray("weights"); if (weights != null) x.put("weights", weights);
                x.put("cycles", in.optLong("cycles", 0));
                x.put("revision_count", in.optLong("revision_count", 0));
                x.put("peer_turn_count", in.optLong("peer_turn_count", 0));
                x.put("conclusion", clip(in.optString("conclusion", ""), 420));
                x.put("ai_last", clip(in.optString("ai_last", ""), 280));
                out.put(name, x);
            }
        }
        root.put("cores", out);
        return root;
    }

    private static String clip(String value, int max) {
        String x = value == null ? "" : value.replace('\n',' ').replace('\r',' ').trim();
        return x.length() <= max ? x : x.substring(0,max) + "…";
    }
}
