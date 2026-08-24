package com.vardath.janus;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/** Adds an owner-controlled bridge from JANUS maintenance requests to ChatGPT Supervisor. */
public final class JanusMaintenanceSupervisorPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<LinearLayout> HOSTS = Collections.newSetFromMap(new WeakHashMap<>());
    private JanusMaintenanceSupervisorPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        View decor = activity.getWindow().getDecorView();
        decor.post(() -> scan(activity, decor));
        decor.getViewTreeObserver().addOnGlobalLayoutListener(() -> decor.post(() -> scan(activity, decor)));
    }

    private static void scan(Activity activity, View view) {
        if (view instanceof LinearLayout) maybeInject(activity, (LinearLayout)view);
        if (view instanceof ViewGroup) {
            ViewGroup g=(ViewGroup)view;
            for(int i=0;i<g.getChildCount();i++) scan(activity,g.getChildAt(i));
        }
    }

    private static void maybeInject(Activity activity, LinearLayout layout) {
        if (HOSTS.contains(layout)) return;
        int title=-1;
        for(int i=0;i<layout.getChildCount();i++) {
            View v=layout.getChildAt(i);
            if(v instanceof TextView && !(v instanceof Button) && "Maintenance Review".equals(String.valueOf(((TextView)v).getText()).trim())) { title=i; break; }
        }
        if(title<0) return;
        HOSTS.add(layout);

        LinearLayout panel=new LinearLayout(activity);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(activity,10),dp(activity,8),dp(activity,10),dp(activity,10));
        TextView heading=new TextView(activity); heading.setText("ChatGPT Supervisor handoff"); heading.setTextSize(16); heading.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);
        TextView note=new TextView(activity); note.setText("JANUS records capability gaps and failures, but cannot approve or implement its own maintenance. Copy or share the complete request + retained Chat history packet to ChatGPT for private-repo review. Nothing is sent automatically."); note.setTextSize(12);
        panel.addView(heading,new LinearLayout.LayoutParams(-1,-2)); panel.addView(note,new LinearLayout.LayoutParams(-1,-2));
        LinearLayout actions=new LinearLayout(activity); actions.setOrientation(LinearLayout.HORIZONTAL); actions.setGravity(Gravity.CENTER_VERTICAL);
        Button copy=new Button(activity); copy.setText("Copy handoff"); copy.setAllCaps(false);
        Button share=new Button(activity); share.setText("Share to ChatGPT"); share.setAllCaps(false);
        copy.setOnClickListener(v->fetchPacket(activity,false)); share.setOnClickListener(v->fetchPacket(activity,true));
        actions.addView(copy,new LinearLayout.LayoutParams(0,dp(activity,52),1)); actions.addView(share,new LinearLayout.LayoutParams(0,dp(activity,52),1));
        panel.addView(actions,new LinearLayout.LayoutParams(-1,-2));
        layout.addView(panel,Math.min(title+2,layout.getChildCount()),new LinearLayout.LayoutParams(-1,-2));
    }

    private static void fetchPacket(Activity activity, boolean share) {
        Toast.makeText(activity,"Preparing Supervisor handoff…",Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            JanusApiClient.Response r=new JanusApiClient(activity).get("/maintenance/supervisor-handoff",true);
            String packet="";
            if(r.ok()) try { packet=new JSONObject(r.body).optString("packet",""); } catch(Exception ignored) {}
            final String text=packet;
            activity.runOnUiThread(() -> {
                if(text.isBlank()) { Toast.makeText(activity,"Supervisor handoff could not be prepared.",Toast.LENGTH_LONG).show(); return; }
                if(share) {
                    Intent send=new Intent(Intent.ACTION_SEND); send.setType("text/plain"); send.putExtra(Intent.EXTRA_SUBJECT,"JANUS Supervisor handoff"); send.putExtra(Intent.EXTRA_TEXT,text);
                    activity.startActivity(Intent.createChooser(send,"Send JANUS handoff to ChatGPT"));
                } else {
                    ClipboardManager cm=(ClipboardManager)activity.getSystemService(Context.CLIPBOARD_SERVICE);
                    if(cm!=null) cm.setPrimaryClip(ClipData.newPlainText("JANUS Supervisor handoff",text));
                    Toast.makeText(activity,"Supervisor handoff copied.",Toast.LENGTH_SHORT).show();
                }
            });
        },"janus-supervisor-handoff").start();
    }

    private static int dp(Activity a,int v){return Math.round(v*a.getResources().getDisplayMetrics().density);}
}
