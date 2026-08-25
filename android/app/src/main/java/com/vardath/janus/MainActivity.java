package com.vardath.janus;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.text.InputType;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.tasks.Task;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * JANUS Android native product rebuild.
 *
 * One authoritative native UI, no WebView, no generated HTML and no build-time
 * patch chain. The server remains authoritative for account ownership, memory,
 * research, artifacts and maintenance; the local runtime remains a distinct,
 * zero-model-call 11-core device society.
 */
public final class MainActivity extends Activity {
    public static final String SERVER = JanusApiClient.SERVER;
    private static final String PREFS = JanusApiClient.PREFS;
    private static final int RC_GOOGLE = 731;
    private static final int RC_FILE = 732;
    private static final int RC_EXPORT = 733;
    private static final int MAX_FILE_BYTES = 8 * 1024 * 1024;
    private static final int MAX_ATTACHMENTS = 4;
    private static final String[] CORE_NAMES = new String[]{
            "evidence", "safety", "counterpoint", "context", "logic", "novelty", "memory",
            "left_hemisphere", "right_hemisphere", "front", "interface"
    };

    private final ExecutorService io = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final List<Attachment> attachments = new ArrayList<>();

    private JanusApiClient api;
    private GoogleSignInClient google;
    private String profile = "";
    private LinearLayout root;
    private LinearLayout content;
    private LinearLayout nav;
    private TextView status;
    private LinearLayout chatLog;
    private ScrollView chatScroll;
    private LinearLayout attachmentStrip;
    private EditText chatComposer;
    private String observeMode = "all";
    private String pendingExportFileId = "";
    private String pendingExportName = "JANUS-artifact.md";
    private String pendingExportMime = "application/octet-stream";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        api = new JanusApiClient(this);
        profile = api.profile();
        GoogleSignInOptions options = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                .requestEmail().requestIdToken(BuildConfig.GOOGLE_WEB_CLIENT_ID).build();
        google = GoogleSignIn.getClient(this, options);
        try { JanusLocalCoreRuntime.get(this).start(); } catch (Exception ignored) {}
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 137);
        }
        if (api.token().trim().isEmpty()) showAuth(); else validateSession();
    }

    @Override protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private SharedPreferences prefs() { return getSharedPreferences(PREFS, Context.MODE_PRIVATE); }

    private void showAuth() {
        attachments.clear();
        root = vertical();
        root.setPadding(dp(24), dp(26), dp(24), dp(24));
        root.setGravity(Gravity.CENTER_VERTICAL);
        applyBackground(root);
        JanusSafeArea.install(root);
        root.addView(text("JANUS", 34, true), full());
        root.addView(text("Sign in to continue your JANUS identity, memory, conversations and research.", 16, false), full());
        LinearLayout tabs = horizontal();
        Button sign = button("Sign in"); Button create = button("Create account");
        tabs.addView(sign, weight()); tabs.addView(create, weight()); root.addView(tabs, full());
        LinearLayout form = vertical(); TextView message = text("", 13, false); root.addView(form, full()); root.addView(message, full());
        Button googleButton = button("Continue with Google"); googleButton.setOnClickListener(v -> startActivityForResult(google.getSignInIntent(), RC_GOOGLE)); root.addView(googleButton, full());
        LinearLayout recovery = horizontal(); Button forgot = button("Forgot password"); Button reset = button("Reset password"); recovery.addView(forgot, weight()); recovery.addView(reset, weight()); root.addView(recovery, full());
        Button verify = button("Verify / resend email"); root.addView(verify, full());
        root.addView(text("Password and Google sign-in use the same JANUS account. Google provides identity only; JANUS owns continuity and account state.", 12, false), full());
        sign.setOnClickListener(v -> renderSignIn(form, message)); create.setOnClickListener(v -> renderRegister(form, message)); forgot.setOnClickListener(v -> promptForgotPassword()); reset.setOnClickListener(v -> promptResetPassword()); verify.setOnClickListener(v -> promptEmailVerification());
        renderSignIn(form, message); setContentView(root);
    }

    private void renderSignIn(LinearLayout form, TextView message) {
        form.removeAllViews(); message.setText(""); EditText id = input("Username or email"); EditText password = input("Password"); password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); Button go = button("Sign in");
        form.addView(id, full()); form.addView(password, full()); form.addView(go, full());
        go.setOnClickListener(v -> { String identity = id.getText().toString().trim(); String pw = password.getText().toString(); if (identity.isEmpty() || pw.isEmpty()) { message.setText("Enter your username/email and password."); return; } JSONObject body = new JSONObject(); try { body.put("identifier", identity); body.put("password", pw); } catch (Exception ignored) {} authRequest("/auth/login", body, message); });
    }

    private void renderRegister(LinearLayout form, TextView message) {
        form.removeAllViews(); message.setText(""); EditText username = input("Username"); EditText email = input("Email"); email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS); EditText password = input("Password (12+ characters, including a letter and number)"); password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); Button go = button("Create account");
        form.addView(username, full()); form.addView(email, full()); form.addView(password, full()); form.addView(go, full());
        go.setOnClickListener(v -> { String u = username.getText().toString().trim(); String e = email.getText().toString().trim(); String pw = password.getText().toString(); if (u.length() < 3 || !e.contains("@") || pw.length() < 12 || !pw.matches(".*[A-Za-z].*") || !pw.matches(".*\\d.*")) { message.setText("Use a 3+ character username, valid email and 12+ character password containing a letter and number."); return; } JSONObject body = new JSONObject(); try { body.put("username", u); body.put("email", e); body.put("password", pw); } catch (Exception ignored) {} authRequest("/auth/register", body, message); });
    }

    private void authRequest(String path, JSONObject body, TextView message) {
        message.setText("Connecting to JANUS…");
        io.execute(() -> { JanusApiClient.Response r = api.post(path, body.toString(), false); if (r.ok()) { try { JSONObject j = new JSONObject(r.body); JSONObject account = j.optJSONObject("account"); String token = j.optString("access_token", ""); String p = account == null ? j.optString("username", "") : account.optString("username", ""); if (!token.isBlank()) { api.saveSession(token, p); profile = p; main.post(this::showApp); return; } } catch (Exception ignored) {} } main.post(() -> message.setText("Sign-in failed · " + readableError(r))); });
    }

    private void validateSession() {
        io.execute(() -> { JanusApiClient.Response r = api.get("/auth/me", true); if (!r.ok()) { api.clearSession(); profile = ""; main.post(this::showAuth); return; } try { JSONObject account = new JSONObject(r.body).optJSONObject("account"); if (account != null) profile = account.optString("username", profile); api.saveSession(api.token(), profile); } catch (Exception ignored) {} main.post(this::showApp); });
    }

    private void promptForgotPassword() { EditText email = input("Email"); new AlertDialog.Builder(this).setTitle("Forgot password").setView(email).setPositiveButton("Send reset code", (d, w) -> { JSONObject body = new JSONObject(); try { body.put("email", email.getText().toString().trim()); } catch (Exception ignored) {} backgroundAction("/auth/forgot-password", body, false, "Password reset request sent. If email delivery is configured, check your inbox."); }).setNegativeButton("Cancel", null).show(); }

    private void promptResetPassword() { LinearLayout box = vertical(); EditText code = input("Reset code"); EditText password = input("New password"); password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); box.addView(code, full()); box.addView(password, full()); new AlertDialog.Builder(this).setTitle("Reset password").setView(box).setPositiveButton("Reset", (d, w) -> { JSONObject body = new JSONObject(); try { body.put("token", code.getText().toString().trim()); body.put("new_password", password.getText().toString()); } catch (Exception ignored) {} backgroundAction("/auth/reset-password", body, false, "Password reset. Sign in with the new password."); }).setNegativeButton("Cancel", null).show(); }

    private void promptEmailVerification() { LinearLayout box = vertical(); EditText code = input("Verification code (leave blank to resend)"); EditText email = input("Email for resend"); box.addView(code, full()); box.addView(email, full()); new AlertDialog.Builder(this).setTitle("Email verification").setView(box).setPositiveButton("Continue", (d, w) -> { String c = code.getText().toString().trim(); JSONObject body = new JSONObject(); try { if (!c.isEmpty()) body.put("token", c); else body.put("email", email.getText().toString().trim()); } catch (Exception ignored) {} backgroundAction(c.isEmpty() ? "/auth/resend-verification" : "/auth/verify-email", body, false, c.isEmpty() ? "Verification resend requested." : "Email verified."); }).setNegativeButton("Cancel", null).show(); }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == RC_FILE) { if (resultCode == RESULT_OK && data != null && data.getData() != null) uploadFile(data.getData()); return; }
        if (requestCode == RC_EXPORT) { if (resultCode == RESULT_OK && data != null && data.getData() != null) finishArtifactExport(data.getData()); return; }
        if (requestCode != RC_GOOGLE) return;
        Task<GoogleSignInAccount> task = GoogleSignIn.getSignedInAccountFromIntent(data);
        try { GoogleSignInAccount account = task.getResult(ApiException.class); String idToken = account == null ? null : account.getIdToken(); if (idToken == null || idToken.isBlank()) { toast("Google returned no identity token."); return; } JSONObject body = new JSONObject(); body.put("id_token", idToken); io.execute(() -> { JanusApiClient.Response r = api.post("/auth/google", body.toString(), false); if (!r.ok()) { main.post(() -> toast("Google sign-in failed · " + readableError(r))); return; } try { JSONObject j = new JSONObject(r.body); JSONObject a = j.optJSONObject("account"); String token = j.optString("access_token", ""); String p = a == null ? "" : a.optString("username", ""); if (token.isBlank()) throw new IllegalStateException("No JANUS session token returned"); api.saveSession(token, p); profile = p; main.post(this::showApp); } catch (Exception e) { main.post(() -> toast("Google identity was accepted but the JANUS session could not be restored.")); } }); }
        catch (ApiException e) { if (e.getStatusCode() == 10) toast("Google configuration mismatch (code 10). The package and signing SHA for this APK must be registered in the same Google project as the JANUS Web client ID."); else toast("Google sign-in failed · code " + e.getStatusCode()); }
        catch (Exception e) { toast("Google sign-in failed."); }
    }

    private void showApp() {
        root = vertical(); applyBackground(root); JanusSafeArea.install(root); LinearLayout header = vertical(); header.setPadding(dp(14), dp(8), dp(14), dp(7)); header.addView(text("JANUS", 20, true), full()); LinearLayout state = horizontal(); state.addView(text("11 cores · 7 → 2 → 1 → 1", 12, false), weight()); status = text("Interface active", 12, false); state.addView(status, wrap()); header.addView(state, full()); root.addView(header, full());
        content = vertical(); content.setPadding(dp(12), dp(6), dp(12), dp(6)); root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
        nav = horizontal(); nav.setPadding(dp(6), dp(4), dp(6), dp(8)); for (String page : new String[]{"Chat", "Messages", "Observe", "Stream", "Options"}) { Button b = button(page); b.setTag(page); b.setMinWidth(dp(92)); b.setOnClickListener(v -> showPage((String) v.getTag())); nav.addView(b, new LinearLayout.LayoutParams(dp(92), dp(58))); } HorizontalScrollView navScroll = new HorizontalScrollView(this); navScroll.setHorizontalScrollBarEnabled(false); navScroll.setFillViewport(true); navScroll.addView(nav, new LinearLayout.LayoutParams(-2, dp(66))); root.addView(navScroll, full()); setContentView(root); scheduleMessageChecks(); showPage("Chat"); io.execute(() -> JanusOfflineQueue.flush(this));
    }

    private void resetContentSurface() { LinearLayout previous = content; LinearLayout fresh = vertical(); fresh.setPadding(dp(12), dp(6), dp(12), dp(6)); LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, 0, 1); int index = previous == null ? 1 : root.indexOfChild(previous); if (previous != null && index >= 0) root.removeView(previous); content = fresh; root.addView(content, index >= 0 ? index : Math.min(1, root.getChildCount()), lp); }
    private void showPage(String page) { resetContentSurface(); for (int i = 0; i < nav.getChildCount(); i++) { Button b = (Button) nav.getChildAt(i); boolean selected = page.equals(b.getTag()); b.setTypeface(Typeface.DEFAULT, selected ? Typeface.BOLD : Typeface.NORMAL); b.setAlpha(selected ? 1f : .62f); } if (page.equals("Messages")) showMessages(); else if (page.equals("Observe")) showObserve(); else if (page.equals("Stream")) showStream(); else if (page.equals("Options")) showOptions(); else showChat(); }
    private void scheduleMessageChecks() { PeriodicWorkRequest req = new PeriodicWorkRequest.Builder(JanusMessageWorker.class, 15, TimeUnit.MINUTES).build(); WorkManager.getInstance(this).enqueueUniquePeriodicWork("janus-message-check", ExistingPeriodicWorkPolicy.UPDATE, req); }

    private void showStream() {
        JanusStreamScreen.render(new JanusStreamScreen.Host() {
            @Override public Activity activity() { return MainActivity.this; }
            @Override public JanusApiClient api() { return api; }
            @Override public void runIo(Runnable work) { io.execute(work); }
            @Override public void runUi(Runnable work) { main.post(work); }
            @Override public JSONObject localRecursiveSnapshot() { return JanusRecursiveCoreBridge.snapshot(); }
        }, content);
    }

    private void showChat() {
        content.addView(text(JanusUiLocalizationPolish.shellText(this, "Chat"), 28, true), full()); chatLog = vertical(); chatScroll = new ScrollView(this); chatScroll.addView(chatLog, full()); content.addView(chatScroll, new LinearLayout.LayoutParams(-1, 0, 1)); renderSavedChat();
        attachmentStrip = horizontal(); HorizontalScrollView hs = new HorizontalScrollView(this); hs.addView(attachmentStrip, full()); content.addView(hs, full()); renderAttachments();
        LinearLayout composer = horizontal(); composer.setGravity(Gravity.CENTER_VERTICAL); Button plus = button("+"); chatComposer = input("Message JANUS"); chatComposer.setSingleLine(false); chatComposer.setMaxLines(4); Button send = button("Send"); plus.setOnClickListener(v -> pickFile()); send.setOnClickListener(v -> { String m = chatComposer.getText().toString().trim(); if (m.isEmpty() && attachments.isEmpty()) return; if (m.isEmpty()) m = "Please assess the attached file or files."; chatComposer.setText(""); sendChat(m); }); composer.addView(plus, new LinearLayout.LayoutParams(dp(52), dp(58))); composer.addView(chatComposer, new LinearLayout.LayoutParams(0, dp(58), 1)); composer.addView(send, new LinearLayout.LayoutParams(dp(82), dp(58))); content.addView(composer, full()); drainQueuedReplies();
    }

    private void sendChat(String message) {
        List<Attachment> files = new ArrayList<>(attachments); attachments.clear(); renderAttachments(); String clientId = "android-" + UUID.randomUUID();
        addBubble("You", message + (files.isEmpty() ? "" : "\n\nAttachments: " + attachmentNames(files)), true, true, null); status.setText("JANUS is responding…");
        try { JanusLocalCoreRuntime.get(this).ingestUserMessage(message); } catch (Exception ignored) {}
        JSONObject body = new JSONObject();
        try { body.put("profile_id", profile); body.put("message", message); body.put("client_message_id", clientId); JSONArray ids = new JSONArray(); for (Attachment a : files) ids.put(a.id); body.put("attachment_ids", ids); try { body.put("local_runtime_evidence", JanusLocalCoreRuntime.get(this).statusJson().toString()); } catch (Exception ignored) {} } catch (Exception ignored) {}
        final String prepared = JanusOfflineQueue.prepareChatBody(body.toString());
        io.execute(() -> {
            JanusChatController.Result outcome = JanusChatController.send(api, prepared);
            JanusApiClient.Response result = outcome.response == null ? new JanusApiClient.Response(0, "", "No response") : outcome.response;
            if (!outcome.ok()) {
                if (outcome.retryable) { int pending = JanusOfflineQueue.enqueue(this, prepared); main.post(() -> { addBubble("System", "The server connection did not complete. This message is saved on this device and will retry automatically. Queued: " + pending + ".", false, true, null); status.setText("Offline queue active"); }); }
                else if (outcome.authExpired) main.post(() -> { toast("Your JANUS session expired. Please sign in again."); api.clearSession(); profile = ""; showAuth(); });
                else main.post(() -> { addBubble("System", readableError(result), false, true, null); status.setText("Interface active"); });
                return;
            }
            JanusChatPresentation presentation = outcome.presentation == null ? JanusChatPresentation.fromResponse(new JSONObject(), result.body) : outcome.presentation;
            String reply = presentation.reply;
            try { JanusLocalCoreRuntime.get(this).ingestServerReply(reply); } catch (Exception ignored) {}
            main.post(() -> {
                JanusChatResponseRegistry.remember(presentation);
                addBubble("JANUS", reply, false, false, reply);
                JanusChatHistoryStore.append(this, "JANUS", reply, presentation);
                status.setText("Interface active");
            });
            if (presentation.generatedImage != null) {
                String fileId = presentation.generatedImage.optString("file_id", "");
                if (!fileId.isBlank()) loadGeneratedImage(fileId);
            }
        });
    }

    private void addBubble(String who, String body, boolean user, boolean persist, String reportText) {
        if (chatLog == null) return; LinearLayout box = vertical(); box.setPadding(dp(14), dp(10), dp(14), dp(10)); box.setBackgroundColor(user ? userColor() : surfaceColor()); box.addView(text(who, 13, true), full()); box.addView(text(body, 16, false), full());
        if ("JANUS".equals(who) && reportText != null && !reportText.isBlank()) { Button report = button("Report response"); report.setOnClickListener(v -> promptReport(reportText)); box.addView(report, wrap()); }
        LinearLayout.LayoutParams lp = full(); lp.setMargins(user ? dp(48) : 0, dp(5), user ? 0 : dp(28), dp(5)); chatLog.addView(box, lp); chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN)); if (persist) rememberChat(who, body);
    }

    private void rememberChat(String who, String body) {
        JanusChatPresentation presentation = "JANUS".equals(who) ? JanusChatResponseRegistry.findForReply(body) : null;
        JanusChatHistoryStore.append(this, who, body, presentation);
    }

    private void renderSavedChat() {
        try {
            JSONArray a = JanusChatHistoryStore.read(this);
            for (int i = 0; i < a.length(); i++) {
                JSONObject x = a.optJSONObject(i); if (x == null) continue;
                String who = x.optString("who", "JANUS"); String body = x.optString("body", "");
                JSONObject stored = x.optJSONObject("presentation");
                if (stored != null && "JANUS".equals(who)) { JanusChatPresentation p = JanusChatPresentation.fromStored(stored); JanusChatResponseRegistry.remember(p); body = p.reply; }
                addBubble(who, body, "You".equals(who), false, null);
            }
        } catch (Exception ignored) {}
    }

    private void drainQueuedReplies() {
        try { JSONArray a = new JSONArray(JanusOfflineQueue.drainReplies(this)); for (int i = 0; i < a.length(); i++) { JSONObject x = a.optJSONObject(i); if (x != null) addBubble("JANUS", x.optString("reply", "") + "\n\n[Delivered from the offline queue]", false, true, x.optString("reply", "")); } } catch (Exception ignored) {}
    }

    private String formatResearchSources(JSONArray sources) {
        if (sources == null || sources.length() == 0) return ""; StringBuilder b = new StringBuilder("\n\nSources:");
        for (int i = 0; i < Math.min(8, sources.length()); i++) { Object raw = sources.opt(i); if (raw instanceof JSONObject) { JSONObject s = (JSONObject) raw; b.append("\n• ").append(s.optString("title", s.optString("url", "Source"))); String url = s.optString("url", ""); if (!url.isBlank()) b.append(" — ").append(url); } else if (raw != null) b.append("\n• ").append(String.valueOf(raw)); }
        return b.toString();
    }

    private void promptReport(String responseText) { LinearLayout box = vertical(); EditText category = input("Category: harmful, harassment, sexual, hate, self-harm, illegal, privacy, misinformation, other"); EditText details = input("Optional details"); box.addView(category, full()); box.addView(details, full()); new AlertDialog.Builder(this).setTitle("Report JANUS response").setView(box).setPositiveButton("Submit", (d, w) -> { JSONObject body = new JSONObject(); try { body.put("category", category.getText().toString().trim().isEmpty() ? "other" : category.getText().toString().trim().toLowerCase(Locale.ROOT)); body.put("response_text", responseText); body.put("details", details.getText().toString().trim()); } catch (Exception ignored) {} backgroundAction("/safety/report", body, true, "Report submitted."); }).setNegativeButton("Cancel", null).show(); }

    private void loadGeneratedImage(String fileId) { io.execute(() -> { JanusApiClient.Response r = api.get("/images/" + enc(fileId) + "/inline", true); if (!r.ok()) return; try { JSONObject j = new JSONObject(r.body); byte[] bytes = Base64.decode(j.optString("data_base64", ""), Base64.DEFAULT); Bitmap bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length); if (bitmap == null) return; main.post(() -> { if (chatLog == null) return; ImageView image = new ImageView(this); image.setAdjustViewBounds(true); image.setImageBitmap(bitmap); LinearLayout.LayoutParams lp = full(); lp.setMargins(0, dp(6), dp(28), dp(8)); chatLog.addView(image, lp); chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN)); }); } catch (Exception ignored) {} }); }

    private void pickFile() { if (attachments.size() >= MAX_ATTACHMENTS) { toast("Up to four files can be attached to one Chat turn."); return; } Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.addCategory(Intent.CATEGORY_OPENABLE); i.setType("*/*"); startActivityForResult(i, RC_FILE); }
    private void uploadFile(Uri uri) { if (status != null) status.setText("Uploading attachment…"); io.execute(() -> { try { byte[] bytes = readFile(uri); String name = fileName(uri); String mime = getContentResolver().getType(uri); if (mime == null || mime.isBlank()) mime = "application/octet-stream"; JSONObject body = new JSONObject(); body.put("filename", name); body.put("mime_type", mime); body.put("data_base64", Base64.encodeToString(bytes, Base64.NO_WRAP)); JanusApiClient.Response r = api.post("/files/upload", body.toString(), true); if (!r.ok()) { main.post(() -> status.setText("Attachment failed · " + readableError(r))); return; } JSONObject f = new JSONObject(r.body).optJSONObject("file"); if (f == null) throw new IllegalStateException("Server did not return a file record"); Attachment a = new Attachment(f.optString("id"), f.optString("filename", name)); main.post(() -> { attachments.add(a); renderAttachments(); if (status != null) status.setText("Attachment ready"); }); } catch (Exception e) { main.post(() -> { if (status != null) status.setText("Attachment failed · " + e.getMessage()); }); } }); }
    private void renderAttachments() { if (attachmentStrip == null) return; attachmentStrip.removeAllViews(); for (Attachment a : new ArrayList<>(attachments)) { Button chip = button("× " + a.name); chip.setOnClickListener(v -> { attachments.removeIf(x -> x.id.equals(a.id)); renderAttachments(); }); attachmentStrip.addView(chip, wrap()); } }
    private byte[] readFile(Uri uri) throws Exception { try (InputStream in = getContentResolver().openInputStream(uri); ByteArrayOutputStream out = new ByteArrayOutputStream()) { if (in == null) throw new IllegalArgumentException("File could not be opened"); byte[] buf = new byte[32768]; int n, total = 0; while ((n = in.read(buf)) >= 0) { total += n; if (total > MAX_FILE_BYTES) throw new IllegalArgumentException("File exceeds 8 MB"); out.write(buf, 0, n); } if (total == 0) throw new IllegalArgumentException("Empty files are not supported"); return out.toByteArray(); } }
    private String fileName(Uri uri) { String out = "attachment"; try (Cursor c = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) { if (c != null && c.moveToFirst()) { String s = c.getString(0); if (s != null && !s.isBlank()) out = s; } } catch (Exception ignored) {} return out; }
    private String attachmentNames(List<Attachment> files) { StringBuilder b = new StringBuilder(); for (int i = 0; i < files.size(); i++) { if (i > 0) b.append(", "); b.append(files.get(i).name); } return b.toString(); }

    private void showMessages() { content.addView(text(JanusUiLocalizationPolish.shellText(this, "Messages"), 28, true), full()); content.addView(text("Useful JANUS-originated questions, conclusions, warnings and follow-ups. Routine internal processing belongs in Observe.", 13, false), full()); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1)); Button refresh = button("Refresh"); refresh.setOnClickListener(v -> loadMessages(list)); content.addView(refresh, full()); loadMessages(list); }
    private void loadMessages(LinearLayout list) { list.removeAllViews(); list.addView(text("Loading…", 14, false)); io.execute(() -> { JanusApiClient.Response r = api.get("/desktop/messages?username=" + enc(profile) + "&limit=80", true); main.post(() -> { list.removeAllViews(); if (!r.ok()) { list.addView(text(readableError(r), 14, false)); return; } try { JSONObject j = new JSONObject(r.body); JSONArray items = j.optJSONArray("items"); if (items == null || items.length() == 0) { list.addView(text("No JANUS messages yet.", 15, false)); return; } for (int i = 0; i < items.length(); i++) { JSONObject x = items.getJSONObject(i); long id = x.optLong("id", 0); String detail = x.optString("detail", x.optString("message", "")); LinearLayout card = card(); card.addView(text(("unread".equals(x.optString("state")) ? "New · " : "") + x.optString("message_type", "Message"), 14, true)); card.addView(text(formatTime(x.opt("created_at")), 12, false)); card.addView(text(detail, 15, false)); LinearLayout actions = horizontal(); Button answer = button("Answer in Chat"); Button read = button("Read"); Button dismiss = button("Dismiss"); answer.setOnClickListener(v -> { setMessageState(id, "read"); showPage("Chat"); if (chatComposer != null) { chatComposer.setText("Regarding your message:\n“" + clip(detail, 500) + "”\n\n"); chatComposer.requestFocus(); } }); read.setOnClickListener(v -> { setMessageState(id, "read"); loadMessages(list); }); dismiss.setOnClickListener(v -> { setMessageState(id, "dismissed"); loadMessages(list); }); actions.addView(answer, weight()); actions.addView(read, weight()); actions.addView(dismiss, weight()); card.addView(actions, full()); list.addView(card, full()); } } catch (Exception e) { list.addView(text("Messages could not be displayed.", 14, false)); } }); }); }
    private void setMessageState(long id, String state) { if (id <= 0) return; io.execute(() -> { JSONObject body = new JSONObject(); try { body.put("profile_id", profile); body.put("state", state); } catch (Exception ignored) {} api.post("/desktop/messages/" + id + "/state", body.toString(), true); }); }

    private void showObserve() { content.addView(text(JanusUiLocalizationPolish.shellText(this, "Observe"), 28, true), full()); content.addView(text("Readable externalizable JANUS process activity. This screen is a stable snapshot and does not auto-jump while you read it.", 13, false), full()); LinearLayout filters = horizontal(); for (String mode : new String[]{"all", "thoughts", "interactions"}) { Button b = button(mode.equals("all") ? "All" : capitalize(mode)); b.setOnClickListener(v -> { observeMode = mode; showObserve(); }); filters.addView(b, weight()); } content.addView(filters, full()); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1)); Button refresh = button("Refresh snapshot"); refresh.setOnClickListener(v -> loadObserve(list)); content.addView(refresh, full()); loadObserve(list); }
    private void loadObserve(LinearLayout list) { list.removeAllViews(); list.addView(text("Loading local and global core activity…", 14, false)); io.execute(() -> { JSONArray localItems = new JSONArray(); try { JSONObject local = JanusLocalCoreRuntime.get(this).statusJson(); JSONArray ev = local.optJSONArray("observe_events"); if (ev != null) localItems = ev; } catch (Exception ignored) {} JanusApiClient.Response server = api.get("/desktop/core-observe?username=" + enc(profile) + "&mode=" + enc(observeMode) + "&limit=180", true); JSONArray serverItems = new JSONArray(); if (server.ok()) try { JSONArray a = new JSONObject(server.body).optJSONArray("items"); if (a != null) serverItems = a; } catch (Exception ignored) {} final JSONArray localFinal = localItems; final JSONArray serverFinal = serverItems; main.post(() -> { list.removeAllViews(); int shown = 0; for (int i = localFinal.length() - 1; i >= 0 && shown < 80; i--) { JSONObject x = localFinal.optJSONObject(i); if (x == null || !observeMatches(x)) continue; addObserveCard(list, x, "This device"); shown++; } for (int i = 0; i < serverFinal.length() && shown < 160; i++) { JSONObject x = serverFinal.optJSONObject(i); if (x == null || !observeMatches(x)) continue; addObserveCard(list, x, x.optString("source", "Global JANUS")); shown++; } if (shown == 0) list.addView(text("No observable core activity in this snapshot.", 15, false)); }); }); }
    private boolean observeMatches(JSONObject x) { if ("all".equals(observeMode)) return true; String type = x.optString("event_type", "").toLowerCase(Locale.ROOT); if ("interactions".equals(observeMode)) return type.contains("interaction"); return !type.contains("interaction"); }
    private void addObserveCard(LinearLayout list, JSONObject x, String source) { LinearLayout card = card(); String core = prettyName(x.optString("core_name", "core")); String peer = x.optString("peer_core", ""); String route = peer.isEmpty() ? core : core + " → " + prettyName(peer); card.addView(text(route + " · " + prettyName(x.optString("event_type", "note")), 13, true)); card.addView(text(x.optString("detail", x.optString("summary", "")), 15, false)); card.addView(text(formatTime(x.opt("created_at")) + " · " + source, 12, false)); String raw = x.optString("raw_detail", ""); if (!raw.isBlank() && !raw.equals(x.optString("detail", ""))) { Button tech = button("Technical details"); tech.setOnClickListener(v -> new AlertDialog.Builder(this).setTitle(route).setMessage(raw).setPositiveButton("Close", null).show()); card.addView(tech, wrap()); } list.addView(card, full()); }

    private void showOptions() { content.addView(text(JanusBuildInfo.pageLabel("Options"), 28, true), full()); ScrollView scroll = new ScrollView(this); LinearLayout list = vertical(); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1)); option(list, "Cores", "11 live cores: 7 specialists → 2 hemispheres → Front → Interface", this::showCores); option(list, "Memory", "Trace → working → episodic → core, plus device-local continuity", this::showMemory); option(list, "Activity", "Conversation, reflections, decisions and durable events", this::showActivity); option(list, "System status", "Healthy / Reduced capability / Needs attention diagnostics", this::showSystemStatus); option(list, "Compatibility", "Deployed protocol and capability negotiation", this::showCompatibility); option(list, "Research workspace", "Established results, hypotheses, negative results, open questions and proposed tests", this::showResearch); option(list, "Artifacts", "Continuity reports, research digests and working files", this::showArtifacts); option(list, "Background research", "Sources, provenance, suppression reasons and external-compute estimates", this::showBackgroundResearch); option(list, "Maintenance review", "Owner-gated quarterly proposals: approve, defer or reject", this::showMaintenance); option(list, "Settings", "Themes, background/sleep controls and Observe telemetry", this::showSettings); option(list, "Account", "Profile, verification, sign out and account lifecycle", this::showAccount); }
    private void option(LinearLayout list, String title, String subtitle, Runnable action) { Button b = button(title + "\n" + subtitle); b.setGravity(Gravity.START | Gravity.CENTER_VERTICAL); b.setOnClickListener(v -> { b.setEnabled(false); main.post(() -> { try { action.run(); } catch (Throwable failure) { showOptionFailure(title, failure); } }); }); list.addView(b, full()); }
    private void showOptionFailure(String title, Throwable failure) { try { content.removeAllViews(); Button back = button("← Options"); back.setOnClickListener(v -> showPage("Options")); content.addView(back, full()); content.addView(text(title, 28, true), full()); content.addView(text("This screen could not be opened safely. JANUS kept the app running instead of closing.\n\n" + failure.getClass().getSimpleName() + (failure.getMessage() == null ? "" : ": " + clip(failure.getMessage(), 500)), 14, false), full()); } catch (Throwable ignored) { toast("That JANUS screen could not be opened safely."); } }
    private void detailHeader(String title) { resetContentSurface(); Button back = button("← Options"); back.setOnClickListener(v -> showPage("Options")); content.addView(back, full()); content.addView(text(title, 28, true), full()); }

    private void showCores() { detailHeader("Runtime Cores"); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1)); list.addView(text("Loading local and global JANUS runtimes…", 14, false)); io.execute(() -> { JSONObject local = new JSONObject(); try { local = JanusLocalCoreRuntime.get(this).statusJson(); } catch (Exception ignored) {} JanusApiClient.Response r = api.get("/desktop/runtime-cores?username=" + enc(profile), true); JSONObject server = new JSONObject(); if (r.ok()) try { JSONObject j = new JSONObject(r.body); server = j.optJSONObject("runtime"); if (server == null) server = j; } catch (Exception ignored) {} final JSONObject lf = local, sf = server; main.post(() -> { list.removeAllViews(); renderRuntime(list, "THIS DEVICE · LOCAL JANUS", lf); renderRuntime(list, "ONLINE · GLOBAL JANUS", sf); }); }); }
    private void renderRuntime(LinearLayout list, String title, JSONObject rt) { LinearLayout summary = card(); summary.addView(text(title, 15, true)); summary.addView(text("Topology: " + rt.optString("topology", "7 → 2 → 1 → 1") + "\nPhase: " + rt.optString("phase", "unknown") + "\nSync: " + rt.optString("sync_state", "unknown"), 13, false)); list.addView(summary, full()); JSONObject cores = rt.optJSONObject("cores"); if (cores == null) return; for (String name : CORE_NAMES) { JSONObject c = cores.optJSONObject(name); if (c == null) continue; LinearLayout card = card(); card.addView(text(prettyName(name), 14, true)); card.addView(text("Mode: " + c.optString("processing_mode", c.optBoolean("awake", false) ? "active" : "resting") + " · cycles " + c.optLong("cycle_count", 0) + " · pending " + c.optInt("pending_messages", 0), 12, false)); String out = c.optString("last_output", ""); if (!out.isBlank()) card.addView(text(out, 14, false)); JSONObject fano = c.optJSONObject("fano"); if (fano != null) card.addView(text("Fano direction d" + fano.optInt("active_direction", 0) + " · processing bias only, not a truth oracle", 12, false)); list.addView(card, full()); } }
    private void showMemory() { detailHeader("Memory"); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1)); list.addView(text("Loading continuity memory…", 14, false)); io.execute(() -> { JSONArray local = new JSONArray(); try { JSONArray a = JanusLocalCoreRuntime.get(this).statusJson().optJSONArray("local_memories"); if (a != null) local = a; } catch (Exception ignored) {} JanusApiClient.Response r = api.get("/desktop/memory?username=" + enc(profile), true); JSONArray server = new JSONArray(); if (r.ok()) try { JSONArray a = new JSONObject(r.body).optJSONArray("items"); if (a != null) server = a; } catch (Exception ignored) {} final JSONArray lf = local, sf = server; main.post(() -> { list.removeAllViews(); list.addView(text("Device-local continuity", 16, true)); for (int i = lf.length()-1; i >= 0 && i >= lf.length()-40; i--) list.addView(text(lf.optString(i), 14, false), full()); list.addView(text("Server continuity", 16, true)); for (int i = 0; i < sf.length(); i++) { JSONObject x = sf.optJSONObject(i); if (x == null) continue; LinearLayout c = card(); c.addView(text(x.optString("level", "trace") + " · " + x.optString("role", "memory"), 13, true)); c.addView(text(x.optString("content", ""), 14, false)); list.addView(c, full()); } }); }); }
    private void showActivity() { showJsonListScreen("Activity", "/desktop/activity?username=" + enc(profile), "items", "event_type", "detail"); }
    private void showSystemStatus() { detailHeader("System Status"); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1)); list.addView(text("Checking JANUS health…", 14, false)); io.execute(() -> { JanusApiClient.Response r = api.get("/diagnostics/runtime-health", false); JSONObject local = new JSONObject(); try { local = JanusLocalCoreRuntime.get(this).statusJson(); } catch (Exception ignored) {} final JSONObject lf = local; main.post(() -> { list.removeAllViews(); if (!r.ok()) { list.addView(statusCard("Needs attention", "The JANUS server health endpoint is unavailable. Local JANUS remains " + lf.optString("phase", "available") + ".")); return; } try { JSONObject j = new JSONObject(r.body); boolean healthy = "ok".equalsIgnoreCase(j.optString("status")) && j.optBoolean("database_ok", true) && j.optBoolean("auth_schema_ok", true) && j.optBoolean("core_persistence_ok", true); String label = healthy ? "Healthy" : (j.optBoolean("main_app_loaded", true) ? "Reduced capability" : "Needs attention"); String detail = "Server: " + j.optString("status", "unknown") + "\nDatabase: " + yesNo(j.optBoolean("database_ok", false)) + "\nAuth schema: " + yesNo(j.optBoolean("auth_schema_ok", false)) + "\nCore persistence: " + yesNo(j.optBoolean("core_persistence_ok", false)) + "\nServer phase: " + j.optString("core_phase", "unknown") + "\nLocal phase: " + lf.optString("phase", "unknown") + "\nLocal sync: " + lf.optString("sync_state", "unknown"); list.addView(statusCard(label, detail)); } catch (Exception e) { list.addView(statusCard("Reduced capability", r.body)); } }); }); }
    private LinearLayout statusCard(String title, String body) { LinearLayout c = card(); c.addView(text(title, 20, true)); c.addView(text(body, 14, false)); return c; }
    private void showCompatibility() { detailHeader("Compatibility"); TextView body = text("Checking deployed server capabilities…", 14, false); ScrollView scroll = new ScrollView(this); scroll.addView(body, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1)); io.execute(() -> { JanusApiClient.Response r = api.get("/protocol/capabilities", false); String out = r.ok() ? humanCapabilities(r.body) : readableError(r); main.post(() -> body.setText(out)); }); }
    private String humanCapabilities(String raw) { try { JSONObject j = new JSONObject(raw); StringBuilder b = new StringBuilder(); b.append("Server protocol: ").append(j.optInt("protocol_version", 0)).append("\nDeployed commit: ").append(j.optString("deployed_commit", "unknown")).append("\n\nCapabilities\n"); JSONObject f = j.optJSONObject("features"); if (f != null) { JSONArray names = f.names(); if (names != null) for (int i = 0; i < names.length(); i++) { String n = names.optString(i); b.append(f.optBoolean(n, false) ? "✓ " : "— ").append(prettyName(n)).append('\n'); } } return b.toString(); } catch (Exception e) { return raw; } }

    private void showResearch() { detailHeader("Research Workspace"); LinearLayout controls = horizontal(); Button seed = button("Load JANUS baseline"); Button digest = button("Create digest"); controls.addView(seed, weight()); controls.addView(digest, weight()); content.addView(controls, full()); LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1)); seed.setOnClickListener(v -> { backgroundAction("/research/workspace/seed", new JSONObject(), true, "Research baseline loaded."); loadResearch(list); }); digest.setOnClickListener(v -> createArtifact("research_digest", () -> loadResearch(list))); loadResearch(list); }
    private void loadResearch(LinearLayout list) { list.removeAllViews(); list.addView(text("Loading research ledger…", 14, false)); io.execute(() -> { JanusApiClient.Response r = api.get("/research/workspace", true); main.post(() -> { list.removeAllViews(); if (!r.ok()) { list.addView(text(readableError(r),14,false)); return; } try { JSONObject j = new JSONObject(r.body); JSONArray claims = j.optJSONArray("claims"); if (claims == null) claims = j.optJSONArray("items"); if (claims == null || claims.length()==0) { list.addView(text("No research records yet.",14,false)); return; } Map<String, LinearLayout> groups = new LinkedHashMap<>(); for (String g : new String[]{"ESTABLISHED / AUDITED", "HYPOTHESES / PROVISIONAL", "NEGATIVE RESULTS", "OPEN QUESTIONS", "PROPOSED TESTS", "OTHER"}) { LinearLayout section = vertical(); section.addView(text(g,16,true)); groups.put(g, section); list.addView(section, full()); } for (int i=0;i<claims.length();i++) { JSONObject c=claims.optJSONObject(i); if(c==null)continue; String kind=c.optString("claim_kind",""); String state=c.optString("epistemic_state",""); String group=researchGroup(kind,state); LinearLayout card=card(); card.addView(text(c.optString("title","Untitled research item"),15,true)); card.addView(text(prettyName(kind)+" · "+prettyName(state)+" · "+c.optString("domain","general"),12,false)); card.addView(text(c.optString("statement",""),14,false)); JSONArray evidence=c.optJSONArray("evidence"); if(evidence!=null&&evidence.length()>0) card.addView(text("Evidence entries: "+evidence.length(),12,false)); Button discuss=button("Discuss in Chat"); String title=c.optString("title","this research item"); discuss.setOnClickListener(v->{showPage("Chat");if(chatComposer!=null){chatComposer.setText("Please continue our research on \""+title.replace("\"","")+"\". Preserve its current epistemic status and distinguish established evidence from interpretation.");chatComposer.requestFocus();}}); card.addView(discuss,wrap()); groups.get(group).addView(card,full()); } } catch(Exception e){list.addView(text("Research workspace could not be displayed.",14,false));} }); }); }
    private String researchGroup(String kind,String state){ if("negative_result".equals(kind)||"closed_negative".equals(state)||"contradicted".equals(state)||"falsified".equals(state))return"NEGATIVE RESULTS"; if("open_question".equals(kind)||"open".equals(state))return"OPEN QUESTIONS"; if("proposed_test".equals(kind))return"PROPOSED TESTS"; if("hypothesis".equals(kind)||"interpretation".equals(kind)||"provisional".equals(state)||"untested".equals(state)||"inconclusive".equals(state))return"HYPOTHESES / PROVISIONAL"; if("established".equals(state)||"audited".equals(state)||"supported".equals(state))return"ESTABLISHED / AUDITED"; return"OTHER"; }

    private void showArtifacts() { detailHeader("Artifacts"); LinearLayout controls=horizontal(); Button continuity=button("Continuity report"); Button digest=button("Research digest"); Button note=button("Working note"); controls.addView(continuity,weight());controls.addView(digest,weight());controls.addView(note,weight());content.addView(controls,full()); LinearLayout list=vertical();ScrollView scroll=new ScrollView(this);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1)); continuity.setOnClickListener(v->createArtifact("continuity_report",()->loadArtifacts(list))); digest.setOnClickListener(v->createArtifact("research_digest",()->loadArtifacts(list))); note.setOnClickListener(v->createArtifact("working_note",()->loadArtifacts(list))); loadArtifacts(list); }
    private void createArtifact(String kind,Runnable done){ io.execute(()->{ JSONObject body=new JSONObject();try{body.put("kind",kind);}catch(Exception ignored){} JanusApiClient.Response r=api.post("/artifacts",body.toString(),true); main.post(()->{toast(r.ok()?"Artifact created.":"Artifact creation failed · "+readableError(r));if(done!=null)done.run();}); }); }
    private void loadArtifacts(LinearLayout list){ list.removeAllViews();list.addView(text("Loading artifacts…",14,false)); io.execute(()->{ JanusApiClient.Response r=api.get("/artifacts",true); main.post(()->{ list.removeAllViews();if(!r.ok()){list.addView(text(readableError(r),14,false));return;} try{JSONArray items=new JSONObject(r.body).optJSONArray("items");if(items==null||items.length()==0){list.addView(text("No generated artifacts yet.",14,false));return;} for(int i=0;i<items.length();i++){JSONObject a=items.optJSONObject(i);if(a==null)continue;long id=a.optLong("id",0);LinearLayout card=card();card.addView(text(a.optString("title",prettyName(a.optString("kind","artifact"))),15,true));card.addView(text(prettyName(a.optString("kind","artifact"))+" · "+formatTime(a.opt("created_at")),12,false));LinearLayout actions=horizontal();Button open=button("Open");Button export=button("Export");Button share=button("Share");open.setOnClickListener(v->showArtifactDetail(id));export.setOnClickListener(v->prepareArtifactAction(id,false));share.setOnClickListener(v->prepareArtifactAction(id,true));actions.addView(open,weight());actions.addView(export,weight());actions.addView(share,weight());card.addView(actions,full());list.addView(card,full());} }catch(Exception e){list.addView(text("Artifacts could not be displayed.",14,false));} }); }); }
    private void showArtifactDetail(long id){ detailHeader("Artifact");TextView body=text("Loading…",14,false);ScrollView scroll=new ScrollView(this);scroll.addView(body,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1)); io.execute(()->{JanusApiClient.Response r=api.get("/artifacts/"+id,true);String out=r.ok()?prettyJson(r.body):readableError(r);main.post(()->body.setText(out));}); }
    private void prepareArtifactAction(long id,boolean share){ io.execute(()->{ JanusApiClient.Response r=api.get("/artifacts/"+id,true);if(!r.ok()){main.post(()->toast(readableError(r)));return;} try{JSONObject a=new JSONObject(r.body).optJSONObject("artifact");if(a==null)a=new JSONObject(r.body);String fileId=a.optString("file_id","");String name=a.optString("original_name",a.optString("title","JANUS-artifact.md"));String mime=a.optString("mime_type","application/octet-stream");if(fileId.isBlank())throw new IllegalStateException("Artifact file is unavailable");if(share)shareArtifact(fileId,name,mime);else main.post(()->startArtifactExport(fileId,name,mime));} catch(Exception e){main.post(()->toast("Artifact unavailable · "+e.getMessage()));} }); }
    private void startArtifactExport(String fileId,String name,String mime){ pendingExportFileId=fileId;pendingExportName=safeName(name);pendingExportMime=mime==null||mime.isBlank()?"application/octet-stream":mime; Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(pendingExportMime);i.putExtra(Intent.EXTRA_TITLE,pendingExportName);startActivityForResult(i,RC_EXPORT); }
    private void finishArtifactExport(Uri destination){ String fileId=pendingExportFileId;io.execute(()->{try{byte[] bytes=api.download("/files/"+enc(fileId)+"/download",true);try(java.io.OutputStream out=getContentResolver().openOutputStream(destination,"w")){if(out==null)throw new IllegalStateException("Could not open destination");out.write(bytes);}main.post(()->toast("Artifact exported."));}catch(Exception e){main.post(()->toast("Export failed · "+e.getMessage()));}}); }
    private void shareArtifact(String fileId,String name,String mime){ io.execute(()->{try{byte[] bytes=api.download("/files/"+enc(fileId)+"/download",true);File dir=new File(getCacheDir(),"shared_artifacts");if(!dir.exists()&&!dir.mkdirs())throw new IllegalStateException("Could not prepare share cache");File file=new File(dir,safeName(name));try(FileOutputStream out=new FileOutputStream(file)){out.write(bytes);}Uri uri=FileProvider.getUriForFile(this,getPackageName()+".fileprovider",file);main.post(()->{Intent send=new Intent(Intent.ACTION_SEND);send.setType(mime==null||mime.isBlank()?"application/octet-stream":mime);send.putExtra(Intent.EXTRA_STREAM,uri);send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(send,"Share JANUS artifact"));});}catch(Exception e){main.post(()->toast("Share failed · "+e.getMessage()));}}); }

    private void showBackgroundResearch(){ detailHeader("Background Research");LinearLayout list=vertical();ScrollView scroll=new ScrollView(this);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));list.addView(text("Loading provenance…",14,false)); io.execute(()->{JanusApiClient.Response r=api.get("/research-provenance/status?limit=40",true);main.post(()->{list.removeAllViews();if(!r.ok()){list.addView(text(readableError(r),14,false));return;}try{JSONObject j=new JSONObject(r.body);JSONObject u=j.optJSONObject("usefulness");JSONObject c=j.optJSONObject("external_compute");LinearLayout summary=card();summary.addView(text("Research provenance",16,true));if(u!=null)summary.addView(text("Useful completed: "+u.optInt("useful",0)+" / "+u.optInt("completed_scored",0)+" · usefulness rate "+Math.round(u.optDouble("usefulness_rate",0)*100)+"%",13,false));if(c!=null)summary.addView(text("Estimated background external compute today: $"+String.format(Locale.US,"%.4f",c.optDouble("background_today_estimated_usd",0))+" · denied by cost governor: "+c.optInt("denied_today",0)+"\nCosts are planning estimates, not provider invoices. Background core image generation remains disabled.",13,false));list.addView(summary,full());JSONArray searches=j.optJSONArray("recent_searches");if(searches!=null)for(int i=0;i<searches.length();i++){JSONObject x=searches.optJSONObject(i);if(x==null)continue;LinearLayout card=card();card.addView(text(x.optString("query","Background research"),14,true));card.addView(text(x.optString("result_preview",""),14,false));JSONArray sources=x.optJSONArray("sources");if(sources!=null)card.addView(text(formatResearchSources(sources).replaceFirst("\\n\\nSources:","Sources:"),12,false));list.addView(card,full());}}catch(Exception e){list.addView(text(prettyJson(r.body),13,false));}});}); }

    private void showMaintenance(){ detailHeader("Maintenance Review");content.addView(text("JANUS may propose maintenance, but approval only permits manual human/ChatGPT-assisted work. It never authorizes JANUS to edit code, install packages, change models/APIs or deploy itself.",13,false),full());LinearLayout list=vertical();ScrollView scroll=new ScrollView(this);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));loadMaintenance(list); }
    private void loadMaintenance(LinearLayout list){ list.removeAllViews();list.addView(text("Loading maintenance proposals…",14,false));io.execute(()->{JanusApiClient.Response r=api.get("/maintenance/status",true);main.post(()->{list.removeAllViews();if(!r.ok()){list.addView(text(readableError(r),14,false));return;}try{JSONObject j=new JSONObject(r.body);JSONObject m=j.optJSONObject("maintenance");if(m!=null){LinearLayout c=card();c.addView(text("Quarterly maintenance",16,true));c.addView(text("Enabled: "+yesNo(m.optBoolean("enabled",false))+" · interval "+m.optInt("interval_days",90)+" days · "+(m.optBoolean("due",false)?"review due":"not currently due"),13,false));list.addView(c,full());}JSONArray reviews=j.optJSONArray("reviews");if(reviews==null||reviews.length()==0){list.addView(text("No maintenance proposals yet.",14,false));return;}for(int i=0;i<reviews.length();i++){JSONObject x=reviews.optJSONObject(i);if(x==null)continue;long id=x.optLong("id",0);String state=x.optString("review_state","awaiting_owner_review");JSONObject report=x.optJSONObject("report");LinearLayout card=card();card.addView(text(report==null?"Maintenance proposal":prettyName(report.optString("proposal_kind","maintenance review")),15,true));card.addView(text("State: "+prettyName(state),13,false));if(report!=null)card.addView(text(prettyJson(report.toString()),12,false));if("awaiting_owner_review".equals(state)&&id>0){LinearLayout actions=horizontal();Button approve=button("Approve");Button defer=button("Defer");Button reject=button("Reject");approve.setOnClickListener(v->maintenanceDecision(id,"approved_for_manual_work",list));defer.setOnClickListener(v->maintenanceDecision(id,"deferred",list));reject.setOnClickListener(v->maintenanceDecision(id,"rejected",list));actions.addView(approve,weight());actions.addView(defer,weight());actions.addView(reject,weight());card.addView(actions,full());}list.addView(card,full());}}catch(Exception e){list.addView(text(prettyJson(r.body),13,false));}});}); }
    private void maintenanceDecision(long id,String decision,LinearLayout list){ new AlertDialog.Builder(this).setTitle("Confirm maintenance decision").setMessage(prettyName(decision)+"? No automatic changes will be made.").setPositiveButton("Confirm",(d,w)->{io.execute(()->{JSONObject body=new JSONObject();try{body.put("decision",decision);}catch(Exception ignored){}JanusApiClient.Response r=api.post("/maintenance/reviews/"+id+"/decision",body.toString(),true);main.post(()->{toast(r.ok()?"Decision recorded.":readableError(r));loadMaintenance(list);});});}).setNegativeButton("Cancel",null).show(); }

    private void showSettings(){ detailHeader("Settings");ScrollView scroll=new ScrollView(this);LinearLayout list=vertical();scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1)); LinearLayout theme=card();theme.addView(text("Appearance",16,true));LinearLayout modes=horizontal();for(String mode:new String[]{"system","light","dark"}){Button b=button(capitalize(mode));b.setOnClickListener(v->{prefs().edit().putString("theme_mode",mode).apply();recreate();});modes.addView(b,weight());}theme.addView(modes,full());theme.addView(text("Accent",14,true));LinearLayout accents=horizontal();for(String accent:new String[]{"slate","indigo","teal","amber","violet"}){Button b=button(capitalize(accent));b.setOnClickListener(v->{prefs().edit().putString("accent",accent).apply();recreate();});accents.addView(b,weight());}theme.addView(accents,full());list.addView(theme,full()); JanusLanguagePolish.renderSettingsCard(this,list); LinearLayout runtime=card();runtime.addView(text("Local JANUS background operation",16,true));Switch bg=new Switch(this);bg.setText("Background wake cycles");bg.setChecked(prefs().getBoolean("background_cycles_enabled",true));bg.setOnCheckedChangeListener((b,checked)->prefs().edit().putBoolean("background_cycles_enabled",checked).apply());runtime.addView(bg,full());Switch telemetry=new Switch(this);telemetry.setText("Observe telemetry journal");telemetry.setChecked(prefs().getBoolean("observe_telemetry_enabled",true));telemetry.setOnCheckedChangeListener((b,checked)->prefs().edit().putBoolean("observe_telemetry_enabled",checked).apply());runtime.addView(telemetry,full());runtime.addView(text("Local background cadence",14,true));LinearLayout intervals=horizontal();for(int sec:new int[]{30,60,120,300}){Button b=button(sec<60?sec+"s":(sec/60)+"m");b.setOnClickListener(v->{prefs().edit().putInt("local_background_interval_seconds",sec).apply();toast("Local cadence saved.");});intervals.addView(b,weight());}runtime.addView(intervals,full());runtime.addView(text("Deterministic local cognition runs only during wake and uses zero model/API calls. Rest is passive: state stays loaded and foreground input remains immediately responsive, while scheduled autonomous thought is suspended. Settings here are device-local and cannot overwrite protected server identity/core state.",12,false));list.addView(runtime,full()); }

    private void showAccount(){ detailHeader("Account");LinearLayout list=vertical();ScrollView scroll=new ScrollView(this);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));list.addView(text("Loading account…",14,false)); io.execute(()->{JanusApiClient.Response r=api.get("/auth/me",true);main.post(()->{list.removeAllViews();if(r.ok())try{JSONObject a=new JSONObject(r.body).optJSONObject("account");if(a!=null){LinearLayout c=card();c.addView(text(a.optString("username",profile),18,true));c.addView(text(a.optString("email","")+"\nEmail verified: "+yesNo(a.optBoolean("email_verified",false))+"\nGoogle linked: "+yesNo(a.optBoolean("google_linked",false)),14,false));list.addView(c,full());}}catch(Exception ignored){}Button verify=button("Verify / resend email");verify.setOnClickListener(v->promptEmailVerification());list.addView(verify,full());Button logout=button("Sign out");logout.setOnClickListener(v->signOut(false));list.addView(logout,full());Button all=button("Sign out all devices");all.setOnClickListener(v->signOut(true));list.addView(all,full());Button delete=button("Delete account");delete.setOnClickListener(v->promptDeleteAccount());list.addView(delete,full());});}); }
    private void signOut(boolean all){ io.execute(()->{if(all)api.post("/auth/logout-all","{}",true);else api.post("/auth/logout","{}",true);api.clearSession();profile="";try{google.signOut();}catch(Exception ignored){}main.post(this::showAuth);}); }
    private void promptDeleteAccount(){ LinearLayout box=vertical();EditText confirmation=input("Type DELETE");EditText password=input("Current password (blank for Google-only account)");password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);box.addView(confirmation,full());box.addView(password,full());new AlertDialog.Builder(this).setTitle("Permanently delete JANUS account?").setMessage("This deletes the account and associated account data. This cannot be undone.").setView(box).setPositiveButton("Delete",(d,w)->{if(!"DELETE".equals(confirmation.getText().toString())){toast("Deletion cancelled: confirmation did not match.");return;}io.execute(()->{JSONObject body=new JSONObject();try{body.put("confirmation","DELETE");body.put("current_password",password.getText().toString());}catch(Exception ignored){}JanusApiClient.Response r=api.delete("/auth/account",body.toString(),true);main.post(()->{if(r.ok()){api.clearSession();profile="";showAuth();toast("JANUS account deleted.");}else toast("Deletion failed · "+readableError(r));});});}).setNegativeButton("Cancel",null).show(); }

    private void showJsonListScreen(String title,String path,String arrayKey,String headingKey,String bodyKey){ detailHeader(title);LinearLayout list=vertical();ScrollView scroll=new ScrollView(this);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));list.addView(text("Loading…",14,false));io.execute(()->{JanusApiClient.Response r=api.get(path,true);main.post(()->{list.removeAllViews();if(!r.ok()){list.addView(text(readableError(r),14,false));return;}try{JSONObject j=new JSONObject(r.body);JSONArray items=j.optJSONArray(arrayKey);if(items==null){list.addView(text(prettyJson(r.body),13,false));return;}for(int i=0;i<items.length();i++){JSONObject x=items.optJSONObject(i);if(x==null)continue;LinearLayout c=card();c.addView(text(prettyName(x.optString(headingKey,"event")),14,true));String time=formatTime(x.opt("created_at"));if(!time.isBlank())c.addView(text(time,12,false));c.addView(text(x.optString(bodyKey,x.toString()),14,false));list.addView(c,full());}}catch(Exception e){list.addView(text(prettyJson(r.body),13,false));}});}); }
    private void backgroundAction(String path,JSONObject body,boolean auth,String success){ io.execute(()->{JanusApiClient.Response r=api.post(path,body.toString(),auth);main.post(()->toast(r.ok()?success:readableError(r)));}); }

    private LinearLayout vertical(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);applyBackground(l);return l;}
    private LinearLayout horizontal(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);return l;}
    private LinearLayout card(){LinearLayout l=vertical();l.setPadding(dp(12),dp(10),dp(12),dp(10));l.setBackgroundColor(surfaceColor());LinearLayout.LayoutParams lp=full();lp.setMargins(0,dp(5),0,dp(5));l.setLayoutParams(lp);return l;}
    private TextView text(String s,int sp,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setTextColor(textColor());t.setPadding(dp(5),dp(7),dp(5),dp(7));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private EditText input(String hint){EditText e=new EditText(this);JanusUiLocalizationPolish.applyHint(this,e,hint);e.setHintTextColor(mutedColor());e.setTextColor(textColor());e.setSingleLine(true);e.setPadding(dp(12),dp(9),dp(12),dp(9));return e;}
    private Button button(String s){Button b=new Button(this);JanusUiLocalizationPolish.applyButton(this,b,s);b.setAllCaps(false);return b;}
    private void applyBackground(View v){v.setBackgroundColor(backgroundColor());}
    private int backgroundColor(){return isDark()?Color.rgb(18,18,18):Color.WHITE;}
    private int surfaceColor(){return isDark()?Color.rgb(37,37,37):Color.rgb(243,243,243);}
    private int textColor(){return isDark()?Color.rgb(244,244,244):Color.rgb(24,24,24);}
    private int mutedColor(){return isDark()?Color.rgb(180,180,180):Color.rgb(105,105,105);}
    private int userColor(){return isDark()?Color.rgb(37,55,76):Color.rgb(222,237,255);}
    private boolean isDark(){String mode=prefs().getString("theme_mode","system");if("dark".equals(mode))return true;if("light".equals(mode))return false;return (getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK)==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private int accentColor(){String a=prefs().getString("accent","slate");switch(a){case"indigo":return Color.rgb(63,81,181);case"teal":return Color.rgb(0,121,107);case"amber":return Color.rgb(255,160,0);case"violet":return Color.rgb(123,31,162);default:return isDark()?Color.rgb(150,150,150):Color.rgb(60,60,60);}}
    private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
    private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private LinearLayout.LayoutParams full(){return new LinearLayout.LayoutParams(-1,-2);}
    private LinearLayout.LayoutParams wrap(){return new LinearLayout.LayoutParams(-2,-2);}
    private LinearLayout.LayoutParams weight(){return new LinearLayout.LayoutParams(0,-2,1);}

    private String readableError(JanusApiClient.Response r){ if(r==null)return"No response from JANUS.";if(r.error!=null&&!r.error.isBlank())return r.error;try{JSONObject j=new JSONObject(r.body);String d=j.optString("detail","");if(!d.isBlank())return d;}catch(Exception ignored){}if(r.code==401||r.code==403)return"Authentication failed or session expired.";if(r.code==429)return"Too many attempts. Please try again shortly.";if(r.code>=500)return"JANUS server is temporarily unavailable (HTTP "+r.code+").";return r.code>0?"HTTP "+r.code:"Network request failed."; }
    private String prettyJson(String raw){try{return new JSONObject(raw).toString(2);}catch(Exception ignored){}try{return new JSONArray(raw).toString(2);}catch(Exception ignored){}return raw==null?"":raw;}
    private String enc(String s){try{return URLEncoder.encode(s==null?"":s,StandardCharsets.UTF_8);}catch(Exception e){return"";}}
    private String prettyName(String s){String x=(s==null?"":s).replace('_',' ').trim();if(x.isEmpty())return"";return capitalize(x);}
    private String capitalize(String s){if(s==null||s.isEmpty())return"";return Character.toUpperCase(s.charAt(0))+s.substring(1);}
    private String yesNo(boolean v){return v?"yes":"no";}
    private String clip(String s,int max){if(s==null)return"";return s.length()<=max?s:s.substring(0,max)+"…";}
    private String safeName(String s){String x=s==null||s.isBlank()?"JANUS-artifact.md":s.replaceAll("[\\\\/]+","-");return x.length()>120?x.substring(0,120):x;}
    private String formatTime(Object value){ if(value==null||value==JSONObject.NULL)return"";try{if(value instanceof Number){long n=((Number)value).longValue();if(n<100000000000L)n*=1000L;return DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT).format(new Date(n));}String s=String.valueOf(value);if(s.matches("\\d+")){long n=Long.parseLong(s);if(n<100000000000L)n*=1000L;return DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT).format(new Date(n));}return s.replace('T',' ').replace("Z","");}catch(Exception e){return String.valueOf(value);} }

    private static final class Attachment{ final String id;final String name;Attachment(String id,String name){this.id=id;this.name=name;} }
}
