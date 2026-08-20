package com.vardath.janus;

import android.app.Application;

public class JanusApplication extends Application {
    @Override public void onCreate() {
        super.onCreate();
        JanusLocalCoreRuntime.get(this).start();
    }
}
