package com.vardath.janus;

import android.app.Activity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Native Android Back semantics for JANUS' single-Activity page/subpage UI.
 *
 * MainActivity renders pages by replacing one content container, so Android has no
 * Fragment/Activity back stack to pop. This adapter treats explicit "← Parent"
 * buttons as the subpage stack and the four bottom tabs as top-level pages.
 */
public final class JanusNavigationPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusNavigationPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                () -> handleBack(activity));
    }

    private static void handleBack(Activity activity) {
        View root = activity.findViewById(android.R.id.content);
        Button parent = findParentButton(root);
        if (parent != null) {
            parent.performClick();
            return;
        }
        String selected = selectedTopPage(root);
        if (selected != null && !"Chat".equals(selected)) {
            Button chat = findButton(root, "Chat");
            if (chat != null) { chat.performClick(); return; }
        }
        activity.finish();
    }

    private static Button findParentButton(View view) {
        if (view instanceof Button) {
            Button b = (Button) view;
            String s = String.valueOf(b.getText()).trim();
            if (s.startsWith("← ") || s.startsWith("‹ ")) return b;
        }
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) {
                Button found = findParentButton(g.getChildAt(i));
                if (found != null) return found;
            }
        }
        return null;
    }

    private static String selectedTopPage(View root) {
        for (String page : new String[]{"Chat", "Messages", "Observe", "Stream", "Options"}) {
            Button b = findButton(root, page);
            if (b != null && b.getAlpha() > .9f) return page;
        }
        return null;
    }

    private static Button findButton(View view, String exact) {
        if (view instanceof Button && exact.equals(String.valueOf(((TextView) view).getText()).trim())) return (Button) view;
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) {
                Button found = findButton(g.getChildAt(i), exact);
                if (found != null) return found;
            }
        }
        return null;
    }
}
