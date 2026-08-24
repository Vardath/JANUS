package com.vardath.janus;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.net.URI;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * v0.91 Chat citation/source presentation extraction.
 *
 * The current server contract returns structured source metadata which MainActivity
 * still flattens into a predictable text appendix. This layer reverses only that
 * presentation flattening at render time: answer text remains clean, source records
 * become separate tappable cards, and no cognition/network/server behavior changes.
 */
public final class JanusSourcePolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final String TAG_DONE = "janus-source-cards-v091";
    private JanusSourcePolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) walk(activity, root);
        });
    }

    private static void walk(Activity activity, View view) {
        if (view instanceof LinearLayout) enhanceJanusAnswer(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) walk(activity, group.getChildAt(i));
        }
    }

    private static void enhanceJanusAnswer(Activity activity, LinearLayout card) {
        if (TAG_DONE.equals(card.getTag()) || card.getChildCount() < 2) return;
        if (!(card.getChildAt(0) instanceof TextView) || !(card.getChildAt(1) instanceof TextView)) return;
        TextView speaker = (TextView) card.getChildAt(0);
        if (!"JANUS".contentEquals(speaker.getText())) return;
        TextView body = (TextView) card.getChildAt(1);
        String raw = String.valueOf(body.getText());
        int split = raw.indexOf("\n\nSources:");
        if (split < 0) return;

        String answer = raw.substring(0, split).trim();
        String appendix = raw.substring(split + "\n\nSources:".length()).trim();
        List<Source> sources = parseSources(appendix);
        if (sources.isEmpty()) return;

        card.setTag(TAG_DONE);
        body.setText(answer);

        LinearLayout sourcePanel = new LinearLayout(activity);
        sourcePanel.setOrientation(LinearLayout.VERTICAL);
        sourcePanel.setPadding(dp(activity, 10), dp(activity, 8), dp(activity, 10), dp(activity, 8));
        GradientDrawable panelBg = rounded(activity, isDark(activity) ? Color.rgb(31, 34, 38) : Color.rgb(246, 248, 251), 14);
        panelBg.setStroke(dp(activity, 1), isDark(activity) ? Color.rgb(70, 76, 84) : Color.rgb(213, 220, 229));
        sourcePanel.setBackground(panelBg);

        TextView heading = new TextView(activity);
        heading.setText("Sources · " + sources.size());
        heading.setTextSize(13);
        heading.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        heading.setTextColor(isDark(activity) ? Color.rgb(225, 230, 236) : Color.rgb(45, 53, 61));
        heading.setPadding(dp(activity, 4), 0, dp(activity, 4), dp(activity, 5));
        sourcePanel.addView(heading, new LinearLayout.LayoutParams(-1, -2));

        for (int i = 0; i < sources.size(); i++) {
            Source source = sources.get(i);
            LinearLayout row = new LinearLayout(activity);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(dp(activity, 10), dp(activity, 8), dp(activity, 10), dp(activity, 8));
            GradientDrawable rowBg = rounded(activity, isDark(activity) ? Color.rgb(42, 45, 50) : Color.WHITE, 12);
            rowBg.setStroke(dp(activity, 1), isDark(activity) ? Color.rgb(67, 73, 80) : Color.rgb(224, 228, 234));
            row.setBackground(rowBg);
            LinearLayout.LayoutParams rowLp = new LinearLayout.LayoutParams(-1, -2);
            rowLp.setMargins(0, i == 0 ? 0 : dp(activity, 5), 0, 0);

            TextView title = new TextView(activity);
            title.setText((i + 1) + ". " + source.title);
            title.setTextSize(13);
            title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
            title.setTextColor(isDark(activity) ? Color.WHITE : Color.rgb(35, 42, 50));
            row.addView(title, new LinearLayout.LayoutParams(-1, -2));

            String domain = domainOf(source.url);
            if (!domain.isEmpty()) {
                TextView meta = new TextView(activity);
                meta.setText(domain + (source.url.isEmpty() ? "" : " · Tap to open"));
                meta.setTextSize(11);
                meta.setTextColor(isDark(activity) ? Color.rgb(170, 182, 196) : Color.rgb(91, 103, 117));
                meta.setPadding(0, dp(activity, 2), 0, 0);
                row.addView(meta, new LinearLayout.LayoutParams(-1, -2));
            }

            if (!source.url.isEmpty()) {
                row.setClickable(true);
                row.setFocusable(true);
                row.setOnClickListener(v -> openUrl(activity, source.url));
            }
            sourcePanel.addView(row, rowLp);
        }

        int actionIndex = findActionRow(card);
        if (actionIndex >= 0) card.addView(sourcePanel, actionIndex, fullWithMargins(activity));
        else card.addView(sourcePanel, fullWithMargins(activity));
    }

    private static List<Source> parseSources(String appendix) {
        List<Source> out = new ArrayList<>();
        if (appendix == null || appendix.isBlank()) return out;
        for (String line : appendix.split("\\n")) {
            String s = line.trim();
            if (s.startsWith("•")) s = s.substring(1).trim();
            if (s.isEmpty()) continue;
            String title = s;
            String url = "";
            int marker = s.lastIndexOf(" — http");
            if (marker >= 0) {
                title = s.substring(0, marker).trim();
                url = s.substring(marker + 3).trim();
            } else if (s.startsWith("http://") || s.startsWith("https://")) {
                url = s;
                title = domainOf(url);
            }
            if (title.isEmpty()) title = url.isEmpty() ? "Source" : domainOf(url);
            out.add(new Source(title, url));
            if (out.size() >= 8) break;
        }
        return out;
    }

    private static int findActionRow(LinearLayout card) {
        for (int i = 2; i < card.getChildCount(); i++) {
            View v = card.getChildAt(i);
            if (v instanceof LinearLayout) {
                LinearLayout row = (LinearLayout) v;
                for (int j = 0; j < row.getChildCount(); j++) {
                    if (row.getChildAt(j) instanceof android.widget.Button) return i;
                }
            }
        }
        return -1;
    }

    private static void openUrl(Activity activity, String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            activity.startActivity(intent);
        } catch (Exception ignored) {}
    }

    private static String domainOf(String url) {
        if (url == null || url.isBlank()) return "";
        try {
            String host = URI.create(url.trim()).getHost();
            if (host == null) return "";
            return host.startsWith("www.") ? host.substring(4) : host;
        } catch (Exception ignored) { return ""; }
    }

    private static LinearLayout.LayoutParams fullWithMargins(Activity activity) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, dp(activity, 4), 0, dp(activity, 5));
        return lp;
    }

    private static GradientDrawable rounded(Activity activity, int color, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(activity, radiusDp));
        return d;
    }

    private static boolean isDark(Activity activity) {
        int mask = activity.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        return mask == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }

    private static int dp(Activity activity, int value) {
        return Math.round(value * activity.getResources().getDisplayMetrics().density);
    }

    private static final class Source {
        final String title;
        final String url;
        Source(String title, String url) { this.title = title; this.url = url; }
    }
}
