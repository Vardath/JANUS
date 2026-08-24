package com.vardath.janus;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;

import java.util.WeakHashMap;

/**
 * Installs an explicit push-to-talk control on the native Chat composer.
 *
 * Recognized speech is written into the existing composer and the existing Send
 * button is clicked, so voice input follows exactly the same JANUS chat/sensory
 * path as typed input. No ambient listening and no second response pipeline.
 */
final class JanusVoiceUiPolish {
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final WeakHashMap<Activity, JanusDeviceVoice> VOICE = new WeakHashMap<>();
    private static final int TAG_KEY = 0x4a137731;

    private JanusVoiceUiPolish() {}

    static void install(Activity activity) {
        if (activity == null) return;
        attach(activity, 0);
    }

    private static void attach(Activity activity, int attempt) {
        View root = activity.findViewById(android.R.id.content);
        EditText composer = findComposer(root);
        if (composer == null || !(composer.getParent() instanceof LinearLayout)) {
            if (attempt < 8) MAIN.postDelayed(() -> attach(activity, attempt + 1), 180L);
            return;
        }
        LinearLayout row = (LinearLayout) composer.getParent();
        Object tag = row.getTag(TAG_KEY);
        if (Boolean.TRUE.equals(tag)) return;
        Button send = findSend(row);
        if (send == null) return;

        Button mic = new Button(activity);
        mic.setText("Mic");
        mic.setAllCaps(false);
        mic.setContentDescription("Push to talk to JANUS");
        int sendIndex = row.indexOfChild(send);
        row.addView(mic, Math.max(0, sendIndex), new LinearLayout.LayoutParams(dp(activity, 62), dp(activity, 58)));
        row.setTag(TAG_KEY, Boolean.TRUE);

        mic.setOnClickListener(v -> {
            JanusDeviceVoice voice = VOICE.get(activity);
            if (voice == null) {
                voice = new JanusDeviceVoice(activity);
                VOICE.put(activity, voice);
            }
            mic.setEnabled(false);
            mic.setText("…");
            JanusDeviceVoice active = voice;
            active.startPushToTalk(new JanusDeviceVoice.Listener() {
                @Override public void onReady(boolean onDevice) {
                    MAIN.post(() -> mic.setText(onDevice ? "Listen" : "Listen*"));
                }
                @Override public void onPartial(String text) {
                    MAIN.post(() -> composer.setText(text));
                }
                @Override public void onRecognized(String text, boolean onDevice) {
                    MAIN.post(() -> {
                        composer.setText(text);
                        composer.setSelection(composer.length());
                        mic.setEnabled(true);
                        mic.setText("Mic");
                        send.performClick();
                    });
                }
                @Override public void onError(String message) {
                    MAIN.post(() -> {
                        mic.setEnabled(true);
                        mic.setText("Mic");
                        if (message != null && !message.isBlank()) Toast.makeText(activity, message, Toast.LENGTH_SHORT).show();
                    });
                }
            });
        });
    }

    static void destroy(Activity activity) {
        JanusDeviceVoice voice = VOICE.remove(activity);
        if (voice != null) voice.destroy();
    }

    private static EditText findComposer(View view) {
        if (view instanceof EditText) {
            EditText e = (EditText) view;
            CharSequence hint = e.getHint();
            if (hint != null && "Message JANUS".contentEquals(hint)) return e;
        }
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i = 0; i < g.getChildCount(); i++) {
                EditText found = findComposer(g.getChildAt(i));
                if (found != null) return found;
            }
        }
        return null;
    }

    private static Button findSend(ViewGroup row) {
        for (int i = 0; i < row.getChildCount(); i++) {
            View v = row.getChildAt(i);
            if (v instanceof Button && "Send".contentEquals(((Button) v).getText())) return (Button) v;
        }
        return null;
    }

    private static int dp(Activity a, int n) {
        return Math.round(n * a.getResources().getDisplayMetrics().density);
    }
}
