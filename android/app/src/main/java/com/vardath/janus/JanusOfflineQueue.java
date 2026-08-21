package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/**
 * Persistent on-device outbound chat queue.
 *
 * User chat turns get a client_message_id before the first network attempt. If
 * Android receives no HTTP response, the exact turn is retained in app-private
 * storage and retried later. Server-side idempotency makes retries safe when a
 * response was lost after the server had already accepted the turn.
 */
public final class JanusOfflineQueue {
    private static final String PREFS = "janus";
    private static final String OUTBOX = "offline_chat_outbox_v1";
    private static final String REPLIES = "offline_chat_replies_v1";
    private static final int MAX_OUTBOX = 100;
    private static final int MAX_REPLIES = 50;

    private JanusOfflineQueue() {}

    public static String prepareChatBody(String rawJson) {
        try {
            JSONObject body = new JSONObject(rawJson == null ? "{}" : rawJson);
            if (body.optString("client_message_id", "").trim().isEmpty()) {
                body.put("client_message_id", UUID.randomUUID().toString());
            }
            return body.toString();
        } catch (Exception e) {
            try {
                return new JSONObject().put("message", rawJson == null ? "" : rawJson)
                        .put("client_message_id", UUID.randomUUID().toString()).toString();
            } catch (Exception ignored) {
                return rawJson == null ? "{}" : rawJson;
            }
        }
    }

    public static synchronized int enqueue(Context context, String preparedJson) {
        try {
            JSONObject body = new JSONObject(prepareChatBody(preparedJson));
            String id = body.optString("client_message_id", "");
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            JSONArray old = new JSONArray(prefs.getString(OUTBOX, "[]"));
            JSONArray next = new JSONArray();
            boolean found = false;
            for (int i = Math.max(0, old.length() - MAX_OUTBOX + 1); i < old.length(); i++) {
                JSONObject item = old.optJSONObject(i);
                if (item == null) continue;
                if (id.equals(item.optString("id"))) found = true;
                next.put(item);
            }
            if (!found) {
                JSONObject item = new JSONObject();
                item.put("id", id);
                item.put("body", body);
                item.put("created_at", System.currentTimeMillis());
                item.put("attempts", 0);
                next.put(item);
            }
            prefs.edit().putString(OUTBOX, next.toString()).apply();
            return next.length();
        } catch (Exception e) {
            return pendingCount(context);
        }
    }

    public static synchronized int pendingCount(Context context) {
        try {
            return new JSONArray(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .getString(OUTBOX, "[]")).length();
        } catch (Exception e) {
            return 0;
        }
    }

    public static synchronized int flush(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String token = prefs.getString("access_token", "");
        if (token == null || token.trim().isEmpty()) return 0;
        try {
            JSONArray old = new JSONArray(prefs.getString(OUTBOX, "[]"));
            JSONArray keep = new JSONArray();
            int delivered = 0;
            boolean stopForAuth = false;
            for (int i = 0; i < old.length(); i++) {
                JSONObject item = old.optJSONObject(i);
                if (item == null) continue;
                if (stopForAuth) { keep.put(item); continue; }
                JSONObject body = item.optJSONObject("body");
                if (body == null) { continue; }
                int attempts = item.optInt("attempts", 0) + 1;
                item.put("attempts", attempts);
                HttpURLConnection c = null;
                try {
                    c = (HttpURLConnection) new URL(MainActivity.SERVER + "/desktop/chat").openConnection();
                    c.setRequestMethod("POST");
                    c.setDoOutput(true);
                    c.setConnectTimeout(20000);
                    c.setReadTimeout(120000);
                    c.setRequestProperty("Accept", "application/json");
                    c.setRequestProperty("Content-Type", "application/json");
                    c.setRequestProperty("Authorization", "Bearer " + token.trim());
                    try (OutputStream os = c.getOutputStream()) {
                        os.write(body.toString().getBytes(StandardCharsets.UTF_8));
                    }
                    int code = c.getResponseCode();
                    String response = readBody(c, code);
                    if (code >= 200 && code < 300) {
                        delivered++;
                        rememberReply(prefs, item.optString("id"), response);
                    } else if (code == 401 || code == 403) {
                        keep.put(item);
                        stopForAuth = true;
                    } else if (code == 409 || code == 425 || code == 429 || code >= 500) {
                        keep.put(item);
                    } else {
                        rememberReply(prefs, item.optString("id"), new JSONObject()
                                .put("reply", "A queued JANUS message could not be delivered (HTTP " + code + "). It has been removed from the retry queue.")
                                .put("mode", "queue_delivery_error").toString());
                    }
                } catch (Exception e) {
                    keep.put(item);
                } finally {
                    if (c != null) c.disconnect();
                }
            }
            prefs.edit().putString(OUTBOX, keep.toString()).apply();
            return delivered;
        } catch (Exception e) {
            return 0;
        }
    }

    private static String readBody(HttpURLConnection c, int code) throws Exception {
        if (code >= 400 && c.getErrorStream() == null) return "";
        BufferedReader r = new BufferedReader(new InputStreamReader(
                code >= 400 ? c.getErrorStream() : c.getInputStream(), StandardCharsets.UTF_8));
        StringBuilder b = new StringBuilder();
        String line;
        while ((line = r.readLine()) != null && b.length() < 16384) b.append(line);
        r.close();
        return b.toString();
    }

    private static synchronized void rememberReply(SharedPreferences prefs, String id, String rawResponse) {
        try {
            String reply = rawResponse;
            try {
                JSONObject parsed = new JSONObject(rawResponse == null ? "{}" : rawResponse);
                reply = parsed.optString("reply", parsed.optString("detail", rawResponse));
            } catch (Exception ignored) {}
            if (reply == null || reply.trim().isEmpty()) return;
            JSONArray old = new JSONArray(prefs.getString(REPLIES, "[]"));
            JSONArray next = new JSONArray();
            for (int i = Math.max(0, old.length() - MAX_REPLIES + 1); i < old.length(); i++) {
                JSONObject x = old.optJSONObject(i);
                if (x != null) next.put(x);
            }
            next.put(new JSONObject().put("id", id).put("reply", reply).put("delivered_at", System.currentTimeMillis()));
            prefs.edit().putString(REPLIES, next.toString()).apply();
        } catch (Exception ignored) {}
    }

    public static synchronized String drainReplies(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String raw = prefs.getString(REPLIES, "[]");
        prefs.edit().putString(REPLIES, "[]").apply();
        return raw == null ? "[]" : raw;
    }
}
