package com.vardath.janus;

import android.app.Activity;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Collections;
import java.util.Locale;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * v0.89 feature-specific presentation and local filtering.
 *
 * This layer adds functional client-side Memory search/tier filtering and improves
 * Research evidence/category and Account/session presentation without changing
 * server_v2 contracts or JANUS cognition/routing behavior.
 */
public final class JanusFeaturePolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final int TAG_MEMORY_TOOLS = 0x4A8901;
    private JanusFeaturePolish() {}

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
        if (view instanceof LinearLayout) {
            LinearLayout group = (LinearLayout) view;
            maybeInjectMemoryTools(activity, group);
            polishResearchCard(activity, group);
            polishAccountGroup(activity, group);
        }
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) walk(activity, g.getChildAt(i));
        }
    }

    private static void maybeInjectMemoryTools(Activity activity, LinearLayout group) {
        if (group.getTag(TAG_MEMORY_TOOLS) != null) return;
        int memoryTitle = childTextIndex(group, "Memory");
        if (memoryTitle < 0 || group.getChildCount() < 2) return;

        LinearLayout tools = new LinearLayout(activity);
        tools.setOrientation(LinearLayout.VERTICAL);
        tools.setPadding(dp(activity, 0), dp(activity, 8), dp(activity, 0), dp(activity, 10));

        EditText search = new EditText(activity);
        search.setHint("Search visible memory");
        search.setSingleLine(true);
        search.setTextSize(14);
        search.setPadding(dp(activity, 14), 0, dp(activity, 14), 0);
        GradientDrawable searchBg = new GradientDrawable();
        searchBg.setColor(isDark(activity) ? Color.rgb(41, 41, 44) : Color.rgb(247, 247, 249));
        searchBg.setCornerRadius(dp(activity, 14));
        searchBg.setStroke(dp(activity, 1), isDark(activity) ? Color.rgb(86, 86, 92) : Color.rgb(210, 210, 216));
        search.setBackground(searchBg);
        tools.addView(search, new LinearLayout.LayoutParams(-1, dp(activity, 48)));

        HorizontalScrollView scroll = new HorizontalScrollView(activity);
        scroll.setHorizontalScrollBarEnabled(false);
        LinearLayout chips = new LinearLayout(activity);
        chips.setOrientation(LinearLayout.HORIZONTAL);
        String[] tiers = new String[]{"All", "Trace", "Working", "Episodic", "Core"};
        final String[] selected = new String[]{"all"};
        for (String tier : tiers) {
            Button chip = new Button(activity);
            chip.setAllCaps(false);
            chip.setText(tier);
            chip.setTextSize(12);
            chip.setMinHeight(0);
            chip.setMinimumHeight(0);
            chip.setPadding(dp(activity, 12), dp(activity, 4), dp(activity, 12), dp(activity, 4));
            chip.setOnClickListener(v -> {
                selected[0] = tier.toLowerCase(Locale.ROOT);
                applyMemoryFilter(group, search.getText().toString(), selected[0]);
                for (int i = 0; i < chips.getChildCount(); i++) {
                    View c = chips.getChildAt(i);
                    if (c instanceof Button) styleChip(activity, (Button)c, c == v);
                }
            });
            styleChip(activity, chip, "All".equals(tier));
            chips.addView(chip, new LinearLayout.LayoutParams(-2, dp(activity, 38)));
        }
        scroll.addView(chips, new HorizontalScrollView.LayoutParams(-2, -1));
        tools.addView(scroll, new LinearLayout.LayoutParams(-1, dp(activity, 46)));

        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                applyMemoryFilter(group, String.valueOf(s), selected[0]);
            }
            @Override public void afterTextChanged(Editable s) {}
        });

        group.addView(tools, Math.min(memoryTitle + 1, group.getChildCount()));
        group.setTag(TAG_MEMORY_TOOLS, Boolean.TRUE);
    }

    private static void applyMemoryFilter(View root, String query, String tier) {
        String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        applyMemoryFilterRecursive(root, q, tier == null ? "all" : tier);
    }

    private static void applyMemoryFilterRecursive(View view, String q, String tier) {
        if (view instanceof LinearLayout && isMemoryCard((LinearLayout)view)) {
            String text = collectText((ViewGroup)view).toLowerCase(Locale.ROOT);
            boolean tierMatch = "all".equals(tier) || text.contains(tier + " memory");
            boolean queryMatch = q.isEmpty() || text.contains(q);
            view.setVisibility(tierMatch && queryMatch ? View.VISIBLE : View.GONE);
            return;
        }
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup)view;
            for (int i = 0; i < g.getChildCount(); i++) applyMemoryFilterRecursive(g.getChildAt(i), q, tier);
        }
    }

    private static boolean isMemoryCard(LinearLayout card) {
        if (card.getChildCount() == 0) return false;
        String text = collectText(card).toLowerCase(Locale.ROOT);
        return text.contains("trace memory") || text.contains("working memory")
                || text.contains("episodic memory") || text.contains("core memory");
    }

    private static void polishResearchCard(Activity activity, LinearLayout card) {
        if (card.getChildCount() == 0) return;
        String text = collectText(card);
        if (text.contains("Evidence entries:")) {
            for (int i = 0; i < card.getChildCount(); i++) {
                View v = card.getChildAt(i);
                if (v instanceof TextView) {
                    TextView t = (TextView)v;
                    String s = String.valueOf(t.getText()).trim();
                    if (s.startsWith("Evidence entries:")) {
                        String count = s.substring("Evidence entries:".length()).trim();
                        t.setText("Evidence · " + count + " entr" + ("1".equals(count) ? "y" : "ies"));
                        t.setTextSize(12);
                        t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
                        t.setPadding(dp(activity, 10), dp(activity, 5), dp(activity, 10), dp(activity, 5));
                        GradientDrawable d = new GradientDrawable();
                        d.setColor(isDark(activity) ? Color.rgb(38, 52, 58) : Color.rgb(232, 244, 248));
                        d.setCornerRadius(dp(activity, 12));
                        t.setBackground(d);
                    }
                }
            }
        }
        String lower = text.toLowerCase(Locale.ROOT);
        if (lower.contains("established / audited")) accent(card, activity, Color.rgb(46, 125, 50));
        else if (lower.contains("hypotheses / provisional")) accent(card, activity, Color.rgb(2, 119, 189));
        else if (lower.contains("negative results")) accent(card, activity, Color.rgb(117, 117, 117));
        else if (lower.contains("open questions")) accent(card, activity, Color.rgb(230, 135, 0));
        else if (lower.contains("proposed tests")) accent(card, activity, Color.rgb(94, 53, 177));
    }

    private static void polishAccountGroup(Activity activity, LinearLayout group) {
        if (childTextIndex(group, "Account") < 0) return;
        boolean hasSessionAction = false;
        for (int i = 0; i < group.getChildCount(); i++) {
            View v = group.getChildAt(i);
            if (v instanceof Button) {
                String s = String.valueOf(((Button)v).getText()).trim().toLowerCase(Locale.ROOT);
                if (s.contains("sign out") || s.contains("delete account")) hasSessionAction = true;
            }
        }
        if (!hasSessionAction || hasExactText(group, "Session & security")) return;
        TextView section = new TextView(activity);
        section.setText("Session & security");
        section.setTextSize(14);
        section.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        section.setPadding(0, dp(activity, 14), 0, dp(activity, 6));
        group.addView(section, Math.min(2, group.getChildCount()));
    }

    private static void polishText(Activity activity, TextView t) {
        String s = String.valueOf(t.getText()).trim();
        if (s.startsWith("Evidence entries:")) {
            t.setContentDescription("Research evidence count");
        }
    }

    private static void polishButton(Activity activity, Button b) {
        String s = String.valueOf(b.getText()).trim();
        String lower = s.toLowerCase(Locale.ROOT);
        if (lower.equals("sign out all devices") || lower.equals("sign out all")) {
            b.setText("Sign out all devices");
        } else if (lower.equals("sign out")) {
            b.setText("Sign out this device");
        }
    }

    private static int childTextIndex(ViewGroup group, String exact) {
        for (int i = 0; i < group.getChildCount(); i++) {
            View v = group.getChildAt(i);
            if (v instanceof TextView && exact.equals(String.valueOf(((TextView)v).getText()).trim())) return i;
        }
        return -1;
    }

    private static boolean hasExactText(ViewGroup group, String exact) {
        for (int i = 0; i < group.getChildCount(); i++) {
            View v = group.getChildAt(i);
            if (v instanceof TextView && exact.equals(String.valueOf(((TextView)v).getText()).trim())) return true;
        }
        return false;
    }

    private static String collectText(ViewGroup g) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < g.getChildCount(); i++) {
            View v = g.getChildAt(i);
            if (v instanceof TextView) b.append(((TextView)v).getText()).append(' ');
            else if (v instanceof ViewGroup) b.append(collectText((ViewGroup)v)).append(' ');
        }
        return b.toString();
    }

    private static void styleChip(Activity activity, Button chip, boolean selected) {
        int fg = selected ? Color.WHITE : (isDark(activity) ? Color.rgb(225,225,230) : Color.rgb(50,50,55));
        int bg = selected ? Color.rgb(25,118,210) : (isDark(activity) ? Color.rgb(52,52,56) : Color.rgb(238,238,242));
        chip.setTextColor(fg);
        chip.setBackgroundTintList(ColorStateList.valueOf(bg));
    }

    private static void accent(LinearLayout card, Activity activity, int color) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(isDark(activity) ? Color.rgb(39,39,42) : Color.rgb(249,249,251));
        d.setCornerRadius(dp(activity, 16));
        d.setStroke(dp(activity, 1), color);
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
