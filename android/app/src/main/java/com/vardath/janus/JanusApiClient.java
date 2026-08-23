package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

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

    private final SharedPreferences prefs;

    public JanusApiClient(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public String token() { return prefs.getString(TOKEN, ""); }
    public String profile() { return prefs.getString(PROFILE, ""); }

    public void saveSession(String token, String profile) {
        prefs.edit().putString(TOKEN, token == null ? "" : token)
                .putString(PROFILE, profile == null ? "" : profile).apply();
    }

    public void clearSession() {
        prefs.edit().remove(TOKEN).remove(PROFILE).remove("last_notified_message").apply();
    }

    public Response get(String path, boolean auth) { return request("GET", path, null, auth); }
    public Response post(String path, String body, boolean auth) { return request("POST", path, body, auth); }
    public Response delete(String path, String body, boolean auth) { return request("DELETE", path, body, auth); }

    public Response request(String method, String path, String body, boolean auth) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(SERVER + path).openConnection();
            c.setRequestMethod(method);
            c.setConnectTimeout(20000);
            c.setReadTimeout(120000);
            c.setRequestProperty("Accept", "application/json");
            c.setRequestProperty("Connection", "close");
            String token = token();
            if (auth && token != null && !token.trim().isEmpty()) {
                c.setRequestProperty("Authorization", "Bearer " + token.trim());
            }
            if (body != null) {
                c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = c.getOutputStream()) {
                    out.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = c.getResponseCode();
            InputStream in = code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream();
            return new Response(code, read(in), null);
        } catch (Exception e) {
            return new Response(0, "", e.getClass().getSimpleName() + ": " + String.valueOf(e.getMessage()));
        } finally {
            if (c != null) c.disconnect();
        }
    }

    public byte[] download(String path, boolean auth) throws Exception {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(SERVER + path).openConnection();
            c.setRequestMethod("GET");
            c.setConnectTimeout(20000);
            c.setReadTimeout(120000);
            c.setRequestProperty("Accept", "*/*");
            c.setRequestProperty("Connection", "close");
            String token = token();
            if (auth && token != null && !token.trim().isEmpty()) {
                c.setRequestProperty("Authorization", "Bearer " + token.trim());
            }
            int code = c.getResponseCode();
            if (code < 200 || code >= 300) {
                String body = read(c.getErrorStream());
                throw new IllegalStateException("HTTP " + code + (body.isEmpty() ? "" : " · " + body));
            }
            try (InputStream in = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[32768];
                int n;
                while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
                return out.toByteArray();
            }
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String read(InputStream in) throws Exception {
        if (in == null) return "";
        StringBuilder b = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                if (b.length() < 65536) b.append(line).append('\n');
            }
        }
        return b.toString().trim();
    }

    public static final class Response {
        public final int code;
        public final String body;
        public final String error;
        public Response(int code, String body, String error) {
            this.code = code;
            this.body = body == null ? "" : body;
            this.error = error;
        }
        public boolean ok() { return code >= 200 && code < 300; }
        public boolean retryable() { return code == 0 || code == 408 || code == 425 || code == 429 || code == 502 || code == 503 || code == 504; }
    }
}
