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
 * Product-surface readability layer for JANUS Android v0.87.
 *
 * Keeps cognition/network behavior stable while progressively moving visual and
 * human-readable presentation policy out of MainActivity.
 */
public final class JanusProductPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusProductPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) polishTree(activity, root);
        });
    }

    private static void polishTree(Activity activity, View view) {
        if (view instanceof TextView) polishText(activity, (TextView) view);
        if (view instanceof Button) polishButton(activity, (Button) view);
        if (view instanceof LinearLayout) polishCard(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) polishTree(activity, g.getChildAt(i));
        }
    }

    private static void polishText(Activity activity, TextView t) {
        String s = String.valueOf(t.getText());
        if ("Device-local continuity".equals(s)) {
            t.setText("This device · Local continuity"); sectionTitle(activity, t);
        } else if ("Server continuity".equals(s)) {
            t.setText("Global JANUS · Durable continuity"); sectionTitle(activity, t);
        } else if ("Research Workspace".equals(s)) {
            t.setText("Research"); screenTitle(t);
        } else if ("Background Research".equals(s)) {
            t.setText("Background research"); screenTitle(t);
        } else if ("Maintenance Review".equals(s)) {
            t.setText("Maintenance"); screenTitle(t);
        } else if ("System Status".equals(s)) {
            t.setText("System status"); screenTitle(t);
        } else if ("Messages".equals(s)) {
            screenTitle(t);
        } else if ("Account".equals(s)) {
            screenTitle(t);
        } else if (s.startsWith("ESTABLISHED / AUDITED")) {
            t.setText("Established / audited"); sectionTitle(activity, t);
        } else if (s.startsWith("HYPOTHESES / PROVISIONAL")) {
            t.setText("Hypotheses / provisional"); sectionTitle(activity, t);
        } else if (s.startsWith("NEGATIVE RESULTS")) {
            t.setText("Negative results"); sectionTitle(activity, t);
        } else if (s.startsWith("OPEN QUESTIONS")) {
            t.setText("Open questions"); sectionTitle(activity, t);
        } else if (s.startsWith("PROPOSED TESTS")) {
            t.setText("Proposed tests"); sectionTitle(activity, t);
        } else if (s.startsWith("Useful JANUS-originated questions")) {
            t.setText("Questions, conclusions, warnings and follow-ups JANUS has chosen to surface. Routine internal processing stays in Observe.");
            t.setTextSize(13);
        } else if (s.startsWith("Sign in to continue your JANUS identity")) {
            t.setText("Continue your JANUS identity, memory, conversations and research across devices.");
            t.setTextSize(15);
            t.setPadding(t.getPaddingLeft(), dp(activity, 4), t.getPaddingRight(), dp(activity, 14));
        } else if (s.startsWith("Password and Google sign-in use the same JANUS account.")) {
            t.setText("Password and Google sign-in lead to the same JANUS account. Google confirms identity; JANUS retains its own account continuity.");
            t.setTextSize(12);
        } else if (s.startsWith("Deterministic local cycles use zero model/API calls.")) {
            t.setText("Local JANUS background cycles are deterministic and use no model/API calls. Paid background language reflection remains off by default. These controls affect this device only and cannot overwrite protected global identity or core state.");
            t.setTextSize(13);
        } else if (s.startsWith("JANUS may propose maintenance")) {
            t.setText("JANUS can recommend maintenance, but approval only authorizes manual work by you and ChatGPT. JANUS cannot edit its own source, install packages, switch models, change APIs, or deploy itself.");
            t.setTextSize(13);
        } else if (s.startsWith("Loading")) {
            t.setAlpha(.72f);
        } else if (s.contains("could not be displayed") || s.contains("could not be loaded")) {
            t.setText("This information is temporarily unavailable. You can retry without losing local JANUS state.");
            t.setAlpha(.85f);
        }
    }

    private static void polishButton(Activity activity, Button b) {
        String s = String.valueOf(b.getText());
        if (s.startsWith("Cores\n")) b.setText("JANUS · Cores\nSee the 11-core local/global runtime and architecture");
        else if (s.startsWith("Memory\n")) b.setText("JANUS · Memory\nLocal continuity and durable global memory");
        else if (s.startsWith("Activity\n")) b.setText("JANUS · Activity\nConversation, decisions and durable events");
        else if (s.startsWith("System status\n")) b.setText("System · Status\nHealth, sync, persistence and capability checks");
        else if (s.startsWith("Compatibility\n")) b.setText("System · Compatibility\nProtocol and deployed capability negotiation");
        else if (s.startsWith("Research workspace\n")) b.setText("Research · Workspace\nEvidence, hypotheses, negative results and tests");
        else if (s.startsWith("Artifacts\n")) b.setText("Research · Artifacts\nReports, digests and working files");
        else if (s.startsWith("Background research\n")) b.setText("Research · Background\nProvenance, usefulness and governed external compute");
        else if (s.startsWith("Maintenance review\n")) b.setText("System · Maintenance\nOwner-gated proposals, decisions and schedule");
        else if (s.startsWith("Settings\n")) b.setText("App · Settings\nAppearance, local background operation and Observe");
        else if (s.startsWith("Account\n")) b.setText("Account\nProfile, verification, sessions and account lifecycle");
        else if ("30s".equals(s)) b.setText("Active · 30s");
        else if ("1m".equals(s)) b.setText("Balanced · 1m");
        else if ("2m".equals(s)) b.setText("Battery saver · 2m");
        else if ("5m".equals(s)) b.setText("Low activity · 5m");
        else if ("Answer in Chat".equals(s)) b.setText("Reply in Chat");
        else if ("Read".equals(s)) b.setText("Mark read");

        String label = String.valueOf(b.getText());
        if (label.contains("\n")) {
            b.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
            b.setTextSize(14);
            b.setMinHeight(dp(activity, 64));
        }
        if ("Sign in".equals(label) || "Create account".equals(label)) {
            b.setMinHeight(dp(activity, 52));
        } else if ("Continue with Google".equals(label)) {
            b.setMinHeight(dp(activity, 52));
        } else if (label.toLowerCase(Locale.ROOT).contains("delete account")) {
            b.setTextColor(Color.rgb(183, 28, 28));
            b.setBackgroundTintList(ColorStateList.valueOf(isDark(activity) ? Color.rgb(54, 37, 39) : Color.rgb(255, 238, 238)));
        } else if (label.toLowerCase(Locale.ROOT).contains("sign out")) {
            b.setMinHeight(dp(activity, 48));
        }
    }

    private static void polishCard(Activity activity, LinearLayout card) {
        if (card.getChildCount() == 0 || !(card.getChildAt(0) instanceof TextView)) return;
        TextView first = (TextView) card.getChildAt(0);
        String title = String.valueOf(first.getText());
        if ("Healthy".equals(title)) {
            accentCard(activity, card, Color.rgb(46, 125, 50));
        } else if ("Reduced capability".equals(title)) {
            accentCard(activity, card, Color.rgb(230, 135, 0));
        } else if ("Needs attention".equals(title)) {
            accentCard(activity, card, Color.rgb(183, 28, 28));
        }

        if (title.startsWith("New · ")) {
            first.setText("New · " + humanMessageType(title.substring(6)));
            accentCard(activity, card, Color.rgb(25, 118, 210));
            card.setElevation(dp(activity, 2));
        } else if (looksLikeMessageType(title)) {
            first.setText(humanMessageType(title));
        }

        if (title.matches("(?i)(trace|working|episodic|core)\\s*·.*")) {
            String level = title.substring(0, title.indexOf('·')).trim().toLowerCase(Locale.ROOT);
            String human;
            switch (level) {
                case "core": human = "Core memory · protected continuity"; break;
                case "episodic": human = "Episodic memory · durable event"; break;
                case "working": human = "Working memory · active context"; break;
                default: human = "Trace memory · recent signal"; break;
            }
            first.setText(human + title.substring(title.indexOf('·')));
        }
    }

    private static boolean looksLikeMessageType(String title) {
        String s = title.toLowerCase(Locale.ROOT).trim();
        return s.equals("question") || s.equals("conclusion") || s.equals("warning")
                || s.equals("suggestion") || s.equals("maintenance") || s.equals("research")
                || s.equals("research finding") || s.equals("follow-up") || s.equals("message");
    }

    private static String humanMessageType(String raw) {
        String s = raw == null ? "Message" : raw.trim().replace('_', ' ');
        if (s.isEmpty()) return "Message";
        String lower = s.toLowerCase(Locale.ROOT);
        if (lower.contains("question")) return "Question";
        if (lower.contains("warning")) return "Warning";
        if (lower.contains("conclusion")) return "Conclusion";
        if (lower.contains("maintenance")) return "Maintenance";
        if (lower.contains("research")) return "Research finding";
        if (lower.contains("suggest")) return "Suggestion";
        if (lower.contains("follow")) return "Follow-up";
        return Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }

    private static void screenTitle(TextView t) {
        t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    }

    private static void sectionTitle(Activity activity, TextView t) {
        t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        t.setTextSize(15);
        t.setPadding(t.getPaddingLeft(), dp(activity, 12), t.getPaddingRight(), dp(activity, 6));
    }

    private static void accentCard(Activity activity, LinearLayout card, int accent) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(isDark(activity) ? Color.rgb(38, 38, 40) : Color.rgb(248, 248, 250));
        d.setCornerRadius(dp(activity, 16));
        d.setStroke(dp(activity, 2), accent);
        card.setBackground(d);
    }

    private static boolean isDark(Activity activity) {
        int mask = activity.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        return mask == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }

    private static int dp(Activity activity, int v) {
        return Math.round(v * activity.getResources().getDisplayMetrics().density);
    }
}
