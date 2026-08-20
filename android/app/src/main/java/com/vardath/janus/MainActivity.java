package com.vardath.janus;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.annotation.NonNull;
import androidx.credentials.Credential;
import androidx.credentials.CredentialManager;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.CustomCredential;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.exceptions.GetCredentialException;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;

import org.json.JSONObject;

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
    private CredentialManager credentialManager;
    private final ExecutorService pool = Executors.newCachedThreadPool();

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 137);
        }
        credentialManager = CredentialManager.create(this);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                String js = "window.googleComingSoon=function(){Android.googleSignIn();};" +
                        "window.__janusGoogleResult=function(ok,msg){" +
                        "if(ok){authMessage.textContent='Signing in with Google…';" +
                        "api('POST','/auth/google',{id_token:msg},false).then(storeSession).catch(function(e){authMessage.textContent='Google sign-in failed. '+e.message;});}" +
                        "else{authMessage.textContent=msg||'Google sign-in was cancelled.';}};";
                view.evaluateJavascript(js, null);
            }
        });
        web.loadUrl("file:///android_asset/index.html");
        scheduleMessageChecks();
    }

    private void scheduleMessageChecks() {
        PeriodicWorkRequest req = new PeriodicWorkRequest.Builder(JanusMessageWorker.class, 15, TimeUnit.MINUTES).build();
        WorkManager.getInstance(this).enqueueUniquePeriodicWork("janus-message-check", ExistingPeriodicWorkPolicy.UPDATE, req);
    }

    private void persistProfile(String profile) {
        if (profile == null || profile.trim().isEmpty()) return;
        getSharedPreferences("janus", MODE_PRIVATE).edit().putString("profile_id", profile.trim()).apply();
    }

    private void learnProfile(String path, String json) {
        try {
            String p = Uri.parse("https://janus.local" + path).getQueryParameter("username");
            if (p != null && !p.trim().isEmpty()) { persistProfile(p); return; }
        } catch (Exception ignored) {}
        try {
            JSONObject body = new JSONObject(json == null ? "{}" : json);
            String p = body.optString("profile_id", body.optString("username", ""));
            persistProfile(p);
        } catch (Exception ignored) {}
    }

    private void googleResult(boolean ok, String message) {
        if (web == null) return;
        final String js = "window.__janusGoogleResult(" + ok + "," + quote(message) + ")";
        runOnUiThread(() -> web.evaluateJavascript(js, null));
    }

    private void startGoogleSignIn() {
        String clientId = BuildConfig.GOOGLE_WEB_CLIENT_ID == null ? "" : BuildConfig.GOOGLE_WEB_CLIENT_ID.trim();
        if (clientId.isEmpty()) {
            googleResult(false, "Google sign-in needs the JANUS Google OAuth client ID configured in the release build.");
            return;
        }
        try {
            GetSignInWithGoogleOption option = new GetSignInWithGoogleOption.Builder(clientId).build();
            GetCredentialRequest request = new GetCredentialRequest.Builder()
                    .addCredentialOption(option)
                    .build();
            credentialManager.getCredentialAsync(
                    this,
                    request,
                    new CancellationSignal(),
                    getMainExecutor(),
                    new CredentialManagerCallback<GetCredentialResponse, GetCredentialException>() {
                        @Override public void onResult(GetCredentialResponse result) {
                            Credential credential = result.getCredential();
                            if (credential instanceof CustomCredential) {
                                CustomCredential custom = (CustomCredential) credential;
                                String type = custom.getType();
                                if (GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(type)
                                        || GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_SIWG_CREDENTIAL.equals(type)) {
                                    try {
                                        GoogleIdTokenCredential google = GoogleIdTokenCredential.createFrom(custom.getData());
                                        googleResult(true, google.getIdToken());
                                        return;
                                    } catch (Exception e) {
                                        googleResult(false, "Google returned an unreadable identity token.");
                                        return;
                                    }
                                }
                            }
                            googleResult(false, "Google did not return a supported identity credential.");
                        }

                        @Override public void onError(@NonNull GetCredentialException e) {
                            String message = e.getLocalizedMessage();
                            googleResult(false, message == null || message.isBlank() ? "Google sign-in was cancelled or unavailable." : message);
                        }
                    }
            );
        } catch (Exception e) {
            googleResult(false, "Unable to start Google sign-in: " + e.getMessage());
        }
    }

    public class Bridge {
        @JavascriptInterface public String profileId() {
            String saved = getSharedPreferences("janus", MODE_PRIVATE).getString("profile_id", "");
            if (saved != null && !saved.isEmpty()) return saved;
            String id = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
            return "android-" + (id == null ? "local" : id);
        }
        @JavascriptInterface public void setProfile(String profile) {
            persistProfile(profile);
            scheduleMessageChecks();
        }
        @JavascriptInterface public void googleSignIn() { runOnUiThread(MainActivity.this::startGoogleSignIn); }
        @JavascriptInterface public String serverUrl() { return SERVER; }
        @JavascriptInterface public void request(String id, String method, String path, String json) {
            learnProfile(path, json);
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
