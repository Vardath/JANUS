package com.vardath.janus;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
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
                        "else{authMessage.textContent=msg||'Google sign-in was cancelled.';}};" +
                        "window.janusDeleteAccount=async function(){" +
                        "if(!confirm('Permanently delete your JANUS account, memories, messages and account data? This cannot be undone.'))return;" +
                        "var word=prompt('Type DELETE to confirm permanent account deletion.');if(word!=='DELETE')return;" +
                        "var pwd=prompt('Enter your current JANUS password. If this is a Google-only account, leave this blank.');" +
                        "try{await api('DELETE','/auth/account',{confirmation:'DELETE',current_password:pwd||null});" +
                        "localStorage.removeItem('janusToken');localStorage.removeItem('janusAccountId');localStorage.removeItem('janusProfile');Android.clearSession();alert('Your JANUS account has been deleted.');location.reload();" +
                        "}catch(e){alert('Account deletion failed. '+e.message);}};" +
                        "window.janusReportResponse=async function(box,text){" +
                        "var cats='harmful, harassment, sexual, hate, self-harm, illegal, privacy, misinformation, other';" +
                        "var category=prompt('Report this JANUS response. Choose a category:\\n'+cats,'other');if(category===null)return;category=category.trim().toLowerCase();" +
                        "if(cats.split(', ').indexOf(category)<0){alert('Please use one of the listed report categories.');return;}" +
                        "var details=prompt('Optional: tell us what was wrong with this response.','')||'';" +
                        "var previous=box.previousElementSibling;var context=(previous&&previous.classList.contains('user'))?previous.innerText:'';" +
                        "try{var r=await api('POST','/safety/report',{category:category,response_text:text,user_context:context,details:details});alert(r.message||'Report submitted. Thank you.');}" +
                        "catch(e){alert('Unable to submit report. '+e.message);}};" +
                        "if(window.addMsg&&!window.__janusReportWrapped){window.__janusReportWrapped=true;var originalAddMsg=window.addMsg;window.addMsg=function(who,text){originalAddMsg(who,text);if(who==='JANUS'){var box=chatlog.lastElementChild;if(box&&!box.querySelector('.janus-report')){var b=document.createElement('button');b.className='janus-report';b.textContent='Report';b.style.cssText='margin-top:8px;border:0;background:transparent;color:#666;text-decoration:underline;padding:2px 0;font-size:12px';b.onclick=function(){window.janusReportResponse(box,String(text||''));};box.appendChild(document.createElement('br'));box.appendChild(b);}}};}" +
                        "(function(){var box=document.querySelector('#options .options');if(box&&!document.getElementById('deleteAccountBtn')){var b=document.createElement('button');b.id='deleteAccountBtn';b.style.borderColor='#b00020';b.style.color='#b00020';b.innerHTML='<b>Delete account</b><br><span class=\"small\">Permanently delete this JANUS account and associated data</span>';b.onclick=window.janusDeleteAccount;box.appendChild(b);}})();" +
                        "(function(){var top=document.querySelector('.top');if(top&&top.childNodes.length)top.childNodes[0].nodeValue='JANUS · 11 cores · 7→2→1→1 ';var buttons=document.querySelectorAll('#options .options button');buttons.forEach(function(b){if((b.getAttribute('onclick')||'').indexOf(\"showSub('cores')\")>=0)b.innerHTML='<b>Cores · 11 active</b><br><span class=\"small\">7 specialists → 2 hemispheres → consensus → interface</span>';});var cl=document.getElementById('coreList');if(cl&&!document.getElementById('coreTopology')){var d=document.createElement('div');d.id='coreTopology';cl.parentNode.insertBefore(d,cl);}})();" +
                        "window.renderCoreSide=function(title,r,isLocal){var cores=(r&&r.cores)||{};var names=['evidence','logic','counterpoint','context','memory','safety','novelty','left_hemisphere','right_hemisphere','consensus','interface'];var h='<div class=\"card\"><b>'+esc(title)+'</b><br><span class=\"small\">'+esc(r.topology||'7 → 2 → 1 → 1')+' · phase '+esc(r.phase||'unknown')+' · storage '+esc(r.storage_backend||(r.persistent_storage?'persistent':'unknown'))+(isLocal?' · sync '+esc(r.sync_state||'unknown'):' · clients '+esc(r.remote_clients||0))+'</span></div>';h+='<div class=\"grid\">';names.forEach(function(n){var c=cores[n]||{};var role=n.replaceAll('_',' ');h+='<div class=\"card\"><b>'+esc(role)+'</b><div class=\"small\">cycles '+esc(c.cycle_count||0)+' · pending '+esc(c.pending_messages||0)+'</div><div class=\"small\">'+esc((c.last_output||'').slice(0,180))+'</div></div>';});return h+'</div>';};" +
                        "window.refreshCoreTopology=async function(){var host=document.getElementById('coreTopology');if(!host)return;try{var local=JSON.parse(Android.localCoreStatus());var global=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=global.runtime||global;host.innerHTML='<div class=\"card\"><b>JANUS 11-core topology</b><p>7 specialist perspectives feed two hemispheres. The hemispheres feed the consensus reader/giver. Consensus feeds the interface core that represents JANUS to you.</p><div class=\"small\">Local and global runtimes synchronize compact state without using paid API calls for their background cycles.</div></div>'+window.renderCoreSide('This device · local JANUS',local,true)+window.renderCoreSide('Online · global JANUS',gr,false);}catch(e){host.innerHTML='<div class=\"card\"><b>11-core runtime</b><div class=\"small\">Unable to refresh live core status: '+esc(e.message)+'</div></div>';}};" +
                        "if(window.refresh&&!window.__janusCoreRefreshWrapped){window.__janusCoreRefreshWrapped=true;var oldRefresh=window.refresh;window.refresh=function(p){var x=oldRefresh(p);if(p==='cores')setTimeout(window.refreshCoreTopology,80);return x;};}" +
                        "if(window.show&&!window.__janusCoreShowWrapped){window.__janusCoreShowWrapped=true;var oldShow=window.show;window.show=function(p){var x=oldShow(p);if(p==='cores')setTimeout(window.refreshCoreTopology,80);return x;};}";
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

    private String learnAccessToken(String json) {
        try {
            JSONObject body = new JSONObject(json == null ? "{}" : json);
            String token = body.optString("_janus_token", "").trim();
            if (!token.isEmpty()) {
                getSharedPreferences("janus", MODE_PRIVATE).edit().putString("access_token", token).apply();
                return token;
            }
        } catch (Exception ignored) {}
        String saved = getSharedPreferences("janus", MODE_PRIVATE).getString("access_token", "");
        return saved == null ? "" : saved.trim();
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
            GetCredentialRequest request = new GetCredentialRequest.Builder().addCredentialOption(option).build();
            credentialManager.getCredentialAsync(this, request, new CancellationSignal(), getMainExecutor(),
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
                    });
        } catch (Exception e) {
            googleResult(false, "Unable to start Google sign-in: " + e.getMessage());
        }
    }

    public class Bridge {
        @JavascriptInterface public String profileId() {
            String saved = getSharedPreferences("janus", MODE_PRIVATE).getString("profile_id", "");
            return saved == null ? "" : saved;
        }
        @JavascriptInterface public void setProfile(String profile) {
            persistProfile(profile);
            scheduleMessageChecks();
        }
        @JavascriptInterface public void clearSession() {
            getSharedPreferences("janus", MODE_PRIVATE).edit()
                    .remove("access_token").remove("profile_id").remove("last_notified_message").apply();
        }
        @JavascriptInterface public String localCoreStatus() {
            try { return JanusLocalCoreRuntime.get(MainActivity.this).statusJson().toString(); }
            catch (Exception e) { return "{\"architecture\":\"11-core\",\"phase\":\"unknown\",\"error\":\"local status unavailable\"}"; }
        }
        @JavascriptInterface public void googleSignIn() { runOnUiThread(MainActivity.this::startGoogleSignIn); }
        @JavascriptInterface public String serverUrl() { return SERVER; }
        @JavascriptInterface public void request(String id, String method, String path, String json) {
            learnProfile(path, json);
            final String accessToken = learnAccessToken(json);
            pool.submit(() -> {
                String result;
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(SERVER + path).openConnection();
                    c.setRequestMethod(method);
                    c.setConnectTimeout(20000);
                    c.setReadTimeout(120000);
                    c.setRequestProperty("Accept", "application/json");
                    if (!accessToken.isEmpty()) c.setRequestProperty("Authorization", "Bearer " + accessToken);
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
