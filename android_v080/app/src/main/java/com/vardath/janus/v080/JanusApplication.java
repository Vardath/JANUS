package com.vardath.janus.v080;

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;

public final class JanusApplication extends Application {
    @Override public void onCreate(){
        super.onCreate();
        ThemePrefs.applyGlobal(this);
        registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks(){
            @Override public void onActivityResumed(Activity activity){ThemePrefs.applyAccent(activity.getWindow().getDecorView(),activity);}
            @Override public void onActivityCreated(Activity a, Bundle b){}
            @Override public void onActivityStarted(Activity a){}
            @Override public void onActivityPaused(Activity a){}
            @Override public void onActivityStopped(Activity a){}
            @Override public void onActivitySaveInstanceState(Activity a, Bundle b){}
            @Override public void onActivityDestroyed(Activity a){}
        });
    }
}
