package com.vardath.janus;

import android.app.Activity;
import android.content.res.Configuration;
import android.os.Build;
import android.view.Window;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

/**
 * Keeps Android-owned system chrome independent from JANUS appearance settings.
 *
 * JANUS appearance preferences are intentionally app-view-only. They must never
 * recolour or otherwise track the host Android status/navigation bars. This
 * class only keeps system-bar icon contrast aligned with the device's own
 * current light/dark configuration.
 */
public final class JanusSystemChrome {
    private JanusSystemChrome() {}

    public static void install(Activity activity) {
        apply(activity);
    }

    public static void apply(Activity activity) {
        if (activity == null || activity.isFinishing()) return;
        Window window = activity.getWindow();
        WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, window.getDecorView());
        if (controller == null) return;

        boolean deviceDark = (activity.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK)
                == Configuration.UI_MODE_NIGHT_YES;
        controller.setAppearanceLightStatusBars(!deviceDark);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            controller.setAppearanceLightNavigationBars(!deviceDark);
        }
    }
}
