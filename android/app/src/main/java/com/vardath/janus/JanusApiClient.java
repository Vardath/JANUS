package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Shared native network client for the rebuilt Android product. */
public final class JanusApiClient {
    public static final String SERVER = "https://janus-global-core.onrender.com";
    public static final String PREFS = "janus";
    public static final String TOKEN = "access_token";
    public static final String PROFILE = "profile_id";
    private final Context appContext;
    private final SharedPreferences prefs;
    private volatile int lastResponseCode = 200;
    private volatile String lastRequestPath = "";

    public JanusApiClient(Context context) {
        appContext = context.getApplicationContext();
        prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
    public String token() { return prefs.getString(TOKEN, ""); }
    public String profile() { return prefs.getString(PROFILE, ""); }
    public void saveSession(String token, String profile) {
        JanusAccountIsolation.beforeSaveSession(appContext, profile);
        prefs.edit().putString(TOKEN, token == null ? "" : token).putString(PROFILE, profile == null ? "" : profile).apply();
    }
    public void clearSession() {
        // Startup validation must not turn a transient network/Render wake failure into
        // a destructive logout. Explicit logout/delete requests still clear locally.
        if ("/auth/me".equals(lastRequestPath) && isTransient(lastResponseCode)) return;
        JanusAccountIsolation.clearForSignOut(appContext);
    }
    public Response get(String path, boolean auth) { return request("GET", path, null, auth, true); }

    public Response post(String path, String body, boolean auth) {
        String effectivePath = auth ? JanusRoutePolicy.sanitizeAuthenticatedPath(path) : path;
        if (auth && "/desktop/chat".equals(effectivePath)) return JanusChatController.sendOnce(this, body).response;
        return request("POST", path, body, auth, true);
    }

    public Response delete(String path, String body, boolean auth) { return request("DELETE", path, body, auth, true); }

    /** Raw Chat transport. Local thought context is injected here so UI/history retain only the user's visible message. */
    Response postRaw(String path, String body, boolean auth) {
        String effectivePath = auth ? JanusRoutePolicy.sanitizeAuthenticatedPath(path) : path;
        String prepared = body;
        if (auth && "/desktop/chat".equals(effectivePath)) prepared = augmentChatBody(body);
        return request("POST", path, prepared, auth, false);
    }

    private String augmentChatBody(String body) {
        if (body == null || body.isBlank()) return body;
        try {
            JSONObject j = new JSONObject(body);
            String message = j.optString("message", "");
            if (message.isBlank()) return body;
            // Preserve the exact visible message separately. The server uses this for
            // complete owner-controlled Supervisor transcripts and never stores the
            // hidden local-core context as if the user typed it.
            j.put("user_visible_message", message);
            String augmented = JanusThoughtBridge.augment(JanusLocalCoreRuntime.get(appContext), message);
            if (!augmented.equals(message)) j.put("message", augmented);
            return j.toString();
        } catch (Exception ignored) {
            return body;
        }
    }

    public Response request(String method, String path, String body, boolean auth) { return request(method, path, body, auth, true); }

    private Response request(String method, String path, String body, boolean auth, boolean captureChat) {
        HttpURLConnection c = null;
        String effectivePath = auth ? JanusRoutePolicy.sanitizeAuthenticatedPath(path) : path;
        lastRequestPath = effectivePath == null ? "" : effectivePath;
        try {
            c = (HttpURLConnection) new URL(SERVER + effectivePath).openConnection();
            c.setRequestMethod(method); c.setConnectTimeout(20000); c.setReadTimeout(120000);
            c.setRequestProperty("Accept", "application/json"); c.setRequestProperty("Connection", "close");
            String token = token();
            if (auth && token != null && !token.trim().isEmpty()) c.setRequestProperty("Authorization", "Bearer " + token.trim());
            if (body != null) {
                c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = c.getOutputStream()) { out.write(body.getBytes(StandardCharsets.UTF_8)); }
            }
            int code = c.getResponseCode();
            lastResponseCode = code;
            InputStream in = code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream();
            String responseBody = read(in);
            if (code >= 200 && code < 300 && auth) senseCapability(method, effectivePath, body, responseBody);
            if (captureChat && code >= 200 && code < 300 && "POST".equals(method) && "/desktop/chat".equals(effectivePath)) {
                JanusChatResponseRegistry.capture(responseBody);
            }
            return new Response(code, responseBody, null);
        } catch (Exception e) {
            lastResponseCode = 0;
            return new Response(0, "", e.getClass().getSimpleName() + ": " + String.valueOf(e.getMessage()));
        }
        finally { if (c != null) c.disconnect(); }
    }

    private static boolean isTransient(int code) {
        return code == 0 || code == 408 || code == 425 || code == 429 || code == 502 || code == 503 || code == 504 || code >= 500;
    }

