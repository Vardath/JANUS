package com.vardath.janus;

import android.app.Activity;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

/**
 * Explicit localization helpers for JANUS-owned controls.
 *
 * This class deliberately does not install layout listeners or walk the live view
 * hierarchy. Screen owners localize controls when they create them, which keeps
 * localization deterministic and prevents user/JANUS conversation bodies from
 * being rewritten after layout.
 */
public final class JanusUiLocalizationPolish {
    private JanusUiLocalizationPolish() {}

    public static String controlText(Activity activity, String canonical) {
        if (canonical == null) return "";
        String direct = JanusUiTranslations.translate(activity, canonical);
        if (!canonical.equals(direct)) return direct;
        int newline = canonical.indexOf('\n');
        if (newline > 0) {
            String title = canonical.substring(0, newline);
            String translatedTitle = JanusUiTranslations.translate(activity, title);
            if (!title.equals(translatedTitle)) return translatedTitle + canonical.substring(newline);
        }
        return canonical;
    }

    public static void applyButton(Activity activity, Button button, String canonical) {
        if (button == null) return;
        button.setText(controlText(activity, canonical));
        applyDirection(activity, button);
    }

    public static void applyHint(Activity activity, TextView view, String canonicalHint) {
        if (view == null) return;
        view.setHint(JanusUiTranslations.translate(activity, canonicalHint == null ? "" : canonicalHint));
        applyDirection(activity, view);
    }

    public static String shellText(Activity activity, String canonical) {
        return JanusUiTranslations.translate(activity, canonical == null ? "" : canonical);
    }

    private static void applyDirection(Activity activity, TextView view) {
        view.setTextDirection(View.TEXT_DIRECTION_LOCALE);
        view.setTextAlignment(JanusUiTranslations.isRightToLeft(activity)
                ? View.TEXT_ALIGNMENT_VIEW_END
                : View.TEXT_ALIGNMENT_INHERIT);
    }
}
