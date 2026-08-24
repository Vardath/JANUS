package com.vardath.janus;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Typeface;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.DateFormat;
import java.util.Date;
import java.util.Locale;

/** Read-only native Observe surface for local/global externalizable core activity. */
public final class JanusObserveScreen {
    private JanusObserveScreen() {}

    public interface Host {
        Activity activity();
        JanusApiClient api();
        JanusLocalCoreRuntime localRuntime();
        String profile();
        String observeMode();
        void setObserveMode(String mode);
        void runIo(Runnable work);
        void runUi(Runnable work);
        void rerenderObserve();
    }

    public static void render(Host host, LinearLayout content) {
        if (host == null || content == null) return;
        Activity a = host.activity();
        content.addView(text(a, "Observe", 28, true), full());
        content.addView(text(a, "Readable externalizable JANUS process activity. Sensory cards identify where information came from. This is a stable, read-only snapshot and does not auto-jump while you read it.", 13, false), full());
        LinearLayout filters = horizontal(a);
        for (String mode : new String[]{"all", "thoughts", "interactions"}) {
            Button b = button(a, mode.equals("all") ? "All" : capitalize(mode));
            b.setAlpha(mode.equals(host.observeMode()) ? 1f : .62f);
            b.setOnClickListener(v -> { host.setObserveMode(mode); host.rerenderObserve(); });
            filters.addView(b, weight());
        }
        content.addView(filters, full());
        LinearLayout list = vertical(a); ScrollView scroll = new ScrollView(a); scroll.addView(list, full()); content.addView(scroll, new LinearLayout.LayoutParams(-1,0,1));
        Button refresh = button(a, "Refresh snapshot"); refresh.setOnClickListener(v -> load(host, list)); content.addView(refresh, full());
        load(host, list);
    }

    private static void load(Host host, LinearLayout list) {
        Activity a = host.activity(); list.removeAllViews(); list.addView(text(a, "Loading local and global core activity…", 14, false));
        host.runIo(() -> {
            JSONArray localItems = new JSONArray();
            try { JSONObject local = host.localRuntime().statusJson(); JSONArray ev = local.optJSONArray("observe_events"); if (ev != null) localItems = ev; } catch (Exception ignored) {}
            JanusApiClient.Response server = host.api().get("/desktop/core-observe?username=" + enc(host.profile()) + "&mode=" + enc(host.observeMode()) + "&limit=180", true);
            JSONArray serverItems = new JSONArray(); if (server.ok()) try { JSONArray x = new JSONObject(server.body).optJSONArray("items"); if (x != null) serverItems = x; } catch (Exception ignored) {}
            final JSONArray lf = localItems, sf = serverItems;
            host.runUi(() -> { list.removeAllViews(); int shown = 0; for (int i=lf.length()-1;i>=0 && shown<80;i--) { JSONObject x=lf.optJSONObject(i); if (x==null || !matches(host.observeMode(),x)) continue; addCard(a,list,x,"This device"); shown++; } for (int i=0;i<sf.length() && shown<160;i++) { JSONObject x=sf.optJSONObject(i); if (x==null || !matches(host.observeMode(),x)) continue; addCard(a,list,x,x.optString("source","Global JANUS")); shown++; } if (shown==0) list.addView(text(a,"No observable core activity in this snapshot.",15,false)); });
        });
    }

    private static boolean matches(String mode, JSONObject x) { if ("all".equals(mode)) return true; String type=x.optString("event_type","").toLowerCase(Locale.ROOT); return "interactions".equals(mode) ? type.contains("interaction") : !type.contains("interaction"); }

    private static void addCard(Activity a, LinearLayout list, JSONObject x, String source) {
        LinearLayout card=card(a);
        String core=pretty(x.optString("core_name","core"));
        String peer=x.optString("peer_core","");
        String route=peer.isEmpty()?core:core+" → "+pretty(peer);
        String eventType=x.optString("event_type","note");
        card.addView(text(a,route+" · "+pretty(eventType),13,true));
        String provenance=provenance(x,source);
        if(!provenance.isBlank()) card.addView(text(a,provenance,12,true));
        card.addView(text(a,x.optString("detail",x.optString("summary","")),15,false));
        card.addView(text(a,formatTime(x.opt("created_at"))+" · "+source,12,false));
        String raw=x.optString("raw_detail","");
        if(!raw.isBlank()&&!raw.equals(x.optString("detail",""))){ Button tech=button(a,"Technical details"); tech.setOnClickListener(v->new AlertDialog.Builder(a).setTitle(route).setMessage(raw).setPositiveButton("Close",null).show()); card.addView(tech,wrap()); }
        list.addView(card,full());
    }

