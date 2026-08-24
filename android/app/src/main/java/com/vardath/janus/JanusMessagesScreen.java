package com.vardath.janus;

import android.app.Activity;
import android.graphics.Typeface;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.DateFormat;
import java.util.Date;

/** Owns native Messages presentation and message-state actions. */
public final class JanusMessagesScreen {
    private JanusMessagesScreen() {}

    public interface Host {
        Activity activity();
        JanusApiClient api();
        String profile();
        void runIo(Runnable work);
        void runUi(Runnable work);
        void replyInChat(String message);
    }

    public static void render(Host host, LinearLayout content) {
        if (host == null || content == null) return;
        Activity a = host.activity();
        content.addView(text(a, "Messages", 28, true), full());
        content.addView(text(a, "Useful JANUS-originated questions, conclusions, warnings and follow-ups. Routine internal processing belongs in Observe.", 13, false), full());
        LinearLayout list = vertical(a);
        ScrollView scroll = new ScrollView(a);
        scroll.addView(list, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        Button refresh = button(a, "Refresh");
        refresh.setOnClickListener(v -> load(host, list));
        content.addView(refresh, full());
        load(host, list);
    }

    private static void load(Host host, LinearLayout list) {
        Activity a = host.activity();
        list.removeAllViews();
        list.addView(text(a, "Loading…", 14, false));
        host.runIo(() -> {
            JanusApiClient.Response r = host.api().get("/desktop/messages?username=" + enc(host.profile()) + "&limit=80", true);
            host.runUi(() -> {
                list.removeAllViews();
                if (!r.ok()) { list.addView(text(a, "Messages could not be loaded.", 14, false)); return; }
                try {
                    JSONArray items = new JSONObject(r.body).optJSONArray("items");
                    if (items == null || items.length() == 0) { list.addView(text(a, "No JANUS messages yet.", 15, false)); return; }
                    for (int i = 0; i < items.length(); i++) {
                        JSONObject x = items.getJSONObject(i);
                        long id = x.optLong("id", 0);
                        String detail = x.optString("detail", x.optString("message", ""));
                        LinearLayout card = card(a);
                        card.addView(text(a, ("unread".equals(x.optString("state")) ? "New · " : "") + x.optString("message_type", "Message"), 14, true));
                        card.addView(text(a, formatTime(x.opt("created_at")), 12, false));
                        card.addView(text(a, detail, 15, false));
                        LinearLayout actions = horizontal(a);
                        Button answer = button(a, "Answer in Chat");
                        Button read = button(a, "Read");
                        Button dismiss = button(a, "Dismiss");
                        answer.setOnClickListener(v -> { setState(host, id, "read"); host.replyInChat("Regarding your message:\n“" + clip(detail, 500) + "”\n\n"); });
                        read.setOnClickListener(v -> { setState(host, id, "read"); load(host, list); });
                        dismiss.setOnClickListener(v -> { setState(host, id, "dismissed"); load(host, list); });
                        actions.addView(answer, weight()); actions.addView(read, weight()); actions.addView(dismiss, weight());
                        card.addView(actions, full()); list.addView(card, full());
                    }
                } catch (Exception e) { list.addView(text(a, "Messages could not be displayed.", 14, false)); }
            });
        });
    }

    private static void setState(Host host, long id, String state) {
        if (id <= 0) return;
        host.runIo(() -> { JSONObject body = new JSONObject(); try { body.put("profile_id", host.profile()); body.put("state", state); } catch (Exception ignored) {} host.api().post("/desktop/messages/" + id + "/state", body.toString(), true); });
    }

    private static LinearLayout vertical(Activity a) { LinearLayout x = new LinearLayout(a); x.setOrientation(LinearLayout.VERTICAL); return x; }
    private static LinearLayout horizontal(Activity a) { LinearLayout x = new LinearLayout(a); x.setOrientation(LinearLayout.HORIZONTAL); return x; }
    private static LinearLayout card(Activity a) { LinearLayout x = vertical(a); int p = dp(a, 12); x.setPadding(p,p,p,p); LinearLayout.LayoutParams lp = full(); lp.setMargins(0,dp(a,6),0,dp(a,6)); x.setLayoutParams(lp); x.setBackgroundColor(0x181C8CFF); return x; }
    private static TextView text(Activity a, String s, int sp, boolean bold) { TextView v = new TextView(a); v.setText(s); v.setTextSize(sp); v.setTextColor(0xffe8eef7); if (bold) v.setTypeface(Typeface.DEFAULT_BOLD); v.setPadding(dp(a,4),dp(a,5),dp(a,4),dp(a,5)); return v; }
    private static Button button(Activity a, String s) { Button b = new Button(a); b.setText(s); b.setAllCaps(false); b.setGravity(Gravity.CENTER); return b; }
    private static LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1,-2); }
    private static LinearLayout.LayoutParams weight() { return new LinearLayout.LayoutParams(0,-2,1); }
    private static int dp(Activity a, int n) { return Math.round(n * a.getResources().getDisplayMetrics().density); }
    private static String enc(String s) { try { return java.net.URLEncoder.encode(s == null ? "" : s, "UTF-8"); } catch (Exception e) { return ""; } }
    private static String clip(String s, int n) { if (s == null) return ""; return s.length() <= n ? s : s.substring(0,n) + "…"; }
    private static String formatTime(Object raw) { if (raw == null) return ""; if (raw instanceof Number) { long n = ((Number) raw).longValue(); if (n < 100000000000L) n *= 1000L; return DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date(n)); } return String.valueOf(raw); }
}
