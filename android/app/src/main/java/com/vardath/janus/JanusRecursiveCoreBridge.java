package com.vardath.janus;

import org.json.JSONObject;

import java.lang.reflect.Field;

/** Narrow access to the one Application-owned recursive engine instance. */
final class JanusRecursiveCoreBridge {
    private JanusRecursiveCoreBridge() {}

    static JSONObject foreground(JanusLocalCoreRuntime runtime, String message) {
        try {
            Field f = JanusRecursiveCoreEngine.class.getDeclaredField("instance");
            f.setAccessible(true);
            Object value = f.get(null);
            if (!(value instanceof JanusRecursiveCoreEngine)) return new JSONObject();
            return ((JanusRecursiveCoreEngine) value).foreground(message);
        } catch (Exception ignored) {
            return new JSONObject();
        }
    }

    static void applyAiCounsel(JSONObject counsel) {
        try {
            Field f = JanusRecursiveCoreEngine.class.getDeclaredField("instance");
            f.setAccessible(true);
            Object value = f.get(null);
            if (value instanceof JanusRecursiveCoreEngine) ((JanusRecursiveCoreEngine) value).applyAiCounsel(counsel);
        } catch (Exception ignored) {}
    }
}
