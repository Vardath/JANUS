package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import java.text.Collator;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Device-local language preferences shared by Chat, speech and locale presentation. */
final class JanusLanguageSettings {
    static final String LANGUAGE_KEY = "preferred_language_tag";
    static final String SPEECH_KEY = "preferred_speech_language_tag";
    static final String SYSTEM = "system";

    private JanusLanguageSettings() {}

    static String languageTag(Context context) {
        return prefs(context).getString(LANGUAGE_KEY, SYSTEM);
    }

    static String speechLanguageTag(Context context) {
        String speech = prefs(context).getString(SPEECH_KEY, SYSTEM);
        if (!SYSTEM.equals(speech)) return speech;
        String language = languageTag(context);
        return SYSTEM.equals(language) ? Locale.getDefault().toLanguageTag() : language;
    }

    static Locale responseLocale(Context context) {
        return localeFor(languageTag(context));
    }

    static Locale speechLocale(Context context) {
        return localeFor(speechLanguageTag(context));
    }

    static void setLanguageTag(Context context, String tag) {
        prefs(context).edit().putString(LANGUAGE_KEY, normalize(tag)).apply();
    }

    static void setSpeechLanguageTag(Context context, String tag) {
        prefs(context).edit().putString(SPEECH_KEY, normalize(tag)).apply();
    }

    static String responseLanguageName(Context context) {
        String tag = languageTag(context);
        if (SYSTEM.equals(tag)) return "System language (" + displayName(Locale.getDefault()) + ")";
        return displayName(Locale.forLanguageTag(tag));
    }

    static String speechLanguageName(Context context) {
        String tag = prefs(context).getString(SPEECH_KEY, SYSTEM);
        if (SYSTEM.equals(tag)) return "Match JANUS language (" + displayName(speechLocale(context)) + ")";
        return displayName(Locale.forLanguageTag(tag));
    }

    static String augmentPrompt(Context context, String message) {
        String tag = languageTag(context);
        if (SYSTEM.equals(tag)) tag = Locale.getDefault().toLanguageTag();
        Locale locale = Locale.forLanguageTag(tag);
        String name = displayName(locale);
        if (message == null || message.isBlank()) return message;
        return message + "\n\n[DEVICE JANUS LANGUAGE PREFERENCE]\n"
                + "Preferred response language: " + name + " (" + locale.toLanguageTag() + "). "
                + "Respond primarily in this language unless the user explicitly requests another language. "
                + "Preserve names, code, citations, mathematical notation and quoted source text where appropriate.";
    }

    static List<Choice> availableLanguages() {
        Map<String, Locale> unique = new LinkedHashMap<>();
        for (Locale locale : Locale.getAvailableLocales()) {
            if (locale == null || locale.getLanguage() == null || locale.getLanguage().isBlank()) continue;
            String tag = locale.toLanguageTag();
            if (tag == null || tag.isBlank() || "und".equalsIgnoreCase(tag)) continue;
            unique.putIfAbsent(tag, locale);
        }
        List<Choice> result = new ArrayList<>();
        result.add(new Choice(SYSTEM, "System language"));
        List<Locale> locales = new ArrayList<>(unique.values());
        Collator collator = Collator.getInstance(Locale.getDefault());
        locales.sort(Comparator.comparing(JanusLanguageSettings::displayName, collator));
        for (Locale locale : locales) result.add(new Choice(locale.toLanguageTag(), displayName(locale)));
        return result;
    }

    static String displayName(Locale locale) {
        if (locale == null) return "Unknown";
        String nativeName = locale.getDisplayName(locale);
        String localName = locale.getDisplayName(Locale.getDefault());
        if (nativeName == null || nativeName.isBlank()) nativeName = locale.toLanguageTag();
        if (localName == null || localName.isBlank() || nativeName.equalsIgnoreCase(localName)) return nativeName;
        return nativeName + " · " + localName;
    }

    private static Locale localeFor(String tag) {
        if (tag == null || tag.isBlank() || SYSTEM.equals(tag)) return Locale.getDefault();
        Locale locale = Locale.forLanguageTag(tag);
        return locale.getLanguage().isBlank() ? Locale.getDefault() : locale;
    }

    private static String normalize(String tag) {
        if (tag == null || tag.isBlank() || SYSTEM.equals(tag)) return SYSTEM;
        Locale locale = Locale.forLanguageTag(tag);
        return locale.getLanguage().isBlank() ? SYSTEM : locale.toLanguageTag();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
    }

    static final class Choice {
        final String tag;
        final String label;
        Choice(String tag, String label) { this.tag = tag; this.label = label; }
    }
}
