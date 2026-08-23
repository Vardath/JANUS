package com.vardath.janus;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.tasks.Task;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URLEncoder;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * JANUS Android clean rebuild.
 *
 * This is deliberately a native Android client. It does not load the old WebView
 * application, does not compose UI from patches, and does not depend on legacy
 * JavaScript. The existing JANUS server/global core and local core runtime remain
 * the cognition/continuity layer; this class is only the user-facing client.
 */
public final class MainActivity extends Activity {
    private static final String SERVER = "https://janus-global-core.onrender.com";
    private static final String PREFS = "janus_native_rebuild";
    private static final String TOKEN = "access_token";
    private static final String PROFILE = "profile";
    private static final int RC_GOOGLE = 731;
    private static final int RC_FILE = 732;
    private static final int MAX_FILE_BYTES = 8 * 1024 * 1024;

    private final ExecutorService io = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final List<Attachment> attachments = new ArrayList<>();

    private GoogleSignInClient google;
    private String token = "";
    private String profile = "";
    private LinearLayout root;
    private LinearLayout content;
    private LinearLayout nav;
    private TextView status;
    private LinearLayout chatLog;
    private ScrollView chatScroll;
    private LinearLayout attachmentStrip;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        token = prefs().getString(TOKEN, "");
        profile = prefs().getString(PROFILE, "");
        GoogleSignInOptions options = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                .requestEmail()
                .requestIdToken(BuildConfig.GOOGLE_WEB_CLIENT_ID)
                .build();
        google = GoogleSignIn.getClient(this, options);
        try { JanusLocalCoreRuntime.get(this).start(); } catch (Exception ignored) {}
        if (token.isBlank()) showAuth(); else validateSession();
    }

    @Override protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private android.content.SharedPreferences prefs() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    // ---------- Authentication ----------
    private void showAuth() {
        attachments.clear();
        root = vertical();
        root.setPadding(dp(24), dp(28), dp(24), dp(24));
        root.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(text("JANUS", 34, true));
        root.addView(text("Sign in to continue your JANUS identity, memory and conversations.", 16, false));

        LinearLayout tabs = horizontal();
        Button sign = button("Sign in");
        Button create = button("Create account");
        tabs.addView(sign, weight());
        tabs.addView(create, weight());
        root.addView(tabs, full());

        LinearLayout form = vertical();
        TextView message = text("", 13, false);
        root.addView(form, full());
        root.addView(message, full());

        Button googleButton = button("Continue with Google");
        googleButton.setOnClickListener(v -> startActivityForResult(google.getSignInIntent(), RC_GOOGLE));
        root.addView(googleButton, full());
        root.addView(text("Password and Google sign-in use the same JANUS account and continuity state.", 12, false), full());

        sign.setOnClickListener(v -> renderSignIn(form, message));
        create.setOnClickListener(v -> renderRegister(form, message));
        renderSignIn(form, message);
        setContentView(root);
    }

    private void renderSignIn(LinearLayout form, TextView message) {
        form.removeAllViews();
        message.setText("");
        EditText id = input("Username or email");
        EditText password = input("Password");
        password.setInputType(0x81);
        Button go = button("Sign in");
        form.addView(id, full());
        form.addView(password, full());
        form.addView(go, full());
        go.setOnClickListener(v -> {
            String identity = id.getText().toString().trim();
            String pw = password.getText().toString();
            if (identity.isEmpty() || pw.isEmpty()) { message.setText("Enter your username/email and password."); return; }
            JSONObject body = new JSONObject();
            try { body.put("identifier", identity); body.put("password", pw); } catch (Exception ignored) {}
            authRequest("/auth/login", body, message);
        });
    }

    private void renderRegister(LinearLayout form, TextView message) {
        form.removeAllViews();
        message.setText("");
        EditText username = input("Username");
        EditText email = input("Email");
        EditText password = input("Password (12+ characters, including a letter and number)");
        password.setInputType(0x81);
        Button go = button("Create account");
        form.addView(username, full());
        form.addView(email, full());
        form.addView(password, full());
        form.addView(go, full());
        go.setOnClickListener(v -> {
            String u = username.getText().toString().trim();
            String e = email.getText().toString().trim();
            String pw = password.getText().toString();
            if (u.length() < 3 || !e.contains("@") || pw.length() < 12) {
                message.setText("Use a 3+ character username, valid email and 12+ character password."); return;
            }
            JSONObject body = new JSONObject();
            try { body.put("username", u); body.put("email", e); body.put("password", pw); } catch (Exception ignored) {}
            authRequest("/auth/register", body, message);
        });
    }

    private void authRequest(String path, JSONObject body, TextView message) {
        message.setText("Connecting to JANUS…");
        io.execute(() -> {
            Response r = request("POST", path, body.toString(), false);
            if (r.ok()) {
                try {
                    JSONObject j = new JSONObject(r.body);
                    JSONObject account = j.optJSONObject("account");
                    String t = j.optString("access_token", "");
                    String p = account == null ? j.optString("username", "") : account.optString("username", "");
                    if (!t.isBlank()) {
                        saveSession(t, p);
                        main.post(this::showApp);
                        return;
                    }
                } catch (Exception ignored) {}
            }
            main.post(() -> message.setText("Sign-in failed · " + readableError(r)));
        });
    }

    private void validateSession() {
        io.execute(() -> {
            Response r = request("GET", "/auth/me", null, true);
            if (!r.ok()) { clearSession(); main.post(this::showAuth); return; }
            try {
                JSONObject account = new JSONObject(r.body).optJSONObject("account");
                if (account != null) profile = account.optString("username", profile);
                prefs().edit().putString(PROFILE, profile).apply();
            } catch (Exception ignored) {}
            main.post(this::showApp);
        });
    }

    private void saveSession(String t, String p) {
        token = t; profile = p;
        prefs().edit().putString(TOKEN, t).putString(PROFILE, p).apply();
    }

    private void clearSession() {
        token = ""; profile = ""; attachments.clear();
        prefs().edit().clear().apply();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == RC_FILE) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) uploadFile(data.getData());
            return;
        }
        if (requestCode != RC_GOOGLE) return;
        Task<GoogleSignInAccount> task = GoogleSignIn.getSignedInAccountFromIntent(data);
        try {
            GoogleSignInAccount account = task.getResult(ApiException.class);
            String idToken = account.getIdToken();
            if (idToken == null || idToken.isBlank()) { toast("Google returned no identity token."); return; }
            JSONObject body = new JSONObject(); body.put("id_token", idToken);
            io.execute(() -> {
                Response r = request("POST", "/auth/google", body.toString(), false);
                if (!r.ok()) { main.post(() -> toast("Google sign-in failed · " + readableError(r))); return; }
                try {
                    JSONObject j = new JSONObject(r.body), a = j.optJSONObject("account");
                    String t = j.optString("access_token", "");
                    String p = a == null ? "" : a.optString("username", "");
                    if (t.isBlank()) throw new IllegalStateException("No session token returned");
                    saveSession(t, p); main.post(this::showApp);
                } catch (Exception e) { main.post(() -> toast("Google sign-in failed after verification.")); }
            });
        } catch (ApiException e) {
            if (e.getStatusCode() == 10) toast("Google configuration mismatch (code 10). Password sign-in is available; OAuth package/signing registration must match this build.");
            else toast("Google sign-in failed · code " + e.getStatusCode());
        } catch (Exception e) { toast("Google sign-in failed."); }
    }

    // ---------- Main shell ----------
    private void showApp() {
        root = vertical();
        LinearLayout header = vertical();
        header.setPadding(dp(14), dp(8), dp(14), dp(7));
        header.addView(text("JANUS", 20, true), full());
        LinearLayout state = horizontal();
        state.addView(text("11 cores · 7 → 2 → 1 → 1", 12, false), weight());
        status = text("Interface active", 12, false);
        state.addView(status, wrap());
        header.addView(state, full());
        root.addView(header, full());

        content = vertical();
        content.setPadding(dp(12), dp(6), dp(12), dp(6));
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));

        nav = horizontal();
        nav.setPadding(dp(6), dp(4), dp(6), dp(8));
        for (String page : new String[]{"Chat", "Messages", "Observe", "Options"}) {
            Button b = button(page);
            b.setTag(page);
            b.setOnClickListener(v -> showPage((String) v.getTag()));
            nav.addView(b, new LinearLayout.LayoutParams(0, dp(58), 1));
        }
        root.addView(nav, full());
        setContentView(root);
        showPage("Chat");
    }

    private void showPage(String page) {
        content.removeAllViews();
        for (int i = 0; i < nav.getChildCount(); i++) {
            Button b = (Button) nav.getChildAt(i);
            boolean selected = page.equals(b.getTag());
            b.setTypeface(Typeface.DEFAULT, selected ? Typeface.BOLD : Typeface.NORMAL);
            b.setAlpha(selected ? 1f : .65f);
        }
        if (page.equals("Messages")) showMessages();
        else if (page.equals("Observe")) showObserve();
        else if (page.equals("Options")) showOptions();
        else showChat();
    }

    // ---------- Chat ----------
    private void showChat() {
        content.addView(text("Chat", 28, true), full());
        chatLog = vertical();
        chatScroll = new ScrollView(this);
        chatScroll.addView(chatLog, full());
        content.addView(chatScroll, new LinearLayout.LayoutParams(-1, 0, 1));

        attachmentStrip = horizontal();
        HorizontalScrollView hs = new HorizontalScrollView(this);
        hs.addView(attachmentStrip, full());
        content.addView(hs, full());
        renderAttachments();

        LinearLayout composer = horizontal();
        composer.setGravity(Gravity.CENTER_VERTICAL);
        Button plus = button("+");
        EditText message = input("Message JANUS");
        message.setSingleLine(false);
        message.setMaxLines(4);
        Button send = button("Send");
        plus.setOnClickListener(v -> pickFile());
        send.setOnClickListener(v -> {
            String m = message.getText().toString().trim();
            if (m.isEmpty() && attachments.isEmpty()) return;
            if (m.isEmpty()) m = "Please assess the attached file or files.";
            message.setText("");
            sendChat(m);
        });
        composer.addView(plus, new LinearLayout.LayoutParams(dp(52), dp(58)));
        composer.addView(message, new LinearLayout.LayoutParams(0, dp(58), 1));
        composer.addView(send, new LinearLayout.LayoutParams(dp(82), dp(58)));
        content.addView(composer, full());
    }

    private void sendChat(String message) {
        List<Attachment> files = new ArrayList<>(attachments);
        attachments.clear(); renderAttachments();
        addBubble("You", message + (files.isEmpty() ? "" : "\nAttachments: " + attachmentNames(files)), true);
        status.setText("JANUS is responding…");
        JSONObject body = new JSONObject();
        try {
            body.put("profile_id", profile);
            body.put("message", message);
            body.put("client_message_id", "android-native-" + UUID.randomUUID());
            JSONArray ids = new JSONArray(); for (Attachment a : files) ids.put(a.id);
            body.put("attachment_ids", ids);
        } catch (Exception ignored) {}
        io.execute(() -> {
            Response r = request("POST", "/desktop/chat", body.toString(), true);
            if (!r.ok()) {
                main.post(() -> { addBubble("System", readableError(r), false); status.setText("Connection problem"); });
                return;
            }
            String reply = r.body;
            try { JSONObject j = new JSONObject(r.body); reply = j.optString("reply", j.optString("response", r.body)); } catch (Exception ignored) {}
            String finalReply = reply;
            main.post(() -> { addBubble("JANUS", finalReply, false); status.setText("Interface active"); });
        });
    }

    private void addBubble(String who, String body, boolean user) {
        if (chatLog == null) return;
        LinearLayout box = vertical();
        box.setPadding(dp(14), dp(10), dp(14), dp(10));
        box.setBackgroundColor(user ? Color.rgb(225, 238, 255) : Color.rgb(242, 242, 242));
        box.addView(text(who, 13, true), full());
        box.addView(text(body, 16, false), full());
        LinearLayout.LayoutParams lp = full();
        lp.setMargins(user ? dp(48) : 0, dp(5), user ? 0 : dp(28), dp(5));
        chatLog.addView(box, lp);
        chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN));
    }

    // ---------- Attachments ----------
    private void pickFile() {
        if (attachments.size() >= 4) { toast("Up to 4 files per Chat turn."); return; }
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE); i.setType("*/*");
        startActivityForResult(i, RC_FILE);
    }

    private void uploadFile(Uri uri) {
        status.setText("Uploading attachment…");
        io.execute(() -> {
            try {
                byte[] bytes = readFile(uri);
                String name = fileName(uri);
                String mime = getContentResolver().getType(uri);
                if (mime == null) mime = "application/octet-stream";
                JSONObject body = new JSONObject();
                body.put("filename", name);
                body.put("mime_type", mime);
                body.put("data_base64", Base64.encodeToString(bytes, Base64.NO_WRAP));
                Response r = request("POST", "/files/upload", body.toString(), true);
                if (!r.ok()) { main.post(() -> status.setText("Attachment failed · " + readableError(r))); return; }
                JSONObject f = new JSONObject(r.body).optJSONObject("file");
                if (f == null) throw new IllegalStateException("Server did not return a file record");
                Attachment a = new Attachment(f.optString("id"), f.optString("filename", name));
                main.post(() -> { attachments.add(a); renderAttachments(); status.setText("Attachment ready"); });
            } catch (Exception e) { main.post(() -> status.setText("Attachment failed · " + e.getMessage())); }
        });
    }

    private void renderAttachments() {
        if (attachmentStrip == null) return;
        attachmentStrip.removeAllViews();
        for (Attachment a : new ArrayList<>(attachments)) {
            Button chip = button("× " + a.name);
            chip.setOnClickListener(v -> { attachments.removeIf(x -> x.id.equals(a.id)); renderAttachments(); });
            attachmentStrip.addView(chip, wrap());
        }
    }

    private byte[] readFile(Uri uri) throws Exception {
        try (InputStream in = getContentResolver().openInputStream(uri); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            if (in == null) throw new IllegalArgumentException("File could not be opened");
            byte[] buf = new byte[32768]; int n, total = 0;
            while ((n = in.read(buf)) >= 0) { total += n; if (total > MAX_FILE_BYTES) throw new IllegalArgumentException("File exceeds 8 MB"); out.write(buf, 0, n); }
            return out.toByteArray();
        }
    }

    private String fileName(Uri uri) {
        String out = "attachment";
        try (Cursor c = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) { String s = c.getString(0); if (s != null && !s.isBlank()) out = s; }
        } catch (Exception ignored) {}
        return out;
    }

    private String attachmentNames(List<Attachment> files) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < files.size(); i++) { if (i > 0) b.append(", "); b.append(files.get(i).name); }
        return b.toString();
    }

    // ---------- Messages / Observe / Options ----------
    private void showMessages() {
        content.addView(text("Messages", 28, true), full());
        content.addView(text("Questions, observations, memories and follow-ups JANUS creates outside the immediate chat turn.", 13, false), full());
        LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        Button refresh = button("Refresh"); refresh.setOnClickListener(v -> loadMessages(list)); content.addView(refresh, full());
        loadMessages(list);
    }

    private void loadMessages(LinearLayout list) {
        list.removeAllViews(); list.addView(text("Loading…", 14, false));
        io.execute(() -> {
            Response r = request("GET", "/desktop/messages?username=" + enc(profile) + "&limit=50", null, true);
            main.post(() -> {
                list.removeAllViews();
                if (!r.ok()) { list.addView(text(readableError(r), 14, false)); return; }
                try {
                    JSONObject j = new JSONObject(r.body); JSONArray items = j.optJSONArray("items");
                    if (items == null || items.length() == 0) { list.addView(text("No JANUS messages yet.", 15, false)); return; }
                    for (int i = 0; i < items.length(); i++) {
                        JSONObject x = items.getJSONObject(i);
                        LinearLayout card = vertical(); card.setPadding(dp(12), dp(10), dp(12), dp(10));
                        card.addView(text(x.optString("message_type", "Message"), 14, true));
                        card.addView(text(x.optString("detail", x.optString("message", "")), 15, false));
                        list.addView(card, full());
                    }
                } catch (Exception e) { list.addView(text("Messages could not be displayed.", 14, false)); }
            });
        });
    }

    private void showObserve() {
        content.addView(text("Observe", 28, true), full());
        content.addView(text("Stable externalizable JANUS activity. This view does not expose private chain-of-thought.", 13, false), full());
        LinearLayout list = vertical(); ScrollView scroll = new ScrollView(this); scroll.addView(list, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        Button refresh = button("Refresh snapshot"); refresh.setOnClickListener(v -> loadObserve(list)); content.addView(refresh, full());
        loadObserve(list);
    }

    private void loadObserve(LinearLayout list) {
        list.removeAllViews(); list.addView(text("Loading core activity…", 14, false));
        io.execute(() -> {
            Response r = request("GET", "/desktop/runtime-cores?username=" + enc(profile), null, true);
            main.post(() -> {
                list.removeAllViews();
                if (!r.ok()) { list.addView(text(readableError(r), 14, false)); return; }
                try {
                    JSONObject j = new JSONObject(r.body); JSONObject rt = j.optJSONObject("runtime"); if (rt == null) rt = j;
                    list.addView(text("11 functional cores · 7 specialists → 2 hemispheres → consensus → interface", 15, true));
                    list.addView(text("Phase: " + rt.optString("phase", "unknown") + "\nPresence: " + rt.optString("presence_state", "unknown") + "\nRemote clients: " + rt.optInt("remote_clients", 0), 14, false));
                    JSONObject cores = rt.optJSONObject("cores");
                    if (cores != null) {
                        JSONArray names = cores.names();
                        if (names != null) for (int i = 0; i < names.length(); i++) {
                            String name = names.optString(i); JSONObject c = cores.optJSONObject(name);
                            String detail = c == null ? "" : c.optString("last_output", c.optString("processing_mode", "active"));
                            list.addView(text(name.replace('_', ' ') + "\n" + detail, 14, false), full());
                        }
                    }
                } catch (Exception e) { list.addView(text("Runtime snapshot could not be displayed.", 14, false)); }
            });
        });
    }

    private void showOptions() {
        content.addView(text("Options", 28, true), full());
        ScrollView scroll = new ScrollView(this); LinearLayout list = vertical(); scroll.addView(list, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        option(list, "Cores", "Runtime core state", "/desktop/runtime-cores?username=" + enc(profile));
        option(list, "Memory", "Trace → working → episodic → core", "/desktop/memory?username=" + enc(profile));
        option(list, "Activity", "Conversation, reflections, decisions and events", "/desktop/activity?username=" + enc(profile));
        option(list, "System status", "Server, database and persistence health", "/diagnostics/runtime-health");
        option(list, "Research workspace", "Established results, hypotheses, negative results and open questions", "/research/workspace");
        option(list, "Artifacts", "Generated continuity and research artifacts", "/artifacts");
        option(list, "Background research", "Externalized provenance and research activity", "/research-provenance/status");
        option(list, "Maintenance review", "Owner-gated maintenance proposals", "/maintenance/status");
        Button signOut = button("Sign out\n" + (profile.isBlank() ? "JANUS account" : profile));
        signOut.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        signOut.setOnClickListener(v -> { clearSession(); try { google.signOut(); } catch (Exception ignored) {} showAuth(); });
        list.addView(signOut, full());
    }

    private void option(LinearLayout list, String title, String subtitle, String path) {
        Button b = button(title + "\n" + subtitle);
        b.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        b.setOnClickListener(v -> showDetail(title, path));
        list.addView(b, full());
    }

    private void showDetail(String title, String path) {
        content.removeAllViews();
        Button back = button("← Options"); back.setOnClickListener(v -> showPage("Options")); content.addView(back, full());
        content.addView(text(title, 28, true), full());
        TextView body = text("Loading…", 14, false); ScrollView scroll = new ScrollView(this); scroll.addView(body, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        io.execute(() -> {
            Response r = request("GET", path, null, true);
            String out = r.ok() ? prettyJson(r.body) : readableError(r);
            main.post(() -> body.setText(out));
        });
    }

    private String prettyJson(String raw) {
        try { return new JSONObject(raw).toString(2); } catch (Exception ignored) {}
        try { return new JSONArray(raw).toString(2); } catch (Exception ignored) {}
        return raw;
    }

    // ---------- Networking ----------
    private Response request(String method, String path, String body, boolean auth) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(SERVER + path).openConnection();
            c.setRequestMethod(method); c.setConnectTimeout(15000); c.setReadTimeout(90000);
            c.setRequestProperty("Accept", "application/json");
            if (auth && !token.isBlank()) c.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
                c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = c.getOutputStream()) { out.write(body.getBytes(StandardCharsets.UTF_8)); }
            }
            int code = c.getResponseCode(); InputStream in = code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream();
            return new Response(code, read(in), null);
        } catch (Exception e) { return new Response(0, "", e.getClass().getSimpleName() + ": " + e.getMessage()); }
        finally { if (c != null) c.disconnect(); }
    }

    private String read(InputStream in) throws Exception {
        if (in == null) return "";
        StringBuilder b = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line; while ((line = r.readLine()) != null) b.append(line).append('\n');
        }
        return b.toString().trim();
    }

    private String readableError(Response r) {
        if (r.error != null) return r.error;
        try {
            JSONObject j = new JSONObject(r.body); String d = j.optString("detail", ""); if (!d.isBlank()) return d;
        } catch (Exception ignored) {}
        if (r.code == 401) return "Authentication failed or session expired.";
        if (r.code == 429) return "Too many attempts. Try again shortly.";
        if (r.code >= 500) return "JANUS server is temporarily unavailable (HTTP " + r.code + ").";
        return r.code > 0 ? "HTTP " + r.code : "Network request failed.";
    }

    private String enc(String s) { return URLEncoder.encode(s == null ? "" : s, StandardCharsets.UTF_8); }

    // ---------- UI helpers ----------
    private LinearLayout vertical() { LinearLayout l = new LinearLayout(this); l.setOrientation(LinearLayout.VERTICAL); return l; }
    private LinearLayout horizontal() { LinearLayout l = new LinearLayout(this); l.setOrientation(LinearLayout.HORIZONTAL); return l; }
    private TextView text(String s, int sp, boolean bold) { TextView t = new TextView(this); t.setText(s); t.setTextSize(sp); t.setTextColor(Color.rgb(25,25,25)); t.setPadding(dp(5), dp(7), dp(5), dp(7)); if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return t; }
    private EditText input(String hint) { EditText e = new EditText(this); e.setHint(hint); e.setSingleLine(true); e.setPadding(dp(12), dp(9), dp(12), dp(9)); return e; }
    private Button button(String s) { Button b = new Button(this); b.setText(s); b.setAllCaps(false); return b; }
    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_LONG).show(); }
    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
    private LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private LinearLayout.LayoutParams wrap() { return new LinearLayout.LayoutParams(-2, -2); }
    private LinearLayout.LayoutParams weight() { return new LinearLayout.LayoutParams(0, -2, 1); }

    private static final class Response {
        final int code; final String body; final String error;
        Response(int code, String body, String error) { this.code = code; this.body = body; this.error = error; }
        boolean ok() { return code >= 200 && code < 300; }
    }
    private static final class Attachment {
        final String id; final String name;
        Attachment(String id, String name) { this.id = id; this.name = name; }
    }
}
