package com.vardath.janus;

import android.app.Activity;
import android.widget.LinearLayout;

/**
 * Native Observe surface boundary.
 *
 * Observe is intentionally read-only presentation of JANUS/local-core state.
 * It must not become a second control plane for the 11-core runtime.
 */
public final class JanusObserveScreen {
    private JanusObserveScreen() {}

    public interface Host {
        Activity activity();
        JanusApiClient api();
        JanusLocalCoreRuntime localRuntime();
        String observeMode();
        void setObserveMode(String mode);
        void runIo(Runnable work);
        void runUi(Runnable work);
        void toast(String message);
    }

    public static void render(Host host, LinearLayout content) {
        if (host == null || content == null) return;
        // Behaviour is migrated from MainActivity incrementally. This class is
        // the stable ownership boundary for core map, filters and telemetry.
    }
}
