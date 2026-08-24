package com.vardath.janus;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.view.Window;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import java.util.Map;
import java.util.WeakHashMap;

/** Applies JANUS theme preferences to the otherwise-unused Android status/navigation bar areas. */
public final class JanusSystemChrome {
    private static final Map<Activity, SharedPreferences.OnSharedPreferenceChangeListener> LISTENERS = new WeakHashMap<>();
    private JanusSystemChrome() {}

    public static synchronized void install(Activity activity) {
        if (activity == null) return;
        apply(activity);
        if (LISTENERS.containsKey(activity)) return;
        SharedPreferences prefs = activity.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        SharedPreferences.OnSharedPreferenceChangeListener listener = (p, key) -> {
            if ("theme_mode".equals(key) || "accent".equals(key)) activity.runOnUiThread(() -> apply(activity));
        };
        prefs.registerOnSharedPreferenceChangeListener(listener);
        LISTENERS.put(activity, listener);
    }

    public static void apply(Activity activity) {
        if (activity == null || activity.isFinishing()) return;
        boolean dark = isDark(activity);
        int chrome = chromeColor(activity, dark);
        Window w = activity.getWindow();
        w.setStatusBarColor(chrome);
        w.setNavigationBarColor(chrome);
        WindowInsetsControllerCompat c = WindowCompat.getInsetsController(w, w.getDecorView());
        if (c != null) {
            c.setAppearanceLightStatusBars(!dark);
            c.setAppearanceLightNavigationBars(!dark);
        }
    }

    private static int chromeColor(Context context, boolean dark) {
        SharedPreferences p = context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        String accent = p.getString("accent", "slate");
        int a;
        switch (accent) {
            case "indigo": a = Color.rgb(63,81,181); break;
            case "teal": a = Color.rgb(0,121,107); break;
            case "amber": a = Color.rgb(180,105,0); break;
            case "violet": a = Color.rgb(105,38,140); break;
            default: a = dark ? Color.rgb(56,60,64) : Color.rgb(112,116,120); break;
        }
        if ("slate".equals(accent)) return dark ? Color.rgb(48,50,52) : Color.rgb(188,190,192);
        int base = dark ? 36 : 214;
        float mix = dark ? 0.48f : 0.28f;
        return Color.rgb(
                Math.round(base * (1f - mix) + Color.red(a) * mix),
                Math.round(base * (1f - mix) + Color.green(a) * mix),
                Math.round(base * (1f - mix) + Color.blue(a) * mix));
    }

    private static boolean isDark(Context context) {
        SharedPreferences p = context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        String mode = p.getString("theme_mode", "system");
        if ("dark".equals(mode)) return true;
        if ("light".equals(mode)) return false;
        return (context.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK)
                == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }
}
