package com.vardath.janus;

import android.app.Activity;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
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
        // Chat bubbles are user/JANUS content, not shell text. Never rewrite the
        // second TextView in a bubble headed by "You" or "JANUS", even when its
        // content happens to equal a translatable navigation label such as "Settings".
        boolean conversationBody = isConversationBody(view);
        CharSequence current = view.getText();
        if (!conversationBody && !TextUtils.isEmpty(current)) {
            String before = current.toString();
            String after = translateVisibleControl(activity, view, before);
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

    private static String translateVisibleControl(Activity activity, TextView view, String before) {
        String direct = JanusUiTranslations.translate(activity, before);
        if (!before.equals(direct)) return direct;
        // Options rows are buttons whose first line is the actionable title and whose
        // second line is explanatory prose. Translate the known title while retaining
        // English fallback for uncurated prose.
        if (view instanceof Button) {
            int newline = before.indexOf('\n');
            if (newline > 0) {
                String title = before.substring(0, newline);
                String translatedTitle = JanusUiTranslations.translate(activity, title);
                if (!title.equals(translatedTitle)) return translatedTitle + before.substring(newline);
            }
        }
        return before;
    }

    private static boolean isConversationBody(TextView view) {
        if (!(view.getParent() instanceof ViewGroup)) return false;
        ViewGroup parent = (ViewGroup) view.getParent();
        if (parent.getChildCount() < 2 || parent.getChildAt(1) != view || !(parent.getChildAt(0) instanceof TextView)) return false;
        String author = String.valueOf(((TextView) parent.getChildAt(0)).getText()).trim();
        return "You".equals(author) || "JANUS".equals(author);
    }
}
