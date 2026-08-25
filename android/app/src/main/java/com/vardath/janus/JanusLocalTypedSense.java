package com.vardath.janus;

import android.content.Context;

import java.lang.reflect.Method;

/**
 * Narrow adapter for injecting capability results into the existing local 1|3|7 runtime.
 *
 * The authoritative runtime predates the generic typed-sense entry point and keeps its
 * routing helpers private. Until that class is safely refactored, this adapter invokes
 * only the existing broadcast/service/persist methods on the same runtime instance.
 * It does not create a second society, does not call any model/API, and fails closed if
 * the runtime contract changes. Authentication/credential traffic must never call here.
 */
final class JanusLocalTypedSense {
    private JanusLocalTypedSense() {}

    static boolean ingest(Context context, String modality, String source, String content) {
        String type = clean(modality, 32);
        String origin = clean(source, 96);
        String detail = clean(content, 1800);
        if (type.isEmpty() || detail.isEmpty()) return false;
        try {
            Context app = context.getApplicationContext();
            JanusLocalCoreRuntime runtime = JanusLocalCoreRuntime.get(app);
            Method broadcast = JanusLocalCoreRuntime.class.getDeclaredMethod(
                    "broadcastSense", String.class, String.class, String.class);
            Method service = JanusLocalCoreRuntime.class.getDeclaredMethod("serviceBurst", boolean.class);
            Method persist = JanusLocalCoreRuntime.class.getDeclaredMethod("persist");
            broadcast.setAccessible(true);
            service.setAccessible(true);
            persist.setAccessible(true);
            synchronized (runtime) {
                broadcast.invoke(runtime, detail, origin.isEmpty() ? "capability" : origin, type);
                service.invoke(runtime, true);
                persist.invoke(runtime);
            }
            // The same sense also reaches the complete JANUS/Fano processor living
            // inside every top-level local core. This nested pass is deterministic.
            JanusRecursiveCoreEngine.get(app).sense(type, origin.isEmpty() ? "capability" : origin, detail);
            return true;
        } catch (Exception ignored) {
            // Fail closed: never relabel a capability event as user text or peer state.
            return false;
        }
    }

    private static String clean(String value, int max) {
        String x = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        return x.length() <= max ? x : x.substring(0, max) + "…";
    }
}
