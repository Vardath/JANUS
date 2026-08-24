package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.UUID;
import java.util.concurrent.TimeUnit;

/** Persistent on-device outbound Chat queue with retry-safe idempotency and structured presentation replay. */
public final class JanusOfflineQueue {
    private static final String PREFS = "janus";
    private static final String OUTBOX = "offline_chat_outbox_v1";
    private static final String REPLIES = "offline_chat_replies_v2";
    private static final String LEGACY_REPLIES = "offline_chat_replies_v1";
    private static final int MAX_OUTBOX = 100;
    private static final int MAX_REPLIES = 50;
    private static final long DUPLICATE_WINDOW_MS = 120_000L;

    private JanusOfflineQueue() {}

    public static String prepareChatBody(String rawJson) {
        try {
            JSONObject body = new JSONObject(rawJson == null ? "{}" : rawJson);
            if (body.optString("client_message_id", "").trim().isEmpty()) body.put("client_message_id", UUID.randomUUID().toString());
            return body.toString();
        } catch (Exception e) {
            try {
                return new JSONObject().put("message", rawJson == null ? "" : rawJson)
                        .put("client_message_id", UUID.randomUUID().toString()).toString();
            } catch (Exception ignored) { return rawJson == null ? "{}" : rawJson; }
        }
    }

    private static String normalizedMessage(JSONObject body) {
        String m = body.optString("message", body.optString("text", ""));
        return m == null ? "" : m.trim().replaceAll("\\s+", " ");
    }

    private static void scheduleFastRetries(Context context) {
        long[] delays = new long[]{8L, 25L, 60L};
        WorkManager manager = WorkManager.getInstance(context.getApplicationContext());
        for (long delay : delays) {
            OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(JanusQueueRetryWorker.class)
                    .setInitialDelay(delay, TimeUnit.SECONDS).build();
            manager.enqueueUniqueWork("janus-offline-chat-retry-" + delay, ExistingWorkPolicy.REPLACE, request);
        }
    }

    public static synchronized int enqueue(Context context, String preparedJson) {
        try {
            JSONObject body = new JSONObject(prepareChatBody(preparedJson));
            String id = body.optString("client_message_id", "");
            String message = normalizedMessage(body);
            long now = System.currentTimeMillis();
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            JSONArray old = new JSONArray(prefs.getString(OUTBOX, "[]"));
            JSONArray next = new JSONArray();
            boolean found = false;
            for (int i = Math.max(0, old.length() - MAX_OUTBOX + 1); i < old.length(); i++) {
                JSONObject item = old.optJSONObject(i);
                if (item == null) continue;
                JSONObject oldBody = item.optJSONObject("body");
                boolean sameId = id.equals(item.optString("id"));
                boolean recentDuplicate = oldBody != null && !message.isEmpty()
                        && message.equals(normalizedMessage(oldBody))
                        && now - item.optLong("created_at", 0L) <= DUPLICATE_WINDOW_MS;
                if (sameId || recentDuplicate) found = true;
                next.put(item);
            }
            if (!found) {
                JSONObject item = new JSONObject();
                item.put("id", id); item.put("body", body); item.put("created_at", now); item.put("attempts", 0);
                next.put(item);
            }
            prefs.edit().putString(OUTBOX, next.toString()).apply();
            scheduleFastRetries(context);
            return next.length();
        } catch (Exception e) { return pendingCount(context); }
    }

    public static synchronized int pendingCount(Context context) {
        try { return new JSONArray(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(OUTBOX, "[]")).length(); }
        catch (Exception e) { return 0; }
    }

    public static synchronized int flush(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String token = prefs.getString("access_token", "");
        if (token == null || token.trim().isEmpty()) return 0;
        JanusApiClient api = new JanusApiClient(context);
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
                if (body == null) continue;
                item.put("attempts", item.optInt("attempts", 0) + 1);

                JanusChatController.Result result = JanusChatController.sendOnce(api, body.toString());
                if (result.ok()) {
                    delivered++;
                    rememberReply(context, prefs, item.optString("id"), result.response.body);
                } else if (result.authExpired) {
                    keep.put(item); stopForAuth = true;
                } else if (result.retryable || result.response.code == 409) {
                    keep.put(item);
                } else {
                    rememberReply(context, prefs, item.optString("id"), new JSONObject()
                            .put("reply", "A queued JANUS message could not be delivered (HTTP " + result.response.code + "). It has been removed from the retry queue.")
                            .put("mode", "queue_delivery_error").toString());
                }
            }
            prefs.edit().putString(OUTBOX, keep.toString()).apply();
            return delivered;
        } catch (Exception e) { return 0; }
    }

    private static synchronized void rememberReply(Context context, SharedPreferences prefs, String id, String rawResponse) {
        try {
            JanusChatPresentation presentation = JanusChatPresentation.fromResponse(new JSONObject(rawResponse == null ? "{}" : rawResponse), rawResponse);
            if (presentation.reply == null || presentation.reply.trim().isEmpty()) return;
            JanusChatResponseRegistry.capture(context, rawResponse);
            JSONArray old = new JSONArray(prefs.getString(REPLIES, "[]"));
            JSONArray next = new JSONArray();
            for (int i = Math.max(0, old.length() - MAX_REPLIES + 1); i < old.length(); i++) {
                JSONObject x = old.optJSONObject(i); if (x != null) next.put(x);
            }
            next.put(new JSONObject()
                    .put("id", id)
                    .put("reply", presentation.reply)
                    .put("presentation", presentation.toJson())
                    .put("delivered_at", System.currentTimeMillis()));
            prefs.edit().putString(REPLIES, next.toString()).apply();
        } catch (Exception ignored) {}
    }

    public static synchronized String drainReplies(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONArray structured = new JSONArray(prefs.getString(REPLIES, "[]"));
            JSONArray legacy = new JSONArray(prefs.getString(LEGACY_REPLIES, "[]"));
            for (int i = 0; i < legacy.length(); i++) {
                JSONObject old = legacy.optJSONObject(i);
                if (old == null) continue;
                String reply = old.optString("reply", "").trim();
                if (reply.isEmpty()) continue;
                structured.put(new JSONObject().put("id", old.optString("id", ""))
                        .put("reply", reply).put("delivered_at", old.optLong("delivered_at", System.currentTimeMillis())));
            }
            prefs.edit().putString(REPLIES, "[]").putString(LEGACY_REPLIES, "[]").apply();
            return structured.toString();
        } catch (Exception e) {
            prefs.edit().putString(REPLIES, "[]").putString(LEGACY_REPLIES, "[]").apply();
            return "[]";
        }
    }
}
