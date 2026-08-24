package com.vardath.janus;

import android.app.Activity;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Collections;
import java.util.Locale;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * v0.88 screen-state and high-level product presentation extraction.
 *
 * This layer intentionally contains no networking or JANUS cognition logic. It turns
 * dynamically rebuilt native screens into clearer loading, empty, error, inbox and
 * account states while preserving MainActivity behaviour and server_v2 contracts.
 */
public final class JanusScreenStatePolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusScreenStatePolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) walk(activity, root);
        });
    }

    private static void walk(Activity activity, View view) {
        if (view instanceof TextView) polishText(activity, (TextView) view);
        if (view instanceof Button) polishButton(activity, (Button) view);
        if (view instanceof LinearLayout) polishCard(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) walk(activity, g.getChildAt(i));
        }
    }

    private static void polishText(Activity activity, TextView t) {
        String s = String.valueOf(t.getText()).trim();
        if (s.isEmpty()) return;

        if (s.equals("Loading…") || s.startsWith("Loading ") || s.startsWith("Checking ")) {
            t.setText("Working…");
            t.setTextSize(14);
            t.setAlpha(.72f);
            t.setGravity(Gravity.CENTER_HORIZONTAL);
            t.setPadding(t.getPaddingLeft(), dp(activity, 18), t.getPaddingRight(), dp(activity, 18));
            return;
        }

        if (s.startsWith("No JANUS messages yet")) {
            t.setText("No surfaced messages yet\nJANUS will place useful questions, conclusions, warnings and follow-ups here when there is something worth interrupting you for.");
            emptyState(activity, t);
            return;
        }
        if (s.startsWith("No observable core activity")) {
            t.setText("No observable activity in this snapshot\nRefresh when you want a newer externalizable view. JANUS does not move this screen while you are reading it.");
            emptyState(activity, t);
            return;
        }
        if (s.contains("temporarily unavailable") || s.contains("could not be displayed") || s.contains("could not be loaded") || s.startsWith("HTTP ")) {
            t.setText("Temporarily unavailable\nYour local JANUS state is still intact. Retry this screen when the connection is available.");
            stateText(activity, t, Color.rgb(230, 135, 0));
            return;
        }

        if (s.startsWith("Useful JANUS-originated questions")) {
            t.setText("JANUS inbox\nOnly useful surfaced questions, conclusions, warnings and follow-ups appear here. Routine internal processing stays in Observe.");
            t.setTextSize(13);
        } else if (s.startsWith("Continue your JANUS identity")) {
            t.setText("Your JANUS continuity\nSign in to reconnect this device with your global identity, durable memory, conversations and research.");
            t.setTextSize(15);
        } else if (s.startsWith("Password and Google sign-in lead")) {
            t.setText("Password and Google are two ways to confirm the same JANUS account. Your JANUS identity and continuity remain server-owned, not Google-owned.");
            t.setTextSize(12);
        }
    }

    private static void polishButton(Activity activity, Button b) {
        String label = String.valueOf(b.getText()).trim();
        String lower = label.toLowerCase(Locale.ROOT);

        if ("Dismiss".equals(label)) b.setText("Dismiss");
        else if ("Refresh".equals(label)) b.setText("Refresh inbox");
        else if ("Refresh snapshot".equals(label)) b.setText("Refresh snapshot");
        else if ("Verify / resend email".equals(label)) b.setText("Verify email");
        else if ("Forgot password".equals(label)) b.setText("Forgot password?");

        label = String.valueOf(b.getText()).trim();
        lower = label.toLowerCase(Locale.ROOT);
        if (lower.contains("delete account")) {
            b.setTextColor(Color.rgb(183, 28, 28));
            b.setBackgroundTintList(ColorStateList.valueOf(isDark(activity) ? Color.rgb(56, 35, 38) : Color.rgb(255, 238, 238)));
            b.setMinHeight(dp(activity, 50));
        } else if (lower.contains("sign out all")) {
            b.setBackgroundTintList(ColorStateList.valueOf(isDark(activity) ? Color.rgb(52, 46, 38) : Color.rgb(255, 248, 230)));
        }
    }

    private static void polishCard(Activity activity, LinearLayout card) {
        if (card.getChildCount() == 0 || !(card.getChildAt(0) instanceof TextView)) return;
        TextView first = (TextView) card.getChildAt(0);
        String title = String.valueOf(first.getText()).trim();

        if (title.startsWith("New · ")) {
            accent(card, activity, Color.rgb(25, 118, 210));
            first.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
            card.setElevation(dp(activity, 3));
        } else if (title.equals("Delivery status")) {
            accent(card, activity, Color.rgb(96, 125, 139));
        } else if (title.equals("Healthy")) {
            accent(card, activity, Color.rgb(46, 125, 50));
        } else if (title.equals("Reduced capability")) {
            accent(card, activity, Color.rgb(230, 135, 0));
        } else if (title.equals("Needs attention")) {
            accent(card, activity, Color.rgb(183, 28, 28));
        }
    }

    private static void emptyState(Activity activity, TextView t) {
        t.setGravity(Gravity.CENTER);
        t.setTextSize(14);
        t.setAlpha(.78f);
        t.setPadding(dp(activity, 18), dp(activity, 28), dp(activity, 18), dp(activity, 28));
    }

    private static void stateText(Activity activity, TextView t, int accent) {
        t.setTextSize(14);
        t.setPadding(dp(activity, 14), dp(activity, 14), dp(activity, 14), dp(activity, 14));
        GradientDrawable d = new GradientDrawable();
        d.setColor(isDark(activity) ? Color.rgb(45, 42, 36) : Color.rgb(255, 249, 232));
        d.setCornerRadius(dp(activity, 14));
        d.setStroke(dp(activity, 1), accent);
        t.setBackground(d);
    }

    private static void accent(LinearLayout card, Activity activity, int color) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(isDark(activity) ? Color.rgb(39, 39, 42) : Color.rgb(249, 249, 251));
        d.setCornerRadius(dp(activity, 16));
        d.setStroke(dp(activity, 2), color);
        card.setBackground(d);
    }

    private static boolean isDark(Activity activity) {
        int mask = activity.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        return mask == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }

    private static int dp(Activity activity, int value) {
        return Math.round(value * activity.getResources().getDisplayMetrics().density);
    }
}
