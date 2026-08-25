package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.Color;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

/** App-local high-contrast JANUS palette. Never changes Android system/theme colours. */
public final class JanusTheme {
    private JanusTheme() {}

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
    }

    public static boolean dark(Context c) {
        String mode = prefs(c).getString("theme_mode", "system");
        if ("dark".equals(mode)) return true;
        if ("light".equals(mode)) return false;
        return (c.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK)
                == Configuration.UI_MODE_NIGHT_YES;
    }

    private static int neutralBackground(Context c) {
        return dark(c) ? Color.rgb(15, 18, 22) : Color.rgb(248, 249, 251);
    }

    private static int neutralSurface(Context c) {
        return dark(c) ? Color.rgb(31, 37, 44) : Color.rgb(236, 239, 243);
    }

    private static int neutralRaised(Context c) {
        return dark(c) ? Color.rgb(40, 48, 57) : Color.WHITE;
    }

    private static int blend(int base, int tint, float amount) {
        float a = Math.max(0f, Math.min(1f, amount));
        int r = Math.round(Color.red(base) * (1f - a) + Color.red(tint) * a);
        int g = Math.round(Color.green(base) * (1f - a) + Color.green(tint) * a);
        int b = Math.round(Color.blue(base) * (1f - a) + Color.blue(tint) * a);
        return Color.rgb(r, g, b);
    }

    /**
     * Accent now tints the whole JANUS-owned interface instead of only selected buttons.
     * The tint remains deliberately restrained so contrast/readability stay stable.
     */
    public static int background(Context c) {
        return blend(neutralBackground(c), accent(c), dark(c) ? 0.07f : 0.035f);
    }

    public static int surface(Context c) {
        return blend(neutralSurface(c), accent(c), dark(c) ? 0.13f : 0.07f);
    }

    public static int surfaceRaised(Context c) {
        return blend(neutralRaised(c), accent(c), dark(c) ? 0.20f : 0.11f);
    }

    public static int text(Context c) { return dark(c) ? Color.rgb(248, 250, 252) : Color.rgb(24, 29, 35); }
    public static int muted(Context c) { return dark(c) ? Color.rgb(194, 202, 211) : Color.rgb(82, 91, 101); }
    public static int userBubble(Context c) {
        int base = dark(c) ? Color.rgb(38, 61, 84) : Color.rgb(219, 235, 252);
        return blend(base, accent(c), dark(c) ? 0.22f : 0.13f);
    }

    public static int accent(Context c) {
        String a = prefs(c).getString("accent", "slate");
        boolean d = dark(c);
        switch (a) {
            case "indigo": return d ? Color.rgb(116, 137, 255) : Color.rgb(67, 83, 190);
            case "teal": return d ? Color.rgb(73, 191, 174) : Color.rgb(0, 120, 105);
            case "amber": return d ? Color.rgb(245, 184, 74) : Color.rgb(188, 118, 0);
            case "violet": return d ? Color.rgb(190, 132, 255) : Color.rgb(124, 61, 174);
            default: return d ? Color.rgb(139, 158, 176) : Color.rgb(75, 91, 107);
        }
    }

    public static int onAccent(Context c) {
        int x = accent(c);
        double lum = (0.299 * Color.red(x) + 0.587 * Color.green(x) + 0.114 * Color.blue(x)) / 255.0;
        return lum > 0.62 ? Color.rgb(18, 22, 27) : Color.WHITE;
    }

    public static void applyRoot(Context c, View v) { if (v != null) v.setBackgroundColor(background(c)); }
    public static void applyCard(Context c, View v) { if (v != null) v.setBackgroundColor(surface(c)); }
    public static void applyRaised(Context c, View v) { if (v != null) v.setBackgroundColor(surfaceRaised(c)); }

    public static void applyText(Context c, TextView v, boolean mutedText) {
        if (v != null) v.setTextColor(mutedText ? muted(c) : text(c));
    }

    public static void applyInput(Context c, EditText v) {
        if (v == null) return;
        v.setTextColor(text(c));
        v.setHintTextColor(muted(c));
    }

    public static void applyButton(Context c, Button b) {
        if (b == null) return;
        b.setBackgroundTintList(ColorStateList.valueOf(surfaceRaised(c)));
        b.setTextColor(text(c));
    }

    public static void applyAccentButton(Context c, Button b) {
        if (b == null) return;
        b.setBackgroundTintList(ColorStateList.valueOf(accent(c)));
        b.setTextColor(onAccent(c));
    }
}