    /** Externalizable provenance only; never exposes credentials or hidden reasoning. */
    private static String provenance(JSONObject x, String displaySource) {
        String type=x.optString("event_type","");
        if(!"sensory_input".equals(type) && x.optString("sense_modality","").isBlank()) return "";
        String modality=x.optString("sense_modality","");
        String origin=x.optString("sense_origin","");
        String detail=x.optString("detail","");
        if(modality.isBlank()) {
            String low=detail.toLowerCase(Locale.ROOT);
            int a=low.indexOf("a "); int b=low.indexOf(" sense");
            if(a>=0 && b>a+2) modality=detail.substring(a+2,b).trim();
        }
        if(origin.isBlank()) {
            String core=x.optString("core_name","");
            if(!core.isBlank() && !isCanonicalCore(core)) origin=core;
            else origin=displaySource;
        }
        return "Sense · " + pretty(modality.isBlank()?"unknown":modality) + " · from " + prettyOrigin(origin);
    }

    private static boolean isCanonicalCore(String s) {
        String x=s==null?"":s;
        return x.equals("evidence")||x.equals("safety")||x.equals("counterpoint")||x.equals("context")||x.equals("logic")||x.equals("novelty")||x.equals("memory")||x.equals("left_hemisphere")||x.equals("right_hemisphere")||x.equals("front")||x.equals("consensus")||x.equals("interface");
    }

    private static String prettyOrigin(String s) {
        String x=s==null?"":s.replace('_',' ').replace(":"," · ");
        return x.isBlank()?"unknown":x;
    }

    private static LinearLayout vertical(Activity a){LinearLayout x=new LinearLayout(a);x.setOrientation(LinearLayout.VERTICAL);return x;} private static LinearLayout horizontal(Activity a){LinearLayout x=new LinearLayout(a);x.setOrientation(LinearLayout.HORIZONTAL);return x;}
    private static LinearLayout card(Activity a){LinearLayout x=vertical(a);int p=dp(a,12);x.setPadding(p,p,p,p);LinearLayout.LayoutParams lp=full();lp.setMargins(0,dp(a,6),0,dp(a,6));x.setLayoutParams(lp);x.setBackgroundColor(0x181C8CFF);return x;}
    private static TextView text(Activity a,String s,int sp,boolean bold){TextView v=new TextView(a);v.setText(s);v.setTextSize(sp);v.setTextColor(0xffe8eef7);if(bold)v.setTypeface(Typeface.DEFAULT_BOLD);v.setPadding(dp(a,4),dp(a,5),dp(a,4),dp(a,5));return v;}
    private static Button button(Activity a,String s){Button b=new Button(a);b.setText(s);b.setAllCaps(false);b.setGravity(Gravity.CENTER);return b;}
    private static LinearLayout.LayoutParams full(){return new LinearLayout.LayoutParams(-1,-2);} private static LinearLayout.LayoutParams wrap(){return new LinearLayout.LayoutParams(-2,-2);} private static LinearLayout.LayoutParams weight(){return new LinearLayout.LayoutParams(0,-2,1);} private static int dp(Activity a,int n){return Math.round(n*a.getResources().getDisplayMetrics().density);}
    private static String enc(String s){try{return java.net.URLEncoder.encode(s==null?"":s,"UTF-8");}catch(Exception e){return "";}} private static String capitalize(String s){return s==null||s.isEmpty()?"":s.substring(0,1).toUpperCase(Locale.ROOT)+s.substring(1);} private static String pretty(String s){return capitalize((s==null?"":s).replace('_',' '));}
    private static String formatTime(Object raw){if(raw==null)return "";if(raw instanceof Number){long n=((Number)raw).longValue();if(n<100000000000L)n*=1000L;return DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT).format(new Date(n));}return String.valueOf(raw);}
}
