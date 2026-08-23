package com.vardath.janus;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.content.ContentValues;
import android.provider.MediaStore;
import android.util.Base64;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.annotation.NonNull;
import androidx.credentials.ClearCredentialStateRequest;
import androidx.credentials.Credential;
import androidx.credentials.CredentialManager;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.CustomCredential;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.exceptions.ClearCredentialException;
import androidx.credentials.exceptions.GetCredentialException;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.core.content.FileProvider;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.tasks.Task;
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
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
    private static final int RC_GOOGLE_COMPAT = 731;
    private static final int RC_FILE_PICKER = 732;
    private static final int RC_ARTIFACT_EXPORT = 733;
    private static final int MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024;
    private WebView web;
    private CredentialManager credentialManager;
    private GoogleSignInClient legacyGoogleClient;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    private String pendingArtifactFileId = "";
    private String pendingArtifactName = "JANUS-artifact.md";
    private String pendingArtifactMime = "text/markdown";

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 137);
        }
        credentialManager = CredentialManager.create(this);
        JanusLocalCoreRuntime.get(this).start();
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
                        "(function(){var top=document.querySelector('.top');if(top&&top.childNodes.length)top.childNodes[0].nodeValue='JANUS · 11 cores · 7→2→1→1 ';var buttons=document.querySelectorAll('#options .options button');buttons.forEach(function(b){if((b.getAttribute('onclick')||'').indexOf(\"showSub('cores')\")>=0)b.innerHTML='<b>Cores · interface always active</b><br><span class=\"small\">7 specialists → 2 hemispheres → consensus → interface</span>';});var cl=document.getElementById('coreList');if(cl&&!document.getElementById('coreTopology')){var d=document.createElement('div');d.id='coreTopology';cl.parentNode.insertBefore(d,cl);}})();" +
                        "window.janusHeaderStatus=function(){try{var r=JSON.parse(Android.localCoreStatus());if(window.status)status.textContent=(r.phase==='wake'?'Active · full-rate society':'Active · low-duty society');}catch(e){if(window.status)status.textContent='Active';}};" +
                        "if(window.setStatus&&!window.__janusStatusWrapped){window.__janusStatusWrapped=true;var oldSetStatus=window.setStatus;window.setStatus=function(s){if(s==='Dormant'||s==='Active'){window.janusHeaderStatus();return;}oldSetStatus(s);};}window.janusHeaderStatus();" +
                        "window.janusDrainOfflineReplies=function(){try{var a=JSON.parse(Android.drainQueuedReplies()||'[]');a.forEach(function(x){if(x&&x.reply)addMsg('JANUS',x.reply+'\\n\\n[Delivered from the offline queue]');});}catch(e){}};setTimeout(window.janusDrainOfflineReplies,250);" +
                        "window.renderCoreSide=function(title,r,isLocal){var cores=(r&&r.cores)||{};var names=['evidence','logic','counterpoint','context','memory','safety','novelty','left_hemisphere','right_hemisphere','consensus','interface'];var h='<div class=\"card\"><b>'+esc(title)+'</b><br><span class=\"small\">'+esc(r.topology||'7 → 2 → 1 → 1')+' · phase '+esc(r.phase||'unknown')+' · storage '+esc(r.storage_backend||(r.persistent_storage?'persistent':'unknown'))+(isLocal?' · sync '+esc(r.sync_state||'unknown'):' · clients '+esc(r.remote_clients||0))+'</span></div>';h+='<div class=\"grid\">';names.forEach(function(n){var c=cores[n]||{};var role=n.replaceAll('_',' ');var mode=c.processing_mode||((c.awake)?'awake':'resting');h+='<div class=\"card\"><b>'+esc(role)+'</b><div class=\"small\">'+esc(mode)+' · cycles '+esc(c.cycle_count||0)+' · pending '+esc(c.pending_messages||0)+'</div><div class=\"small\">'+esc((c.last_output||'').slice(0,180))+'</div></div>';});return h+'</div>';};" +
                        "window.refreshCoreTopology=async function(){var host=document.getElementById('coreTopology');if(!host)return;try{var local=JSON.parse(Android.localCoreStatus());var global=await api('GET','/desktop/runtime-cores?username='+encodeURIComponent(profile));var gr=global.runtime||global;host.innerHTML='<div class=\"card\"><b>JANUS 11-core topology</b><p>7 specialist perspectives feed two hemispheres. The hemispheres feed the consensus reader/giver. Consensus feeds the interface core that represents JANUS to you.</p><div class=\"small\">The local society runs independently on this device. Server synchronization is optional and does not power local core cycles.</div></div>'+window.renderCoreSide('This device · local JANUS',local,true)+window.renderCoreSide('Online · global JANUS',gr,false);}catch(e){try{var local=JSON.parse(Android.localCoreStatus());host.innerHTML='<div class=\"card\"><b>Local JANUS active · server unavailable</b></div>'+window.renderCoreSide('This device · local JANUS',local,true);}catch(_){host.innerHTML='<div class=\"card\"><b>11-core runtime</b><div class=\"small\">Unable to refresh live core status.</div></div>';}}};" +
                        "window.janusLocalEvidence=function(p){try{var r=JSON.parse(Android.localCoreStatus());var events=(r.observe_events||[]).slice().reverse();if(p==='observe'){var rows=events.filter(function(x){return observeMode==='all'||(observeMode==='interactions'&&x.event_type==='interaction')||(observeMode==='thoughts'&&x.event_type!=='interaction');}).slice(0,160);var h=rows.map(function(x){return '<div class=\"card\"><b>local · '+esc((x.core_name||'core').replaceAll('_',' '))+(x.peer_core?' → '+esc(x.peer_core.replaceAll('_',' ')):'')+' · '+esc((x.event_type||'note').replaceAll('_',' '))+'</b><div class=\"small\">'+fmt(new Date(Number(x.created_at||0)).toISOString())+' · this device</div><div>'+esc(x.detail||'')+'</div></div>';}).join('');if(h){var old=observeList.innerHTML;if(old.indexOf('No observable core activity yet.')>=0)old='';observeList.innerHTML='<div class=\"card\"><b>This device · live local journal</b><div class=\"small\">Available without server sync.</div></div>'+h+old;}}if(p==='memory'){var mem=(r.local_memories||[]).slice().reverse().slice(0,80);if(mem.length){var old=memoryList.innerHTML;if(old.indexOf('No memories yet.')>=0)old='';memoryList.innerHTML='<div class=\"card\"><b>This device · local memory</b><div class=\"small\">App-private continuity used by autonomous local pulses.</div></div>'+mem.map(function(x){return '<div class=\"item\"><b>local · working</b><div>'+esc(x)+'</div></div>';}).join('')+old;}}if(p==='activity'){var rows=events.filter(function(x){return ['autonomous_pulse','self_assessment','process_note','interaction','user_topic','phase'].indexOf(x.event_type)>=0;}).slice(0,120);if(rows.length){var old=activityList.innerHTML;if(old.indexOf('No activity yet.')>=0)old='';activityList.innerHTML='<div class=\"card\"><b>This device · local activity</b></div>'+rows.map(function(x){return '<div class=\"item\"><b>'+esc((x.event_type||'activity').replaceAll('_',' '))+' · '+esc((x.core_name||'core').replaceAll('_',' '))+'</b><div class=\"small\">'+fmt(new Date(Number(x.created_at||0)).toISOString())+'</div><div>'+esc(x.detail||'')+'</div></div>';}).join('')+old;}}}catch(e){}};" +
                        "if(window.refresh&&!window.__janusCoreRefreshWrapped){window.__janusCoreRefreshWrapped=true;var oldRefresh=window.refresh;window.refresh=async function(p){var x;try{x=await oldRefresh(p);}catch(e){}if(p==='cores')setTimeout(window.refreshCoreTopology,80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},80);return x;};}" +
                        "if(window.show&&!window.__janusCoreShowWrapped){window.__janusCoreShowWrapped=true;var oldShow=window.show;window.show=function(p){var x=oldShow(p);if(p==='cores')setTimeout(window.refreshCoreTopology,80);if(p==='observe'||p==='memory'||p==='activity')setTimeout(function(){window.janusLocalEvidence(p);},120);return x;};}";
                js += "window.__janusTelemetryV068=true;window.refreshCoreTopology=function(){var host=document.getElementById('coreTopology');if(!host)return;var local={};try{local=JSON.parse(Android.localCoreStatus()||'{}');}catch(e){}var raw='';try{raw=Android.serverCoreStatus()||'';}catch(e){}var server={};try{if(raw)server=JSON.parse(raw);}catch(e){}var has=server&&server.cores&&Object.keys(server.cores).length>0;var intro='<div class=\"card\"><b>JANUS 11-core topology</b><div class=\"small\">This device and Server JANUS are independent runtimes. Server values come from the authenticated core-sync exchange already used by this app.</div></div>';var sh=has?window.renderCoreSide('SERVER JANUS · LIVE',server,false):'<div class=\"card\"><b>SERVER JANUS · WAITING FOR SYNC SNAPSHOT</b><div class=\"small\">Local sync: '+esc(local.sync_state||'unknown')+'. Snapshot bytes: '+esc(raw?raw.length:0)+'. Connected + zero bytes means native capture failed; nonzero bytes means rendering/parser failed.</div></div>';host.innerHTML=intro+window.renderCoreSide('THIS DEVICE JANUS · LIVE',local,true)+sh;};if(!window.__janusTelemetryPollV068){window.__janusTelemetryPollV068=setInterval(function(){try{var v=document.getElementById('cores');if(v&&v.classList.contains('active'))window.refreshCoreTopology();}catch(e){}},3000);}";
                view.evaluateJavascript(js, null);
                pool.submit(() -> {
                    JanusOfflineQueue.flush(MainActivity.this);
                    deliverQueuedRepliesToWeb();
                });
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

    private void deliverQueuedRepliesToWeb() {
        if (web == null) return;
        String raw = JanusOfflineQueue.drainReplies(this);
        try { if (new JSONArray(raw).length() == 0) return; } catch (Exception e) { return; }
        final String js = "(function(){try{var a=JSON.parse(" + quote(raw) + ");a.forEach(function(x){if(x&&x.reply)addMsg('JANUS',x.reply+'\\n\\n[Delivered from the offline queue]');});}catch(e){}})();";
        runOnUiThread(() -> web.evaluateJavascript(js, null));
    }

    private void googleResult(boolean ok, String message) {
        if (web == null) return;
        final String js = "window.__janusGoogleResult(" + ok + "," + quote(message) + ")";
        runOnUiThread(() -> web.evaluateJavascript(js, null));
    }

    private String googleClientId() { return BuildConfig.GOOGLE_WEB_CLIENT_ID == null ? "" : BuildConfig.GOOGLE_WEB_CLIENT_ID.trim(); }

    private void requestGoogleCredential(boolean retryAfterClear) {
        String clientId = googleClientId();
        if (clientId.isEmpty()) { googleResult(false, "Google sign-in needs the JANUS Google OAuth client ID configured in the release build."); return; }
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
                                if (GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(type) || GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_SIWG_CREDENTIAL.equals(type)) {
                                    try { GoogleIdTokenCredential google = GoogleIdTokenCredential.createFrom(custom.getData()); googleResult(true, google.getIdToken()); return; }
                                    catch (Exception e) { googleResult(false, "Google returned an unreadable identity token. Please try again."); return; }
                                }
                            }
                            googleResult(false, "Google did not return a supported identity credential.");
                        }
                        @Override public void onError(@NonNull GetCredentialException e) {
                            String message = e.getLocalizedMessage(); String lower = message == null ? "" : message.toLowerCase();
                            boolean reauth = lower.contains("reauth") || lower.contains("[16]") || lower.contains("account reauth");
                            if (reauth && !retryAfterClear) { clearGoogleCredentialStateAndRetry(); return; }
                            if (reauth) startLegacyGoogleFallback(); else googleResult(false, message == null || message.isBlank() ? "Google sign-in was cancelled or unavailable." : message);
                        }
                    });
        } catch (Exception e) { googleResult(false, "Unable to start Google sign-in: " + e.getMessage()); }
    }

    @SuppressWarnings("deprecation")
    private void startLegacyGoogleFallback() {
        String clientId = googleClientId();
        if (clientId.isEmpty()) { googleResult(false, "Google sign-in is not configured for this build."); return; }
        try {
            GoogleSignInOptions options = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN).requestIdToken(clientId).requestEmail().build();
            legacyGoogleClient = GoogleSignIn.getClient(this, options);
            googleResult(false, "Credential Manager could not reauthenticate this device; trying Google compatibility sign-in…");
            startActivityForResult(legacyGoogleClient.getSignInIntent(), RC_GOOGLE_COMPAT);
        } catch (Exception e) { googleResult(false, "Google compatibility sign-in could not start: " + e.getMessage()); }
    }

    private void clearGoogleCredentialStateAndRetry() {
        try {
            credentialManager.clearCredentialStateAsync(new ClearCredentialStateRequest(), new CancellationSignal(), getMainExecutor(),
                    new CredentialManagerCallback<Void, ClearCredentialException>() {
                        @Override public void onResult(Void result) { requestGoogleCredential(true); }
                        @Override public void onError(@NonNull ClearCredentialException e) { requestGoogleCredential(true); }
                    });
        } catch (Exception ignored) { requestGoogleCredential(true); }
    }

    private void startGoogleSignIn() { requestGoogleCredential(false); }



    private String accessToken() {
        String token = getSharedPreferences("janus", MODE_PRIVATE).getString("access_token", "");
        return token == null ? "" : token;
    }

    private byte[] downloadArtifactBytes(String fileId) throws Exception {
        if (fileId == null || fileId.isBlank()) throw new IllegalArgumentException("Artifact file is unavailable.");
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(SERVER + "/files/" + java.net.URLEncoder.encode(fileId, "UTF-8") + "/download").openConnection();
            c.setRequestMethod("GET");
            c.setConnectTimeout(20000);
            c.setReadTimeout(120000);
            String token = accessToken();
            if (!token.isBlank()) c.setRequestProperty("Authorization", "Bearer " + token);
            int code = c.getResponseCode();
            if (code >= 400) throw new IllegalStateException("JANUS could not export this artifact (HTTP " + code + ").");
            try (InputStream input = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[32768]; int n;
                while ((n = input.read(buffer)) >= 0) out.write(buffer, 0, n);
                return out.toByteArray();
            }
        } finally { if (c != null) c.disconnect(); }
    }

    private void artifactResult(boolean ok, String message) {
        final String js = "if(window.__janusArtifactExportResult)window.__janusArtifactExportResult(" + ok + "," + quote(message == null ? "" : message) + ")";
        runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
    }

    private void startArtifactExport(String fileId, String filename, String mime) {
        pendingArtifactFileId = fileId == null ? "" : fileId;
        pendingArtifactName = filename == null || filename.isBlank() ? "JANUS-artifact.md" : filename;
        pendingArtifactMime = mime == null || mime.isBlank() ? "application/octet-stream" : mime;
        try {
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType(pendingArtifactMime);
            intent.putExtra(Intent.EXTRA_TITLE, pendingArtifactName);
            startActivityForResult(intent, RC_ARTIFACT_EXPORT);
        } catch (Exception e) { artifactResult(false, "Unable to open Android export: " + e.getMessage()); }
    }

    private void finishArtifactExport(Uri destination) {
        final String fileId = pendingArtifactFileId;
        pool.submit(() -> {
            try {
                byte[] bytes = downloadArtifactBytes(fileId);
                try (OutputStream out = getContentResolver().openOutputStream(destination, "w")) {
                    if (out == null) throw new IllegalStateException("Android could not open the selected destination.");
                    out.write(bytes);
                }
                artifactResult(true, "Artifact exported successfully.");
            } catch (Exception e) { artifactResult(false, e.getMessage()); }
        });
    }

    private void shareArtifact(String fileId, String filename, String mime) {
        final String safeName = (filename == null || filename.isBlank()) ? "JANUS-artifact.md" : filename.replaceAll("[\\/]+", "-");
        final String safeMime = (mime == null || mime.isBlank()) ? "application/octet-stream" : mime;
        pool.submit(() -> {
            try {
                byte[] bytes = downloadArtifactBytes(fileId);
                File dir = new File(getCacheDir(), "shared_artifacts");
                if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Could not prepare Android share storage.");
                File out = new File(dir, safeName);
                try (FileOutputStream stream = new FileOutputStream(out)) { stream.write(bytes); }
                Uri uri = FileProvider.getUriForFile(MainActivity.this, getPackageName() + ".fileprovider", out);
                runOnUiThread(() -> {
                    try {
                        Intent send = new Intent(Intent.ACTION_SEND);
                        send.setType(safeMime);
                        send.putExtra(Intent.EXTRA_STREAM, uri);
                        send.putExtra(Intent.EXTRA_SUBJECT, safeName);
                        send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        startActivity(Intent.createChooser(send, "Share JANUS artifact"));
                        artifactResult(true, "Android share sheet opened.");
                    } catch (Exception e) { artifactResult(false, "Unable to share artifact: " + e.getMessage()); }
                });
            } catch (Exception e) { artifactResult(false, e.getMessage()); }
        });
    }

    private void startFilePicker() {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("*/*");
            startActivityForResult(intent, RC_FILE_PICKER);
        } catch (Exception e) {
            deliverFilePickerError("Unable to open the file picker: " + e.getMessage());
        }
    }

    private String displayName(Uri uri) {
        String name = "attachment";
        Cursor cursor = null;
        try {
            cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null);
            if (cursor != null && cursor.moveToFirst()) {
                int i = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (i >= 0 && cursor.getString(i) != null && !cursor.getString(i).isBlank()) name = cursor.getString(i);
            }
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
        return name;
    }

    private byte[] readAttachment(Uri uri) throws Exception {
        try (InputStream input = getContentResolver().openInputStream(uri); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            if (input == null) throw new IllegalArgumentException("The selected file could not be opened.");
            byte[] buffer = new byte[32768];
            int total = 0, n;
            while ((n = input.read(buffer)) >= 0) {
                total += n;
                if (total > MAX_ATTACHMENT_BYTES) throw new IllegalArgumentException("JANUS currently accepts files up to 8 MiB.");
                out.write(buffer, 0, n);
            }
            if (total == 0) throw new IllegalArgumentException("Empty files are not supported.");
            return out.toByteArray();
        }
    }

    private void deliverFilePickerError(String message) {
        final String js = "if(window.__janusFilePickError)window.__janusFilePickError(" + quote(message == null ? "File selection failed." : message) + ")";
        runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
    }

    private void deliverPickedFile(Uri uri) {
        pool.submit(() -> {
            try {
                byte[] bytes = readAttachment(uri);
                String mime = getContentResolver().getType(uri);
                if (mime == null || mime.isBlank()) mime = "application/octet-stream";
                JSONObject item = new JSONObject();
                item.put("filename", displayName(uri));
                item.put("mime_type", mime);
                item.put("data_base64", Base64.encodeToString(bytes, Base64.NO_WRAP));
                final String js = "if(window.__janusFilePicked)window.__janusFilePicked(JSON.parse(" + quote(item.toString()) + "))";
                runOnUiThread(() -> { if (web != null) web.evaluateJavascript(js, null); });
            } catch (Exception e) {
                deliverFilePickerError(e.getMessage());
            }
        });
    }

    @Override @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == RC_FILE_PICKER) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) deliverPickedFile(data.getData());
            else deliverFilePickerError("File selection was cancelled.");
            return;
        }
        if (requestCode == RC_ARTIFACT_EXPORT) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) finishArtifactExport(data.getData());
            else artifactResult(false, "Artifact export was cancelled.");
            return;
        }
        if (requestCode != RC_GOOGLE_COMPAT) return;
        try {
            Task<GoogleSignInAccount> task = GoogleSignIn.getSignedInAccountFromIntent(data);
            GoogleSignInAccount account = task.getResult(ApiException.class);
            String token = account == null ? null : account.getIdToken();
            if (token == null || token.isBlank()) { googleResult(false, "Google compatibility sign-in returned no identity token."); return; }
            googleResult(true, token);
        } catch (ApiException e) {
            googleResult(false, "Google compatibility sign-in failed (code " + e.getStatusCode() + "). If this persists, the Android OAuth client and Web client must be checked in the same Google Cloud project.");
        } catch (Exception e) { googleResult(false, "Google compatibility sign-in failed: " + e.getMessage()); }
    }

    private static boolean isTransientGateway(int code) { return code == 502 || code == 503 || code == 504; }

    private static String readBody(HttpURLConnection c, int code) throws Exception {
        if (code >= 400 && c.getErrorStream() == null) return "";
        BufferedReader r = new BufferedReader(new InputStreamReader(code >= 400 ? c.getErrorStream() : c.getInputStream(), StandardCharsets.UTF_8));
        StringBuilder b = new StringBuilder(); String line;
        while ((line = r.readLine()) != null) if (b.length() < 8192) b.append(line);
        r.close(); return b.toString();
    }

    private static String safeServerBody(int code, String body) {
        String raw = body == null ? "" : body.trim(); String lower = raw.toLowerCase();
        boolean html = lower.startsWith("<!doctype html") || lower.startsWith("<html") || lower.contains("<body") || lower.contains("bad gateway") || lower.contains("service unavailable");
        if (isTransientGateway(code) || html) return "{\"detail\":\"JANUS server is temporarily unavailable. Please try again shortly.\"}";
        if (raw.length() > 8192) raw = raw.substring(0, 8192); return raw;
    }

    public class Bridge {
        @JavascriptInterface public String profileId() { String saved = getSharedPreferences("janus", MODE_PRIVATE).getString("profile_id", ""); return saved == null ? "" : saved; }
        @JavascriptInterface public void setProfile(String profile) { persistProfile(profile); scheduleMessageChecks(); }
        @JavascriptInterface public String drainQueuedReplies() { return JanusOfflineQueue.drainReplies(MainActivity.this); }
        @JavascriptInterface public int queuedMessageCount() { return JanusOfflineQueue.pendingCount(MainActivity.this); }
        @JavascriptInterface public void clearSession() {
            getSharedPreferences("janus", MODE_PRIVATE).edit().remove("access_token").remove("profile_id").remove("last_notified_message").apply();
            runOnUiThread(() -> {
                try { credentialManager.clearCredentialStateAsync(new ClearCredentialStateRequest(), new CancellationSignal(), getMainExecutor(), new CredentialManagerCallback<Void, ClearCredentialException>() {
                    @Override public void onResult(Void result) {}
                    @Override public void onError(@NonNull ClearCredentialException e) {}
                }); } catch (Exception ignored) {}
                try { if (legacyGoogleClient != null) legacyGoogleClient.signOut(); } catch (Exception ignored) {}
            });
        }
        @JavascriptInterface public String localCoreStatus() {
            try { return JanusLocalCoreRuntime.get(MainActivity.this).statusJson().toString(); }
            catch (Exception e) { return "{\"architecture\":\"11-core\",\"phase\":\"unknown\",\"error\":\"local status unavailable\"}"; }
        }
        @JavascriptInterface public String serverCoreStatus() { try { return JanusLocalCoreRuntime.get(MainActivity.this).serverStatusJson(); } catch (Exception e) { return ""; } }
        @JavascriptInterface public void googleSignIn() { runOnUiThread(MainActivity.this::startGoogleSignIn); }
        @JavascriptInterface public void pickFile() { runOnUiThread(MainActivity.this::startFilePicker); }
        @JavascriptInterface public void exportArtifact(String fileId, String filename, String mime) { runOnUiThread(() -> startArtifactExport(fileId, filename, mime)); }
        @JavascriptInterface public void shareArtifact(String fileId, String filename, String mime) { MainActivity.this.shareArtifact(fileId, filename, mime); }
        @JavascriptInterface public String serverUrl() { return SERVER; }
        @JavascriptInterface public void request(String id, String method, String path, String json) {
            final boolean isChat = "POST".equals(method) && "/desktop/chat".equals(path);
            final String requestJson = isChat ? JanusOfflineQueue.prepareChatBody(json) : (json == null ? "{}" : json);
            learnProfile(path, requestJson);
            final String accessToken = learnAccessToken(requestJson);
            if (isChat) {
                try { String m = new JSONObject(requestJson).optString("message", new JSONObject(requestJson).optString("text", "")); JanusLocalCoreRuntime.get(MainActivity.this).ingestUserMessage(m); }
                catch (Exception ignored) {}
            }
            pool.submit(() -> {
                String result = null; Exception lastException = null; int maxAttempts = isChat ? 5 : 3;
                for (int attempt = 1; attempt <= maxAttempts; attempt++) {
                    HttpURLConnection c = null;
                    try {
                        c = (HttpURLConnection) new URL(SERVER + path).openConnection(); c.setRequestMethod(method); c.setConnectTimeout(isChat ? 30000 : 20000); c.setReadTimeout(120000); c.setRequestProperty("Accept", "application/json");
                        if (!accessToken.isEmpty()) c.setRequestProperty("Authorization", "Bearer " + accessToken);
                        if (!"GET".equals(method)) { c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json"); try (OutputStream os = c.getOutputStream()) { os.write(requestJson.getBytes(StandardCharsets.UTF_8)); } }
                        int code = c.getResponseCode(); String body = safeServerBody(code, readBody(c, code));
                        if ((isTransientGateway(code) || (isChat && code == 409)) && attempt < maxAttempts) { try { Thread.sleep(Math.min(8000L, 1500L * attempt)); } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); } continue; }
                        result = "{\"ok\":" + (code < 400) + ",\"status\":" + code + ",\"body\":" + quote(body) + "}";
                        if (code < 400 && isChat) {
                            try { JSONObject parsed=new JSONObject(body); String reply=parsed.optString("reply",parsed.optString("response","")); JanusLocalCoreRuntime.get(MainActivity.this).ingestServerReply(reply); } catch(Exception ignored) {}
                            JanusOfflineQueue.flush(MainActivity.this); deliverQueuedRepliesToWeb();
                        }
                        break;
                    } catch (Exception e) {
                        lastException = e;
                        if (attempt < maxAttempts) { try { Thread.sleep(Math.min(8000L, 1500L * attempt)); } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); } continue; }
                    } finally { if (c != null) c.disconnect(); }
                }
                if (result == null && isChat) {
                    int pending = JanusOfflineQueue.enqueue(MainActivity.this, requestJson);
                    String ack = "I’m still here. I saved that message on this device because the server connection did not complete. The local 11-core society has already received the topic and can continue its zero-API cycles. Queued: " + pending + ".";
                    String body = "{\"reply\":" + quote(ack) + ",\"profile\":" + quote(Bridge.this.profileId()) + ",\"mode\":\"local_offline_queue\",\"stored_locally\":true,\"queued\":" + pending + "}";
                    result = "{\"ok\":true,\"status\":202,\"body\":" + quote(body) + "}";
                } else if (result == null) {
                    String message = lastException == null ? "JANUS server is temporarily unavailable. Please try again shortly." : "JANUS server connection failed. Please try again shortly.";
                    result = "{\"ok\":false,\"status\":0,\"body\":" + quote("{\"detail\":\"" + message + "\"}") + "}";
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
        pool.shutdownNow(); if (web != null) web.destroy(); super.onDestroy();
    }
}
