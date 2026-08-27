package com.vardath.janus;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.view.View;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

/**
 * Explicit safe-area handling for JANUS-owned root surfaces plus the global
 * first-interaction AI transparency notice.
 *
 * No view-tree walking or global-layout listeners are used. Each root opts in once
 * when it is created. System bars/cutouts are added to its authored padding and
 * the IME raises the bottom edge when the keyboard is visible.
 */
public final class JanusSafeArea {
    private static final String PREFS = "janus_compliance";
    private static final String AI_NOTICE_ACK = "ai_notice_ack_v1";
    private JanusSafeArea() {}

    public static void install(View root) {
        if (root == null) return;
        final int left = root.getPaddingLeft();
        final int top = root.getPaddingTop();
        final int right = root.getPaddingRight();
        final int bottom = root.getPaddingBottom();

        ViewCompat.setOnApplyWindowInsetsListener(root, (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout());
            Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
            int safeBottom = Math.max(bars.bottom, ime.bottom);
            view.setPadding(left + bars.left, top + bars.top, right + bars.right, bottom + safeBottom);
            return insets;
        });
        ViewCompat.requestApplyInsets(root);
        installAiTransparencyNotice(root);
    }

    private static void installAiTransparencyNotice(View root) {
        Context context = root.getContext();
        if (!(context instanceof Activity)) return;
        Activity activity = (Activity) context;
        if (activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(AI_NOTICE_ACK, false)) return;

        root.post(() -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            if (activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(AI_NOTICE_ACK, false)) return;
            new AlertDialog.Builder(activity)
                    .setTitle("JANUS is an AI assistant")
                    .setMessage("JANUS uses artificial intelligence to generate responses, research summaries and some images. AI output can be incomplete or wrong. JANUS may send the message you submit and relevant account-private context to configured AI/search service providers when needed to answer or research. JANUS is not a human and should not be the sole decision-maker for medical care, legal rights, finance, employment, housing, education, insurance, credit, safety-critical actions or other decisions that can significantly affect a person. You can report a JANUS response from Chat, review the Privacy Policy in the app, and delete your account and associated JANUS data from Account settings.")
                    .setCancelable(false)
                    .setNeutralButton("Privacy", (dialog, which) -> {
                        try {
                            activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://janus-global-core.onrender.com/privacy")));
                        } catch (Exception ignored) {}
                    })
                    .setPositiveButton("Continue", (dialog, which) ->
                            activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                                    .edit().putBoolean(AI_NOTICE_ACK, true).apply())
                    .show();
        });
    }
}
