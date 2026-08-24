package com.vardath.janus;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.PrintWriter;
import java.io.StringWriter;

/**
 * Externalizable client diagnostics. Unexpected Android crashes are persisted
 * locally and submitted after the next authenticated launch. This records a
 * request only; it cannot approve maintenance or alter/deploy JANUS.
 */
public final class JanusClientDiagnostics {
    private static final String PREFS = "janus_client_diagnostics";
    private static final String PENDING = "pending_crash_report";
    private static volatile boolean installed;
    private static volatile boolean flushing;
    private JanusClientDiagnostics() {}

    public static synchronized void install(Application app) {
        if (installed || app == null) return;
        installed = true;
        Thread.UncaughtExceptionHandler previous = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            try {
                StringWriter sw = new StringWriter();
                error.printStackTrace(new PrintWriter(sw));
                String stack = sw.toString();
                if (stack.length() > 7000) stack = stack.substring(0, 7000);
                JSONObject report = new JSONObject();
                report.put("capability", "android_client_stability");
                report.put("title", "JANUS Android encountered an unexpected crash");
                report.put("detail", error.getClass().getSimpleName() + ": " + String.valueOf(error.getMessage()));
                report.put("evidence", "Thread: " + (thread == null ? "unknown" : thread.getName()) + "\n" + stack);
                report.put("severity", "high");
                app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(PENDING, report.toString()).commit();
            } catch (Exception ignored) {}
            if (previous != null) previous.uncaughtException(thread, error);
        });
    }

    public static void flushPending(Activity activity) {
        if (activity == null || flushing) return;
        SharedPreferences p = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String body = p.getString(PENDING, "");
        if (body == null || body.isBlank()) return;
        JanusApiClient api = new JanusApiClient(activity);
        if (api.token() == null || api.token().isBlank()) return;
        flushing = true;
        new Thread(() -> {
            try {
                JanusApiClient.Response r = api.post("/maintenance/diagnostics/report", body, true);
                if (r.ok()) p.edit().remove(PENDING).apply();
            } catch (Exception ignored) {
            } finally {
                flushing = false;
            }
        }, "janus-diagnostics-flush").start();
    }
}
