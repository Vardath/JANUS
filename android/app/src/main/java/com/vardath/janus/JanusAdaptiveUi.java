package com.vardath.janus;

import android.app.Activity;
import android.content.res.Configuration;
import android.graphics.Typeface;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/** Responsive layout and accessibility guardrails for JANUS Android v0.92. */
public final class JanusAdaptiveUi {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusAdaptiveUi() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) walk(activity, root);
        });
    }

    private static void walk(Activity activity, View view) {
        applyAccessibility(activity, view);
        if (view instanceof LinearLayout) adaptRow(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) walk(activity, group.getChildAt(i));
        }
    }

    private static void applyAccessibility(Activity activity, View view) {
        int minTouch = dp(activity, 48);
        if (view instanceof Button || view instanceof EditText) {
            view.setMinimumHeight(Math.max(view.getMinimumHeight(), minTouch));
            view.setFocusable(true);
        }
        if (view instanceof Button) {
            Button b = (Button) view;
            if (b.getContentDescription() == null || b.getContentDescription().length() == 0)
                b.setContentDescription(String.valueOf(b.getText()).replace("\n", ". "));
        }
        if (view instanceof TextView) {
            TextView t = (TextView) view;
            t.setIncludeFontPadding(true);
            if (t.getTextSize() / activity.getResources().getDisplayMetrics().scaledDensity >= 20f)
                t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        }
    }

    private static void adaptRow(Activity activity, LinearLayout row) {
        if (row.getOrientation() != LinearLayout.HORIZONTAL || row.getChildCount() < 2) return;
        int widthDp = activity.getResources().getConfiguration().screenWidthDp;
        if (widthDp <= 0) widthDp = Math.round(activity.getResources().getDisplayMetrics().widthPixels / activity.getResources().getDisplayMetrics().density);

        // Preserve the four-item bottom navigation and horizontal attachment scrollers.
        if (isPrimaryNavigation(row) || row.getParent() instanceof HorizontalScrollView) return;

        // Narrow phones: action rows with 3+ verbose controls stack so labels never collide.
        if (widthDp < 380 && row.getChildCount() >= 3 && hasVerboseButtons(row)) {
            row.setOrientation(LinearLayout.VERTICAL);
            for (int i = 0; i < row.getChildCount(); i++) {
                View child = row.getChildAt(i);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
                lp.setMargins(0, dp(activity, 3), 0, dp(activity, 3));
                child.setLayoutParams(lp);
            }
        }

        // Tablet/foldable layouts get more breathing room without changing navigation semantics.
        if (widthDp >= 600) {
            row.setPadding(Math.max(row.getPaddingLeft(), dp(activity, 8)), row.getPaddingTop(),
                    Math.max(row.getPaddingRight(), dp(activity, 8)), row.getPaddingBottom());
        }
    }

    private static boolean isPrimaryNavigation(LinearLayout row) {
        if (row.getChildCount() != 4) return false;
        StringBuilder labels = new StringBuilder();
        for (int i = 0; i < row.getChildCount(); i++) {
            if (!(row.getChildAt(i) instanceof Button)) return false;
            labels.append(((Button) row.getChildAt(i)).getText()).append('|');
        }
        String s = labels.toString();
        return s.contains("Chat|") && s.contains("Messages|") && s.contains("Observe|") && s.contains("Options|");
    }

    private static boolean hasVerboseButtons(LinearLayout row) {
        int buttons = 0;
        int chars = 0;
        for (int i = 0; i < row.getChildCount(); i++) {
            if (row.getChildAt(i) instanceof Button) {
                buttons++;
                chars += String.valueOf(((Button) row.getChildAt(i)).getText()).length();
            }
        }
        return buttons >= 3 && chars >= 24;
    }

    private static int dp(Activity activity, int value) {
        return Math.round(value * activity.getResources().getDisplayMetrics().density);
    }
}
