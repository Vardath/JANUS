package com.vardath.janus.v080;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.method.ScrollingMovementMethod;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends AppCompatActivity {
    private static final String PREFS = "janus_v080";
    private static final String TOKEN = "access_token";
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    private LinearLayout root;
    private LinearLayout content;
    private TextView status;
    private String accessToken = "";
    private String activeTab = "Chat";

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        accessToken = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(TOKEN, "");
        buildRoot();
        if (accessToken == null || accessToken.isBlank()) {
            showAuth();
        } else {
            validateSession();
        }
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private void buildRoot() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(18), dp(16), dp(14));

        TextView title = text("JANUS · v0.80 dev · 11 cores · 7→2→1→1", 18, true);
        root.addView(title, matchWrap());

        status = text("Starting…", 13, false);
        status.setPadding(0, dp(6), 0, dp(10));
        root.addView(status, matchWrap());

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        root.addView(content, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);
    }

    private void showAuth() {
        content.removeAllViews();
        activeTab = "Auth";
        status.setText("Not signed in · checking server…");
        checkHealth();

        TextView heading = text("Sign in to JANUS", 30, true);
        heading.setPadding(0, dp(18), 0, dp(16));
        content.addView(heading, matchWrap());

        EditText identifier = input("Username or email");
        EditText email = input("Email (for registration)");
        EditText password = input("Password");
        password.setInputType(0x00000081);
        content.addView(identifier, matchWrap());
        content.addView(email, matchWrap());
        content.addView(password, matchWrap());

        Button login = button("Sign in");
        Button register = button("Create account");
        content.addView(login, matchWrap());
        content.addView(register, matchWrap());

        TextView note = text("v0.80 is the clean native rebuild. It is installed alongside the legacy JANUS app during development.", 14, false);
        note.setPadding(0, dp(16), 0, 0);
        content.addView(note, matchWrap());

        login.setOnClickListener(v -> {
            String id = identifier.getText().toString().trim();
            String pw = password.getText().toString();
            if (id.isEmpty() || pw.isEmpty()) {
                toast("Enter your username/email and password.");
                return;
            }
            JSONObject body = new JSONObject();
            try {
                body.put("identifier", id);
                body.put("password", pw);
            } catch (Exception ignored) {}
            authenticate("/auth/login", body);
        });

        register.setOnClickListener(v -> {
            String username = identifier.getText().toString().trim();
            String mail = email.getText().toString().trim();
            String pw = password.getText().toString();
            if (username.isEmpty() || mail.isEmpty() || pw.isEmpty()) {
                toast("Registration needs username, email and password.");
                return;
            }
            JSONObject body = new JSONObject();
            try {
                body.put("username", username);
                body.put("email", mail);
                body.put("password", pw);
            } catch (Exception ignored) {}
            authenticate("/auth/register", body);
        });
    }

    private void authenticate(String path, JSONObject body) {
        status.setText("Connecting to JANUS…");
        io.execute(() -> {
            HttpResult result = request("POST", path, body.toString(), false);
            if (result.ok()) {
                try {
                    JSONObject json = new JSONObject(result.body);
                    String token = json.optString("access_token", "");
                    if (!token.isBlank()) {
                        saveToken(token);
                        ui.post(this::showApp);
                        return;
                    }
                } catch (Exception ignored) {}
            }
            ui.post(() -> status.setText("Sign-in failed · " + friendlyError(result)));
        });
    }

    private void validateSession() {
        status.setText("Restoring JANUS session…");
        io.execute(() -> {
            HttpResult result = request("GET", "/auth/me", null, true);
            ui.post(() -> {
                if (result.ok()) showApp();
                else {
                    clearToken();
                    showAuth();
                    status.setText("Session expired or unavailable · sign in again");
                }
            });
        });
    }

    private void showApp() {
        content.removeAllViews();
        status.setText("Connected session · checking capabilities…");

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        String[] names = {"Chat", "Messages", "Observe", "Options"};
        for (String name : names) {
            Button b = button(name);
            b.setAllCaps(false);
            b.setOnClickListener(v -> showTab(name));
            tabs.addView(b, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        content.addView(tabs, matchWrap());

        LinearLayout page = new LinearLayout(this);
        page.setId(View.generateViewId());
        page.setOrientation(LinearLayout.VERTICAL);
        content.addView(page, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        page.setTag("page");

        checkCapabilities();
        showTab("Chat");
    }

    private LinearLayout page() {
        for (int i = 0; i < content.getChildCount(); i++) {
            View v = content.getChildAt(i);
            if (v instanceof LinearLayout && "page".equals(v.getTag())) return (LinearLayout) v;
        }
        throw new IllegalStateException("v0.80 page container missing");
    }

    private void showTab(String tab) {
        activeTab = tab;
        LinearLayout page = page();
        page.removeAllViews();
        switch (tab) {
            case "Messages" -> showPlaceholder(page, "Messages", "Queued JANUS prompts and delivered messages will live here in Stage 3.");
            case "Observe" -> showPlaceholder(page, "Observe", "Stable readable 11-core telemetry lands here in Stage 3. This native screen will not use the legacy rapid-refresh WebView.");
            case "Options" -> showOptions(page);
            default -> showChat(page);
        }
    }

    private void showChat(LinearLayout page) {
        TextView heading = text("Chat", 30, true);
        heading.setPadding(0, dp(12), 0, dp(10));
        page.addView(heading, matchWrap());

        TextView transcript = text("JANUS v0.80 Stage 1 ready. Send a message to test the native client/server round trip.\n", 16, false);
        transcript.setMovementMethod(new ScrollingMovementMethod());
        transcript.setPadding(dp(10), dp(10), dp(10), dp(10));

        ScrollView scroller = new ScrollView(this);
        scroller.addView(transcript, matchWrap());
        page.addView(scroller, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout composer = new LinearLayout(this);
        composer.setOrientation(LinearLayout.HORIZONTAL);
        composer.setGravity(Gravity.CENTER_VERTICAL);
        EditText message = input("Message JANUS");
        Button send = button("Send");
        composer.addView(message, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        composer.addView(send, wrapWrap());
        page.addView(composer, matchWrap());

        send.setOnClickListener(v -> {
            String text = message.getText().toString().trim();
            if (text.isEmpty()) return;
            String clientId = UUID.randomUUID().toString();
            message.setText("");
            transcript.append("\nYou\n" + text + "\n");
            send.setEnabled(false);
            status.setText("Sending to JANUS…");

            JSONObject payload = new JSONObject();
            try {
                payload.put("message", text);
                payload.put("client_message_id", clientId);
            } catch (Exception ignored) {}

            io.execute(() -> {
                HttpResult result = request("POST", "/desktop/chat", payload.toString(), true);
                String reply;
                if (result.ok()) {
                    try {
                        JSONObject json = new JSONObject(result.body);
                        reply = json.optString("reply", result.body);
                    } catch (Exception e) {
                        reply = result.body;
                    }
                } else {
                    reply = "System\n" + friendlyError(result);
                }
                String finalReply = reply;
                ui.post(() -> {
                    transcript.append("\nJANUS\n" + finalReply + "\n");
                    scroller.post(() -> scroller.fullScroll(View.FOCUS_DOWN));
                    send.setEnabled(true);
                    status.setText(result.ok() ? "Interface active" : "Reduced capability · request failed");
                });
            });
        });
    }

    private void showOptions(LinearLayout page) {
        TextView heading = text("Options", 30, true);
        heading.setPadding(0, dp(12), 0, dp(12));
        page.addView(heading, matchWrap());
        TextView server = text("Server: " + BuildConfig.SERVER_BASE_URL, 14, false);
        page.addView(server, matchWrap());
        Button health = button("Check system status");
        Button capabilities = button("Check compatibility");
        Button logout = button("Sign out");
        page.addView(health, matchWrap());
        page.addView(capabilities, matchWrap());
        page.addView(logout, matchWrap());
        health.setOnClickListener(v -> checkHealth());
        capabilities.setOnClickListener(v -> checkCapabilities());
        logout.setOnClickListener(v -> {
            clearToken();
            showAuth();
        });
    }

    private void showPlaceholder(LinearLayout page, String headingText, String body) {
        TextView heading = text(headingText, 30, true);
        heading.setPadding(0, dp(12), 0, dp(14));
        page.addView(heading, matchWrap());
        page.addView(text(body, 16, false), matchWrap());
    }

    private void checkHealth() {
        io.execute(() -> {
            HttpResult result = request("GET", "/health", null, false);
            ui.post(() -> status.setText(result.ok() ? "JANUS server reachable" : "JANUS server unavailable · " + friendlyError(result)));
        });
    }

    private void checkCapabilities() {
        io.execute(() -> {
            HttpResult result = request("GET", "/protocol/capabilities", null, false);
            ui.post(() -> {
                if (result.ok()) status.setText("Interface active · compatibility received");
                else checkHealth();
            });
        });
    }

    private HttpResult request(String method, String path, @Nullable String body, boolean authenticated) {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(BuildConfig.SERVER_BASE_URL + path);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod(method);
            connection.setConnectTimeout(12_000);
            connection.setReadTimeout(45_000);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Connection", "close");
            if (authenticated && accessToken != null && !accessToken.isBlank()) {
                connection.setRequestProperty("Authorization", "Bearer " + accessToken);
            }
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = connection.getOutputStream()) {
                    out.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 400 ? connection.getInputStream() : connection.getErrorStream();
            String text = read(stream);
            return new HttpResult(code, text, null);
        } catch (Exception e) {
            return new HttpResult(0, "", e.getClass().getSimpleName() + ": " + e.getMessage());
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static String read(@Nullable InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder out = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) out.append(line).append('\n');
        }
        return out.toString().trim();
    }

    private String friendlyError(HttpResult result) {
        if (result.error != null && !result.error.isBlank()) return result.error;
        if (result.code == 401) return "Authentication required or session expired.";
        if (result.code == 429) return "JANUS is rate-limited. Try again shortly.";
        if (result.code == 502 || result.code == 503 || result.code == 504) return "JANUS server is temporarily unavailable (HTTP " + result.code + ").";
        if (result.code > 0) return "HTTP " + result.code + (result.body.isBlank() ? "" : " · " + result.body);
        return "Network request failed.";
    }

    private void saveToken(String token) {
        accessToken = token;
        getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(TOKEN, token).apply();
    }

    private void clearToken() {
        accessToken = "";
        getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(TOKEN).apply();
    }

    private TextView text(String value, int sp, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private EditText input(String hint) {
        EditText view = new EditText(this);
        view.setHint(hint);
        view.setSingleLine(true);
        view.setPadding(dp(12), dp(10), dp(12), dp(10));
        return view;
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        return button;
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams wrapWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private record HttpResult(int code, String body, String error) {
        boolean ok() { return code >= 200 && code < 300; }
    }
}
