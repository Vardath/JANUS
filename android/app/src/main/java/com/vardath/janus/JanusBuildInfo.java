package com.vardath.janus;

/** Single source for user-visible Android build identity. */
public final class JanusBuildInfo {
    private JanusBuildInfo() {}

    public static String versionLabel() {
        return "v" + BuildConfig.VERSION_NAME + " (" + BuildConfig.VERSION_CODE + ")";
    }

    public static String pageLabel(String page) {
        String prefix = page == null || page.isBlank() ? "JANUS" : page.trim();
        return prefix + " · " + versionLabel();
    }
}
