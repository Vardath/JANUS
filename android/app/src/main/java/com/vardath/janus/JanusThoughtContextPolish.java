package com.vardath.janus;

import android.app.Activity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/** Adds local-runtime context only when the user explicitly asks about away/background processing. */
public final class JanusThoughtContextPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<EditText> ATTACHED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final String MARKER = "[DEVICE JANUS BACKGROUND-ACTIVITY CONTEXT]";
    private JanusThoughtContextPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        View decor = activity.getWindow().getDecorView();
        decor.post(() -> scan(activity, decor));
        decor.getViewTreeObserver().addOnGlobalLayoutListener(() -> decor.post(() -> scan(activity, decor)));
    }

    private static void scan(Activity activity, View view) {
        if (view instanceof EditText) {
            EditText edit = (EditText) view;
            if ("Message JANUS".contentEquals(edit.getHint())) attach(activity, edit);
        }
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) scan(activity, g.getChildAt(i));
        }
    }

    private static void attach(Activity activity, EditText composer) {
        if (!ATTACHED.add(composer)) return;
        View parent = (View) composer.getParent();
        if (!(parent instanceof ViewGroup)) return;
        ViewGroup row = (ViewGroup) parent;
        for (int i = 0; i < row.getChildCount(); i++) {
            View v = row.getChildAt(i);
            if (!(v instanceof Button) || !"Send".contentEquals(((Button) v).getText())) continue;
            v.setOnTouchListener((button, event) -> {
                if (event.getAction() != MotionEvent.ACTION_DOWN) return false;
                String visible = composer.getText().toString();
                if (visible.contains(MARKER) || !JanusThoughtBridge.asksAboutBackgroundActivity(visible)) return false;
                String augmented = JanusThoughtBridge.augment(JanusLocalCoreRuntime.get(activity), visible);
                if (!augmented.equals(visible)) {
                    composer.setText(augmented);
                    composer.setSelection(composer.length());
                }
                return false;
            });
        }
    }
}
