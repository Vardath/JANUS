package com.vardath.janus;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class JanusMessageWorker extends Worker {
    private static final String CHANNEL = "janus_messages";

    public JanusMessageWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull @Override public Result doWork() {
        Context ctx = getApplicationContext();
        String token = ctx.getSharedPreferences("janus", Context.MODE_PRIVATE).getString("access_token", "");
        if (token == null || token.isEmpty()) return Result.success();
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(MainActivity.SERVER + "/desktop/messages?limit=20").openConnection();
            c.setRequestMethod("GET");
            c.setConnectTimeout(20000);
            c.setReadTimeout(30000);
            c.setRequestProperty("Accept", "application/json");
            c.setRequestProperty("Authorization", "Bearer " + token);
            int code = c.getResponseCode();
            if (code == 401 || code == 403) return Result.success();
            if (code >= 400) return Result.retry();
            BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream(), StandardCharsets.UTF_8));
            StringBuilder b = new StringBuilder(); String line;
            while ((line = r.readLine()) != null) b.append(line);
            r.close();
            JSONObject root = new JSONObject(b.toString());
            JSONArray items = root.optJSONArray("items");
            if (items == null) return Result.success();
            long newest = ctx.getSharedPreferences("janus", Context.MODE_PRIVATE).getLong("last_notified_message", 0);
            JSONObject candidate = null; long candidateId = newest;
            for (int i = 0; i < items.length(); i++) {
                JSONObject x = items.optJSONObject(i);
                if (x == null || !"unread".equals(x.optString("state"))) continue;
                long id = x.optLong("id", 0);
                if (id > candidateId) { candidate = x; candidateId = id; }
            }
            if (candidate != null) {
                notifyMessage(candidate, candidateId);
                ctx.getSharedPreferences("janus", Context.MODE_PRIVATE).edit().putLong("last_notified_message", candidateId).apply();
            }
            return Result.success();
        } catch (Exception e) {
            return Result.retry();
        }
    }

    private void notifyMessage(JSONObject item, long id) {
        Context ctx = getApplicationContext();
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        NotificationChannel channel = new NotificationChannel(CHANNEL, "JANUS messages", NotificationManager.IMPORTANCE_DEFAULT);
        channel.setDescription("Messages initiated by JANUS background processing");
        nm.createNotificationChannel(channel);
        Intent intent = new Intent(ctx, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pending = PendingIntent.getActivity(ctx, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String type = item.optString("message_type", "Message");
        String detail = item.optString("detail", "JANUS has a new message.");
        NotificationCompat.Builder n = new NotificationCompat.Builder(ctx, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("JANUS · " + type)
                .setContentText(detail)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(detail))
                .setContentIntent(pending)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT);
        nm.notify((int)(id % Integer.MAX_VALUE), n.build());
    }
}
