package com.vardath.janus;

import android.app.Activity;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/** Applies curated shell translations after each dynamically rendered native screen. */
public final class JanusUiLocalizationPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusUiLocalizationPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) walk(activity, root);
        });
    }

    private static void walk(Activity activity, View view) {
        if (view instanceof TextView) translate(activity, (TextView) view);
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) walk(activity, group.getChildAt(i));
        }
    }

    private static void translate(Activity activity, TextView view) {
        CharSequence current = view.getText();
        if (!TextUtils.isEmpty(current)) {
            String before = current.toString();
            String after = JanusUiTranslations.translate(activity, before);
            if (!before.equals(after)) view.setText(after);
        }
        CharSequence hint = view.getHint();
        if (!TextUtils.isEmpty(hint)) {
            String before = hint.toString();
            String after = JanusUiTranslations.translate(activity, before);
            if (!before.equals(after)) view.setHint(after);
        }
        view.setTextDirection(View.TEXT_DIRECTION_LOCALE);
        view.setTextAlignment(JanusUiTranslations.isRightToLeft(activity) ? View.TEXT_ALIGNMENT_VIEW_END : View.TEXT_ALIGNMENT_INHERIT);
    }
}
