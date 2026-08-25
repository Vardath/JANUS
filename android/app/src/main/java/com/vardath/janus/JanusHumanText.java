package com.vardath.janus;

import java.util.ArrayList;
import java.util.List;

/** Converts bounded externalizable runtime strings into compact human-facing text. */
public final class JanusHumanText {
    private JanusHumanText() {}

    public static String summarize(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        if (s.isEmpty()) return s;

        // Hide dense machine appraisal blobs from the normal reading path. They remain available in technical details.
        s = s.replaceAll(";?\\s*appraisal=\\{.*?\\}(?=;|$)", "");
        s = s.replaceAll(";?\\s*(origin|line|file|hash|signature)=[^;]*", "");
        s = s.replace('_', ' ');

        String[] parts = s.split(";\\s*");
        List<String> useful = new ArrayList<>();
        for (String part : parts) {
            String p = part == null ? "" : part.trim();
            if (p.isEmpty()) continue;
            if (p.startsWith("attention directive=")) p = "Focus: " + p.substring("attention directive=".length());
            else if (p.startsWith("directional salience=")) p = "Salience: " + p.substring("directional salience=".length());
            else if (p.startsWith("Fano d")) p = "Fano focus: " + p.substring(5);
            else if (p.startsWith("focus=")) p = "Focus: " + p.substring(6);
            useful.add(sentence(p));
            if (useful.size() >= 5) break;
        }
        if (useful.isEmpty()) return sentence(s);
        return String.join("\n", useful);
    }

    public static String memoryTitle(String raw) {
        if (raw == null || raw.isBlank()) return "Continuity memory";
        String s = raw.trim();
        if (s.startsWith("core:")) {
            int second = s.indexOf(':', 5);
            if (second > 5) return pretty(s.substring(5, second)) + " memory";
        }
        return "Continuity memory";
    }

    public static String pretty(String s) {
        if (s == null || s.isBlank()) return "";
        String x = s.replace('_', ' ').trim();
        return Character.toUpperCase(x.charAt(0)) + x.substring(1);
    }

    private static String sentence(String s) {
        if (s == null) return "";
        String x = s.trim();
        if (x.isEmpty()) return x;
        x = Character.toUpperCase(x.charAt(0)) + x.substring(1);
        return x;
    }
}
