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

/**
 * Explicit, read-only owner for the JANUS Front/stream surface.
 *
 * This renderer does not search or rewrite the live Android view tree, does not
 * reflect private Activity fields and does not install delayed/global-layout
 * callbacks. The hosting Activity supplies the content container and runtime
 * dependencies directly.
 */
public final class JanusStreamScreen {
    private JanusStreamScreen() {}

    public interface Host {
        Activity activity();
        JanusApiClient api();
        void runIo(Runnable work);
        void runUi(Runnable work);
        JSONObject localRecursiveSnapshot();
    }

    public static void render(Host host, LinearLayout content) {
        if (host == null || content == null) return;
        Activity a = host.activity();
        content.addView(text(a, "Stream", 28, true), full());
        content.addView(text(a,
                "Read-only externalizable activity from JANUS Front, the single integrated stream that receives Left and Right before Interface. Hidden chain-of-thought is never exposed.",
                13, false), full());

        LinearLayout list = vertical(a);
        ScrollView scroll = new ScrollView(a);
        scroll.addView(list, full());
        content.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        Button refresh = button(a, "Refresh stream snapshot");
        refresh.setOnClickListener(v -> load(host, list));
        content.addView(refresh, full());
        load(host, list);
    }

    private static void load(Host host, LinearLayout list) {
        Activity a = host.activity();
        list.removeAllViews();
        list.addView(text(a, "Loading Front stream…", 14, false));
        host.runIo(() -> {
            JSONObject local = new JSONObject();
            try {
                JSONObject supplied = host.localRecursiveSnapshot();
                if (supplied != null) local = supplied;
            } catch (Exception ignored) {}
            JanusApiClient.Response response = host.api().get("/desktop/stream-observe?limit=160", true);
            JSONObject server = new JSONObject();
            try { if (response.ok()) server = new JSONObject(response.body); } catch (Exception ignored) {}
            final JSONObject localFinal = local;
            final JSONObject serverFinal = server;
            final boolean serverOk = response.ok();
            host.runUi(() -> renderSnapshot(a, list, localFinal, serverFinal, serverOk));
        });
    }

    private static void renderSnapshot(Activity a, LinearLayout list, JSONObject local, JSONObject server, boolean serverOk) {
        list.removeAllViews();
        JSONObject localFront = local.optJSONObject("cores") == null ? null : local.optJSONObject("cores").optJSONObject("front");
        if (localFront != null) addStateCard(a, list, "This device · Front", localFront, "Local recursive Front state");

        JSONObject current = server.optJSONObject("current");
        JSONObject globalFront = current == null ? null : current.optJSONObject("recursive_janus");
        if (globalFront != null) addStateCard(a, list, "Global JANUS · Front", globalFront,
                "Server recursive Front state · phase " + server.optString("phase", "unknown"));

        JSONArray items = server.optJSONArray("items");
        if (items != null) {
            for (int i = 0; i < items.length(); i++) {
                JSONObject x = items.optJSONObject(i);
                if (x == null) continue;
                LinearLayout card = card(a);
                card.addView(text(a, "Front · " + pretty(x.optString("event_type", "event")), 13, true));
                card.addView(text(a, x.optString("detail", ""), 15, false));
                card.addView(text(a, formatTime(x.opt("created_at")) + " · " + x.optString("mode", "foreground"), 12, false));
                list.addView(card, full());
            }
        }

        if (!serverOk) {
            list.addView(text(a, "Global stream is temporarily unavailable. Local Front state remains readable.", 13, false));
        } else if (list.getChildCount() == 0) {
            list.addView(text(a, "No stream activity retained yet.", 15, false));
        }
    }

    private static void addStateCard(Activity a, LinearLayout list, String title, JSONObject x, String subtitle) {
        LinearLayout card = card(a);
        card.addView(text(a, title, 14, true));
        card.addView(text(a, subtitle, 12, false));
        card.addView(text(a,
                "Fano: d" + x.optInt("active_direction", 0) + " " + x.optString("active_faculty", "reference")
                        + " · cycles " + x.optLong("cycles", 0)
                        + " · revisions " + x.optLong("revision_count", 0)
                        + " · peer turns " + x.optLong("peer_turn_count", 0)
                        + " · quiescent " + x.optLong("quiescent_count", 0),
                13, false));
        String conclusion = x.optString("conclusion", "");
        if (!conclusion.isBlank()) card.addView(text(a, conclusion, 14, false));
        list.addView(card, full());
    }

    private static LinearLayout vertical(Activity a) {
        LinearLayout x = new LinearLayout(a);
        x.setOrientation(LinearLayout.VERTICAL);
        return x;
    }

    private static LinearLayout card(Activity a) {
        LinearLayout x = vertical(a);
        int p = dp(a, 12);
        x.setPadding(p, p, p, p);
        LinearLayout.LayoutParams lp = full();
        lp.setMargins(0, dp(a, 6), 0, dp(a, 6));
        x.setLayoutParams(lp);
        x.setBackgroundColor(0x181C8CFF);
        return x;
    }

    private static TextView text(Activity a, String s, int sp, boolean bold) {
        TextView v = new TextView(a);
        v.setText(s);
        v.setTextSize(sp);
        if (bold) v.setTypeface(Typeface.DEFAULT_BOLD);
        v.setPadding(dp(a, 4), dp(a, 5), dp(a, 4), dp(a, 5));
        return v;
    }

    private static Button button(Activity a, String s) {
        Button b = new Button(a);
        b.setText(s);
        b.setAllCaps(false);
        b.setGravity(Gravity.CENTER);
        return b;
    }

    private static LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private static int dp(Activity a, int n) { return Math.round(n * a.getResources().getDisplayMetrics().density); }
    private static String pretty(String s) { return s == null ? "" : s.replace('_', ' '); }

    private static String formatTime(Object raw) {
        if (raw instanceof Number) {
            long n = ((Number) raw).longValue();
            if (n < 100000000000L) n *= 1000L;
            return DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date(n));
        }
        return String.valueOf(raw == null ? "" : raw);
    }
}
