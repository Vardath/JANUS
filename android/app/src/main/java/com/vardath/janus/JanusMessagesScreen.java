package com.vardath.janus;

import android.app.Activity;
import android.widget.LinearLayout;

/**
 * Native Messages surface boundary.
 *
 * v1.03 extraction point: message rendering and actions belong here rather than
 * accumulating further responsibilities in MainActivity. The Activity remains
 * the lifecycle/navigation shell while this screen owns Messages presentation.
 */
public final class JanusMessagesScreen {
    private JanusMessagesScreen() {}

    public interface Host {
        Activity activity();
        JanusApiClient api();
        void runIo(Runnable work);
        void runUi(Runnable work);
        void toast(String message);
        void replyInChat(String message);
    }

    public static void render(Host host, LinearLayout content) {
        if (host == null || content == null) return;
        // Behaviour is migrated from MainActivity incrementally. Keeping the
        // public screen boundary in a standalone class lets subsequent commits
        // move message fetch/render/action code without changing navigation.
    }
}
