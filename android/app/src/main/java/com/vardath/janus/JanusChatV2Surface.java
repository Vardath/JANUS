package com.vardath.janus;

import android.app.Activity;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.WeakHashMap;

/**
 * v1.00 structured Chat surface authority.
 *
 * MainActivity still contains legacy private history helpers during the compatibility window,
 * but this layer makes chat_history_native_v2 the state that is projected into every newly
 * created Chat surface and captures subsequent visible additions back into v2. The legacy
 * preference is therefore a transient adapter for the old private renderer, not the durable
 * source of truth.
 */
public final class JanusChatV2Surface {
    private static final WeakHashMap<Activity, State> STATES = new WeakHashMap<>();
    private JanusChatV2Surface() {}

    public static synchronized void install(Activity activity) {
        if (!(activity instanceof MainActivity) || STATES.containsKey(activity)) return;
        State state = new State(activity);
        STATES.put(activity, state);
        View root = activity.getWindow().getDecorView();
        root.getViewTreeObserver().addOnGlobalLayoutListener(state);
    }

    private static final class State implements ViewTreeObserver.OnGlobalLayoutListener {
        private final Activity activity;
        private ViewGroup currentLog;
        private int childCount = -1;
        private boolean busy;

        State(Activity activity) { this.activity = activity; }

        @Override public void onGlobalLayout() {
            if (busy || activity.isFinishing()) return;
            ViewGroup log = chatLog(activity);
            if (log == null) return;
            try {
                busy = true;
                if (log != currentLog) {
                    // Project authoritative v2 into the legacy private renderer, then redraw once.
                    JanusChatHistoryBridge.prepare(activity);
                    log.removeAllViews();
                    invokeRenderSavedChat(activity);
                    currentLog = log;
                    childCount = log.getChildCount();
                    return;
                }
                int now = log.getChildCount();
                if (now != childCount) {
                    // New user/JANUS/system bubbles are appended by MainActivity; capture the delta.
                    JanusChatHistoryBridge.capture(activity);
                    childCount = now;
                }
            } catch (Exception ignored) {
            } finally { busy = false; }
        }
    }

    private static ViewGroup chatLog(Activity activity) {
        try {
            Field field = MainActivity.class.getDeclaredField("chatLog");
            field.setAccessible(true);
            Object value = field.get(activity);
            return value instanceof ViewGroup ? (ViewGroup) value : null;
        } catch (Exception ignored) { return null; }
    }

    private static void invokeRenderSavedChat(Activity activity) {
        try {
            Method method = MainActivity.class.getDeclaredMethod("renderSavedChat");
            method.setAccessible(true);
            method.invoke(activity);
        } catch (Exception ignored) {}
    }
}
