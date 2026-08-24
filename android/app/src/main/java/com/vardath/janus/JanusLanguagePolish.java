package com.vardath.janus;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Typeface;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.WeakHashMap;

/** Injects broad device-local language controls into the existing Settings screen. */
public final class JanusLanguagePolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final int TAG_LANGUAGE_CARD = 0x4A7310;

    private JanusLanguagePolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        activity.getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            View root = activity.findViewById(android.R.id.content);
            if (root != null) walk(activity, root);
        });
    }

    private static void walk(Activity activity, View view) {
        if (view instanceof LinearLayout) maybeInject(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) walk(activity, group.getChildAt(i));
        }
    }

    private static void maybeInject(Activity activity, LinearLayout group) {
        if (group.getTag(TAG_LANGUAGE_CARD) != null) return;
        if (!containsExact(group, "Settings")) return;
        if (!containsText(group, "Appearance") && !containsText(group, "Local JANUS background operation")) return;

        LinearLayout card = new LinearLayout(activity);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(activity, 14), dp(activity, 12), dp(activity, 14), dp(activity, 12));

        TextView title = new TextView(activity);
        title.setText(JanusUiTranslations.translate(activity, "Language"));
        title.setTextSize(16);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        card.addView(title, full());

        TextView info = new TextView(activity);
        info.setText("Choose JANUS's conversation/research language and, separately, the language used for speech recognition and text-to-speech. Untranslated interface text falls back to English.");
        info.setTextSize(12);
        info.setPadding(0, dp(activity, 4), 0, dp(activity, 8));
        card.addView(info, full());

        Button response = new Button(activity);
        response.setAllCaps(false);
        response.setGravity(android.view.Gravity.START | android.view.Gravity.CENTER_VERTICAL);
        updateResponseLabel(activity, response);
        response.setOnClickListener(v -> showPicker(activity, false, response, null));
        card.addView(response, full());

        Button speech = new Button(activity);
        speech.setAllCaps(false);
        speech.setGravity(android.view.Gravity.START | android.view.Gravity.CENTER_VERTICAL);
        updateSpeechLabel(activity, speech);
        speech.setOnClickListener(v -> showPicker(activity, true, speech, null));
        card.addView(speech, full());

        TextView coverage = new TextView(activity);
        coverage.setText("Conversation and speech languages come from Android's locale catalogue. Static JANUS interface translations cover major languages and safely fall back to English elsewhere. Speech support depends on the installed recognizer/TTS engine.");
        coverage.setTextSize(11);
        coverage.setPadding(0, dp(activity, 6), 0, 0);
        card.addView(coverage, full());

        int insertAt = Math.min(3, group.getChildCount());
        group.addView(card, insertAt, full());
        group.setTag(TAG_LANGUAGE_CARD, Boolean.TRUE);
    }

    private static void showPicker(Activity activity, boolean speech, Button target, String filter) {
        List<JanusLanguageSettings.Choice> all = JanusLanguageSettings.availableLanguages();
        String needle = filter == null ? "" : filter.trim().toLowerCase(Locale.ROOT);
        java.util.ArrayList<JanusLanguageSettings.Choice> choices = new java.util.ArrayList<>();
        for (JanusLanguageSettings.Choice c : all) {
            if (needle.isEmpty() || c.label.toLowerCase(Locale.ROOT).contains(needle) || c.tag.toLowerCase(Locale.ROOT).contains(needle)) choices.add(c);
        }
        CharSequence[] labels = new CharSequence[choices.size()];
        for (int i = 0; i < choices.size(); i++) labels[i] = choices.get(i).label + (JanusLanguageSettings.SYSTEM.equals(choices.get(i).tag) ? "" : "  [" + choices.get(i).tag + "]");

        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle(speech ? "Speech language" : "JANUS language")
                .setItems(labels, (d, which) -> {
                    JanusLanguageSettings.Choice choice = choices.get(which);
                    if (speech) {
                        JanusLanguageSettings.setSpeechLanguageTag(activity, choice.tag);
                        updateSpeechLabel(activity, target);
                    } else {
                        JanusLanguageSettings.setLanguageTag(activity, choice.tag);
                        // Rebuild from canonical English source text before applying the new
                        // locale. This prevents mixed-language screens after switching twice.
                        activity.recreate();
                    }
                })
                .setNegativeButton(JanusUiTranslations.translate(activity, "Cancel"), null)
                .create();
        dialog.setOnShowListener(x -> dialog.getListView().setFastScrollEnabled(true));
        dialog.show();
    }

    private static void updateResponseLabel(Activity activity, Button button) {
        button.setText("JANUS conversation & research\n" + JanusLanguageSettings.responseLanguageName(activity));
    }

    private static void updateSpeechLabel(Activity activity, Button button) {
        button.setText("Speech recognition & voice\n" + JanusLanguageSettings.speechLanguageName(activity));
    }

    private static boolean containsExact(ViewGroup group, String exact) {
        for (int i = 0; i < group.getChildCount(); i++) {
            View v = group.getChildAt(i);
            if (v instanceof TextView && exact.equals(String.valueOf(((TextView) v).getText()).trim())) return true;
        }
        return false;
    }

    private static boolean containsText(ViewGroup group, String fragment) {
        for (int i = 0; i < group.getChildCount(); i++) {
            View v = group.getChildAt(i);
            if (v instanceof TextView && String.valueOf(((TextView) v).getText()).contains(fragment)) return true;
            if (v instanceof ViewGroup && containsText((ViewGroup) v, fragment)) return true;
        }
        return false;
    }

    private static LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private static int dp(Activity activity, int value) { return Math.round(value * activity.getResources().getDisplayMetrics().density); }
}
