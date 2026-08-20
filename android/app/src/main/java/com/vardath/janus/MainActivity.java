package com.vardath.janus;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    static final String SERVER = "https://janus-global-core.onrender.com";
    private WebView web;
    private final ExecutorService pool = Executors.newCachedThreadPool();

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 137);
        }
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.loadUrl("file:///android_asset/index.html");
        scheduleMessageChecks();
    }

    private void scheduleMessageChecks() {
        PeriodicWorkRequest req = new PeriodicWorkRequest.Builder(JanusMessageWorker.class, 15, TimeUnit.MINUTES).build();
        WorkManager.getInstance(this).enqueueUniquePeriodicWork("janus-message-check", ExistingPeriodicWorkPolicy.UPDATE, req);
    }

    public class Bridge {
        @JavascriptInterface public String profileId() {
            String saved = getSharedPreferences("janus", MODE_PRIVATE).getString("profile_id", "");
            if (saved != null && !saved.isEmpty()) return saved;
            String id = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
            return "android-" + (id == null ? "local" : id);
        }
        @JavascriptInterface public void setProfile(String profile) {
            if (profile == null || profile.trim().isEmpty()) return;
            getSharedPreferences("janus", MODE_PRIVATE).edit().putString("profile_id", profile.trim()).apply();
            scheduleMessageChecks();
        }
        @JavascriptInterface public String serverUrl() { return SERVER; }
        @JavascriptInterface public void request(String id, String method, String path, String json) {
            pool.submit(() -> {
                String result;
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(SERVER + path).openConnection();
                    c.setRequestMethod(method);
                    c.setConnectTimeout(20000);
                    c.setReadTimeout(120000);
                    c.setRequestProperty("Accept", "application/json");
                    if (!"GET".equals(method)) {
                        c.setDoOutput(true);
                        c.setRequestProperty("Content-Type", "application/json");
                        byte[] body = (json == null ? "{}" : json).getBytes(StandardCharsets.UTF_8);
                        try (OutputStream os = c.getOutputStream()) { os.write(body); }
                    }
                    int code = c.getResponseCode();
                    BufferedReader r = new BufferedReader(new InputStreamReader(code >= 400 ? c.getErrorStream() : c.getInputStream(), StandardCharsets.UTF_8));
                    StringBuilder b = new StringBuilder(); String line;
                    while ((line = r.readLine()) != null) b.append(line);
                    r.close();
                    result = "{\"ok\":" + (code < 400) + ",\"status\":" + code + ",\"body\":" + quote(b.toString()) + "}";
                } catch (Exception e) {
                    result = "{\"ok\":false,\"status\":0,\"body\":" + quote(e.toString()) + "}";
                }
                final String js = "window.__janusResult(" + quote(id) + "," + result + ")";
                runOnUiThread(() -> web.evaluateJavascript(js, null));
            });
        }
    }

    private static String quote(String s) {
        if (s == null) return "\"\"";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }

    @Override protected void onDestroy() {
        pool.shutdownNow();
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
