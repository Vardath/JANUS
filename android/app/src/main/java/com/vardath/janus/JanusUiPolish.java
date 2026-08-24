package com.vardath.janus;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.text.util.Linkify;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * App-wide native chrome and readability layer for the v0.83 UI pass.
 *
 * MainActivity intentionally remains behaviourally stable while this class
 * supplies edge-to-edge safe areas, IME clearance and consistent visual polish
 * to the programmatic native UI. New views are picked up automatically.
 */
public final class JanusUiPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());

    private JanusUiPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);

        Window window = activity.getWindow();
        WindowCompat.setDecorFitsSystemWindows(window, false);
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);

        View content = activity.findViewById(android.R.id.content);
        if (content != null) {
            ViewCompat.setOnApplyWindowInsetsListener(content, (view, insets) -> {
                Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
                Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
                int bottom = Math.max(bars.bottom, ime.bottom);
                // The application content itself receives only system/IME safe area.
                // Screen-specific padding inside MainActivity remains intact.
                view.setPadding(bars.left, bars.top, bars.right, bottom);
                return insets;
            });
            ViewCompat.requestApplyInsets(content);
        }

        applySystemBarContrast(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) polishTree(activity, root);
        });
    }

    private static void applySystemBarContrast(Activity activity) {
        boolean dark = isDark(activity);
        WindowInsetsControllerCompat c = WindowCompat.getInsetsController(activity.getWindow(), activity.getWindow().getDecorView());
        if (c != null) {
            c.setAppearanceLightStatusBars(!dark);
            c.setAppearanceLightNavigationBars(!dark);
        }
    }

    private static void polishTree(Activity activity, View view) {
        if (view instanceof Button) styleButton(activity, (Button) view);
        else if (view instanceof EditText) styleInput(activity, (EditText) view);
        else if (view instanceof TextView) styleText((TextView) view);

        if (view instanceof LinearLayout) styleSurface(activity, (LinearLayout) view);

        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) polishTree(activity, group.getChildAt(i));
        }
    }

    private static void styleButton(Activity activity, Button button) {
        button.setAllCaps(false);
        button.setMinHeight(dp(activity, 48));
        button.setTextSize(14);
        button.setPadding(dp(activity, 12), dp(activity, 8), dp(activity, 12), dp(activity, 8));

        Object tag = button.getTag();
        boolean nav = tag instanceof String && ("Chat".equals(tag) || "Messages".equals(tag) || "Observe".equals(tag) || "Options".equals(tag));
        int accent = accent(activity);
        int surface = elevatedSurface(activity);
        int text = textColor(activity);

        if (nav) {
            boolean selected = button.getAlpha() > 0.9f;
            button.setBackgroundTintList(ColorStateList.valueOf(selected ? withAlpha(accent, isDark(activity) ? 210 : 235) : surface));
            button.setTextColor(selected ? Color.WHITE : text);
            button.setMinHeight(dp(activity, 52));
        } else {
            button.setBackgroundTintList(ColorStateList.valueOf(surface));
            button.setTextColor(text);
        }
    }

    private static void styleInput(Activity activity, EditText input) {
        if (input.getTag() != null && "janus-polished-input".equals(input.getTag())) return;
        input.setTag("janus-polished-input");
        input.setMinHeight(dp(activity, 52));
        input.setTextColor(textColor(activity));
        input.setHintTextColor(mutedColor(activity));
        input.setPadding(dp(activity, 14), dp(activity, 10), dp(activity, 14), dp(activity, 10));
        GradientDrawable bg = rounded(activity, elevatedSurface(activity), 16);
        bg.setStroke(dp(activity, 1), withAlpha(mutedColor(activity), 90));
        input.setBackground(bg);
    }

    private static void styleText(TextView text) {
        CharSequence value = text.getText();
        if (value != null && value.toString().contains("http")) {
            text.setAutoLinkMask(Linkify.WEB_URLS);
            text.setLinksClickable(true);
        }
        text.setLineSpacing(0f, 1.08f);
    }

    private static void styleSurface(Activity activity, LinearLayout layout) {
        if (!(layout.getBackground() instanceof ColorDrawable)) return;
        int existing = ((ColorDrawable) layout.getBackground()).getColor();
        int surface = isDark(activity) ? Color.rgb(37, 37, 37) : Color.rgb(243, 243, 243);
        int user = isDark(activity) ? Color.rgb(37, 55, 76) : Color.rgb(222, 237, 255);
        if (existing != surface && existing != user) return;

        GradientDrawable rounded = rounded(activity, existing, 18);
        if (existing == surface) rounded.setStroke(dp(activity, 1), withAlpha(mutedColor(activity), 45));
        layout.setBackground(rounded);
        layout.setElevation(dp(activity, 1));
    }

    private static GradientDrawable rounded(Context context, int color, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setShape(GradientDrawable.RECTANGLE);
        d.setColor(color);
        d.setCornerRadius(dp(context, radiusDp));
        return d;
    }

    private static boolean isDark(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        String mode = prefs.getString("theme_mode", "system");
        if ("dark".equals(mode)) return true;
        if ("light".equals(mode)) return false;
        return (context.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK)
                == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }

    private static int accent(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        switch (prefs.getString("accent", "slate")) {
            case "indigo": return Color.rgb(63, 81, 181);
            case "teal": return Color.rgb(0, 121, 107);
            case "amber": return Color.rgb(230, 135, 0);
            case "violet": return Color.rgb(123, 31, 162);
            default: return isDark(context) ? Color.rgb(105, 115, 125) : Color.rgb(58, 68, 78);
        }
    }

    private static int elevatedSurface(Context context) {
        return isDark(context) ? Color.rgb(46, 46, 48) : Color.rgb(247, 247, 249);
    }

    private static int textColor(Context context) {
        return isDark(context) ? Color.rgb(244, 244, 244) : Color.rgb(24, 24, 24);
    }

    private static int mutedColor(Context context) {
        return isDark(context) ? Color.rgb(180, 180, 184) : Color.rgb(102, 102, 108);
    }

    private static int withAlpha(int color, int alpha) {
        return Color.argb(Math.max(0, Math.min(255, alpha)), Color.red(color), Color.green(color), Color.blue(color));
    }

    private static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }
}
