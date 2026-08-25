package com.vardath.janus;

import android.app.Activity;
import android.graphics.Typeface;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.reflect.Field;
import java.text.DateFormat;
import java.util.Date;

/** Read-only Front/stream-of-consciousness observer. Exposes bounded state, never hidden CoT. */
public final class JanusStreamObservePolish {
    private JanusStreamObservePolish() {}

    public static void install(Activity activity) {
        if (activity == null) return;
        new Handler(Looper.getMainLooper()).postDelayed(() -> attach(activity), 350);
    }

    private static void attach(Activity a) {
        Button observe = findButton(a.findViewById(android.R.id.content), "Observe");
        if (observe == null || !(observe.getParent() instanceof LinearLayout)) return;
        LinearLayout nav = (LinearLayout) observe.getParent();
        if (findButton(nav, "Stream") != null) return;
        Button stream = new Button(a); stream.setText("Stream"); stream.setAllCaps(false);
        stream.setOnClickListener(v -> render(a));
        nav.addView(stream, new LinearLayout.LayoutParams(0, dp(a,58), 1));
    }

    private static void render(Activity a) {
        try {
            LinearLayout content = (LinearLayout) field(a,"content");
            JanusApiClient api = (JanusApiClient) field(a,"api");
            if (content == null || api == null) return;
            content.removeAllViews();
            content.addView(text(a,"Stream of Consciousness",28,true),full());
            content.addView(text(a,"Read-only externalizable activity from JANUS Front, the single integrated stream that receives Left and Right before Interface. This does not expose hidden chain-of-thought.",13,false),full());
            LinearLayout list=new LinearLayout(a);list.setOrientation(LinearLayout.VERTICAL);ScrollView scroll=new ScrollView(a);scroll.addView(list,full());content.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
            Button refresh=new Button(a);refresh.setText("Refresh stream snapshot");refresh.setAllCaps(false);refresh.setOnClickListener(v->load(a,api,list));content.addView(refresh,full());
            load(a,api,list);
        } catch(Exception ignored) {}
    }

    private static void load(Activity a, JanusApiClient api, LinearLayout list) {
        list.removeAllViews();list.addView(text(a,"Loading Front stream…",14,false));
        new Thread(() -> {
            JSONObject local=JanusRecursiveCoreBridge.snapshot();
            JanusApiClient.Response r=api.get("/desktop/stream-observe?limit=160",true);
            JSONObject server=new JSONObject();try{if(r.ok())server=new JSONObject(r.body);}catch(Exception ignored){}
            JSONObject finalServer=server;
            a.runOnUiThread(() -> {
                list.removeAllViews();
                try {
                    JSONObject localFront=local.optJSONObject("cores")==null?null:local.optJSONObject("cores").optJSONObject("front");
                    if(localFront!=null)addStateCard(a,list,"This device · Front",localFront,"Local recursive Front state");
                    JSONObject current=finalServer.optJSONObject("current"); JSONObject globalFront=current==null?null:current.optJSONObject("recursive_janus");
                    if(globalFront!=null)addStateCard(a,list,"Global JANUS · Front",globalFront,"Server recursive Front state · phase "+finalServer.optString("phase","unknown"));
                    JSONArray items=finalServer.optJSONArray("items");
                    if(items!=null)for(int i=0;i<items.length();i++){JSONObject x=items.optJSONObject(i);if(x==null)continue;LinearLayout card=card(a);card.addView(text(a,"Front · "+pretty(x.optString("event_type","event")),13,true));card.addView(text(a,x.optString("detail",""),15,false));card.addView(text(a,formatTime(x.opt("created_at"))+" · "+x.optString("mode","foreground"),12,false));list.addView(card,full());}
                    if(list.getChildCount()==0)list.addView(text(a,"No stream activity retained yet.",15,false));
                } catch(Exception e){list.addView(text(a,"Stream snapshot could not be displayed.",14,false));}
            });
        },"janus-stream-observe").start();
    }

    private static void addStateCard(Activity a,LinearLayout list,String title,JSONObject x,String subtitle){LinearLayout card=card(a);card.addView(text(a,title,14,true));card.addView(text(a,subtitle,12,false));card.addView(text(a,"Fano: d"+x.optInt("active_direction",0)+" "+x.optString("active_faculty","reference")+" · cycles "+x.optLong("cycles",0)+" · revisions "+x.optLong("revision_count",0)+" · peer turns "+x.optLong("peer_turn_count",0)+" · quiescent "+x.optLong("quiescent_count",0),13,false));String c=x.optString("conclusion","");if(!c.isBlank())card.addView(text(a,c,14,false));list.addView(card,full());}
    private static Object field(Activity a,String name)throws Exception{Field f=a.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(a);}
    private static Button findButton(View v,String exact){if(v instanceof Button&&exact.equals(String.valueOf(((Button)v).getText()).trim()))return(Button)v;if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++){Button b=findButton(g.getChildAt(i),exact);if(b!=null)return b;}}return null;}
    private static LinearLayout card(Activity a){LinearLayout x=new LinearLayout(a);x.setOrientation(LinearLayout.VERTICAL);int p=dp(a,12);x.setPadding(p,p,p,p);x.setBackgroundColor(0x181C8CFF);LinearLayout.LayoutParams lp=full();lp.setMargins(0,dp(a,6),0,dp(a,6));x.setLayoutParams(lp);return x;}
    private static TextView text(Activity a,String s,int sp,boolean bold){TextView v=new TextView(a);v.setText(s);v.setTextSize(sp);v.setTextColor(0xffe8eef7);if(bold)v.setTypeface(Typeface.DEFAULT_BOLD);v.setPadding(dp(a,4),dp(a,5),dp(a,4),dp(a,5));return v;}
    private static LinearLayout.LayoutParams full(){return new LinearLayout.LayoutParams(-1,-2);}private static int dp(Activity a,int n){return Math.round(n*a.getResources().getDisplayMetrics().density);}private static String pretty(String s){return(s==null?"":s.replace('_',' '));}private static String formatTime(Object raw){if(raw instanceof Number){long n=((Number)raw).longValue();if(n<100000000000L)n*=1000L;return DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT).format(new Date(n));}return String.valueOf(raw==null?"":raw);}
}
