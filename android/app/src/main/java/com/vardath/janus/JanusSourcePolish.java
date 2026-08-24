package com.vardath.janus;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/** Structured live Chat source renderer. Source metadata comes from the HTTP response registry, never text parsing. */
public final class JanusSourcePolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<LinearLayout> ENHANCED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Map<Activity, Runnable> PENDING = new WeakHashMap<>();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private JanusSourcePolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        View decor = activity.getWindow().getDecorView();
        decor.post(() -> run(activity));
        decor.getViewTreeObserver().addOnGlobalLayoutListener(() -> schedule(activity));
    }

    private static synchronized void schedule(Activity activity) {
        Runnable old = PENDING.remove(activity);
        if (old != null) MAIN.removeCallbacks(old);
        Runnable next = () -> {
            synchronized (JanusSourcePolish.class) { PENDING.remove(activity); }
            run(activity);
        };
        PENDING.put(activity, next);
        MAIN.postDelayed(next, 220L);
    }

    private static void run(Activity activity) {
        if (activity == null || activity.isFinishing() || activity.isDestroyed()) return;
        View root = activity.findViewById(android.R.id.content);
        if (root != null) walk(activity, root);
    }

    private static void walk(Activity activity, View view) {
        if (view instanceof LinearLayout) enhance(activity, (LinearLayout) view);
        if (view instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) view;
            for (int i=0;i<g.getChildCount();i++) walk(activity,g.getChildAt(i));
        }
    }

    private static void enhance(Activity activity, LinearLayout card) {
        if (ENHANCED.contains(card) || card.getChildCount() < 2) return;
        if (!(card.getChildAt(0) instanceof TextView) || !(card.getChildAt(1) instanceof TextView)) return;
        if (!"JANUS".contentEquals(((TextView)card.getChildAt(0)).getText())) return;
        TextView body = (TextView) card.getChildAt(1);
        JanusChatPresentation p = JanusChatResponseRegistry.consumeForReply(String.valueOf(body.getText()));
        if (p == null) return;
        ENHANCED.add(card);
        body.setText(p.reply);
        LinearLayout panel = buildPanel(activity,p.sources);
        if (panel != null) card.addView(panel, Math.min(2,card.getChildCount()), fullWithMargins(activity));
    }

    public static LinearLayout buildPanel(Activity activity, List<JanusChatPresentation.Source> sources) {
        if (activity == null || sources == null || sources.isEmpty()) return null;
        LinearLayout panel = new LinearLayout(activity); panel.setOrientation(LinearLayout.VERTICAL); panel.setPadding(dp(activity,10),dp(activity,8),dp(activity,10),dp(activity,8));
        GradientDrawable bg=rounded(activity,isDark(activity)?Color.rgb(31,34,38):Color.rgb(246,248,251),14); bg.setStroke(dp(activity,1),isDark(activity)?Color.rgb(70,76,84):Color.rgb(213,220,229)); panel.setBackground(bg);
        panel.addView(label(activity,"Sources · "+sources.size(),13,true),full());
        for(int i=0;i<sources.size();i++){
            JanusChatPresentation.Source source=sources.get(i); LinearLayout row=new LinearLayout(activity); row.setOrientation(LinearLayout.VERTICAL); row.setPadding(dp(activity,10),dp(activity,8),dp(activity,10),dp(activity,8));
            GradientDrawable rbg=rounded(activity,isDark(activity)?Color.rgb(42,45,50):Color.WHITE,12); rbg.setStroke(dp(activity,1),isDark(activity)?Color.rgb(67,73,80):Color.rgb(224,228,234)); row.setBackground(rbg);
            row.addView(label(activity,(i+1)+". "+source.title,13,true),full());
            if(!source.domain.isEmpty()) row.addView(label(activity,source.domain+(source.url.isEmpty()?"":" · Tap to open"),11,false),full());
            if(!source.url.isEmpty()){row.setClickable(true);row.setFocusable(true);row.setContentDescription("Open source "+source.title);row.setOnClickListener(v->openUrl(activity,source.url));}
            LinearLayout.LayoutParams lp=full();lp.setMargins(0,dp(activity,6),0,0);panel.addView(row,lp);
        }
        return panel;
    }

    private static TextView label(Activity a,String s,int size,boolean bold){TextView t=new TextView(a);t.setText(s);t.setTextSize(size);t.setTypeface(Typeface.DEFAULT,bold?Typeface.BOLD:Typeface.NORMAL);t.setTextColor(isDark(a)?Color.WHITE:Color.rgb(35,42,50));return t;}
    private static void openUrl(Activity a,String url){try{a.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));}catch(Exception ignored){}}
    private static LinearLayout.LayoutParams full(){return new LinearLayout.LayoutParams(-1,-2);}
    private static LinearLayout.LayoutParams fullWithMargins(Activity a){LinearLayout.LayoutParams lp=full();lp.setMargins(0,dp(a,4),0,dp(a,5));return lp;}
    private static GradientDrawable rounded(Activity a,int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(a,radius));return d;}
    private static boolean isDark(Activity a){int m=a.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;return m==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private static int dp(Activity a,int v){return Math.round(v*a.getResources().getDisplayMetrics().density);}
}