    /**
     * Convert successful, non-auth capability results into bounded local typed senses.
     * Raw file bytes/base64, session tokens, passwords and authentication payloads are
     * never forwarded into the local sensory runtime.
     */
    private void senseCapability(String method, String path, String requestBody, String responseBody) {
        if (path == null || path.startsWith("/auth/") || path.startsWith("/maintenance/") || "/core-sync/exchange".equals(path)) return;
        try {
            if ("POST".equals(method) && "/files/upload".equals(path)) {
                JSONObject req = requestBody == null ? new JSONObject() : new JSONObject(requestBody);
                JSONObject root = new JSONObject(responseBody);
                JSONObject file = root.optJSONObject("file");
                String name = req.optString("filename", file == null ? "attachment" : file.optString("filename", "attachment"));
                String mime = req.optString("mime_type", file == null ? "application/octet-stream" : file.optString("mime_type", "application/octet-stream"));
                long size = file == null ? 0L : file.optLong("size_bytes", 0L);
                JanusLocalTypedSense.ingest(appContext, "file", "upload", "Attached file ready: " + name + " (" + mime + ", " + size + " bytes). Content bytes are not copied into local telemetry.");
                return;
            }
            if ("POST".equals(method) && "/images/generate".equals(path)) {
                JSONObject root = new JSONObject(responseBody);
                JSONObject image = root.optJSONObject("generated_image");
                if (image == null) image = root.optJSONObject("image");
                String id = image == null ? "" : image.optString("id", image.optString("file_id", ""));
                JanusLocalTypedSense.ingest(appContext, "image", "generated_visual", "Generated image is available" + (id.isBlank() ? "." : " as file " + id + "."));
                return;
            }
            if ("GET".equals(method) && path.startsWith("/images/") && path.endsWith("/inline")) {
                JSONObject root = new JSONObject(responseBody);
                JanusLocalTypedSense.ingest(appContext, "image", "display", "Image rendered locally: file " + root.optString("file_id", "unknown") + " (" + root.optString("mime_type", "image") + "). Raw image bytes are not copied into sensory telemetry.");
                return;
            }
            if ("POST".equals(method) && "/desktop/chat".equals(path)) {
                JSONObject root = new JSONObject(responseBody);
                JSONArray sources = root.optJSONArray("sources");
                if (sources != null && sources.length() > 0) {
                    StringBuilder b = new StringBuilder("Live research sources returned: ");
                    for (int i = 0; i < Math.min(8, sources.length()); i++) {
                        JSONObject s = sources.optJSONObject(i); if (s == null) continue;
                        if (b.length() > 32) b.append(" | ");
                        b.append(s.optString("title", "source")).append(' ').append(s.optString("url", ""));
                    }
                    JanusLocalTypedSense.ingest(appContext, "web", "chat_research", b.toString());
                } else if (root.optBoolean("research_grounding", false)) {
                    JanusLocalTypedSense.ingest(appContext, "web", "chat_research", "The current answer used external research grounding; detailed source content remains server-side.");
                }
                JSONObject generated = root.optJSONObject("generated_image");
                if (generated != null) {
                    JanusLocalTypedSense.ingest(appContext, "image", "chat_generated_visual", "JANUS attached a generated visual artifact to the current response.");
                }
                return;
            }
            if ("POST".equals(method) && "/artifacts".equals(path)) {
                JSONObject root = new JSONObject(responseBody);
                JSONObject artifact = root.optJSONObject("artifact");
                if (artifact != null) JanusLocalTypedSense.ingest(appContext, "action_result", "artifact", "Artifact created: " + artifact.optString("title", "JANUS artifact") + " (" + artifact.optString("kind", "artifact") + ").");
                return;
            }
            if ("POST".equals(method) && (path.startsWith("/claims") || path.startsWith("/desktop/continuity"))) {
                JanusLocalTypedSense.ingest(appContext, "action_result", "workspace", "JANUS workspace state changed successfully at " + path + ".");
            }
        } catch (Exception ignored) {
            // Sensing is supplementary and must never break the underlying capability.
        }
    }

    public byte[] download(String path, boolean auth) throws Exception {
        HttpURLConnection c = null;
        try {
            String effectivePath = auth ? JanusRoutePolicy.sanitizeAuthenticatedPath(path) : path;
            c = (HttpURLConnection) new URL(SERVER + effectivePath).openConnection(); c.setRequestMethod("GET"); c.setConnectTimeout(20000); c.setReadTimeout(120000);
            c.setRequestProperty("Accept", "*/*"); c.setRequestProperty("Connection", "close");
            String token = token(); if (auth && token != null && !token.trim().isEmpty()) c.setRequestProperty("Authorization", "Bearer " + token.trim());
            int code = c.getResponseCode();
            if (code < 200 || code >= 300) { String responseBody = read(c.getErrorStream()); throw new IllegalStateException("HTTP " + code + (responseBody.isEmpty() ? "" : " · " + responseBody)); }
            try (InputStream in = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[32768]; int n; while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
                byte[] result = out.toByteArray();
                if (auth && effectivePath.startsWith("/files/")) JanusLocalTypedSense.ingest(appContext, "file", "download", "Downloaded an authenticated JANUS file artifact (" + result.length + " bytes). Raw bytes are not copied into local telemetry.");
                return result;
            }
        } finally { if (c != null) c.disconnect(); }
    }

    private static String read(InputStream in) throws Exception {
        if (in == null) return ""; StringBuilder b = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) { String line; while ((line = r.readLine()) != null) { if (b.length() < 65536) b.append(line).append('\n'); } }
        return b.toString().trim();
    }

    public static final class Response {
        public final int code; public final String body; public final String error;
        public Response(int code, String body, String error) { this.code = code; this.body = body == null ? "" : body; this.error = error; }
        public boolean ok() { return code >= 200 && code < 300; }
        public boolean retryable() { return code == 0 || code == 408 || code == 425 || code == 429 || code == 502 || code == 503 || code == 504; }
    }
}
