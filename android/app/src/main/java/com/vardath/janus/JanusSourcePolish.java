package com.vardath.janus;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.List;

/** Direct structured source-card renderer. No text appendix parsing. */
public final class JanusSourcePolish {
    private JanusSourcePolish() {}
    public static void install(Activity activity) { /* retained lifecycle hook; direct rendering is authoritative in v0.93 */ }

    public static LinearLayout buildPanel(Activity activity, List<JanusChatPresentation.Source> sources) {
        if (activity == null || sources == null || sources.isEmpty()) return null;
        LinearLayout panel = new LinearLayout(activity);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(activity,10),dp(activity,8),dp(activity,10),dp(activity,8));
        GradientDrawable bg = rounded(activity, isDark(activity)?Color.rgb(31,34,38):Color.rgb(246,248,251),14);
        bg.setStroke(dp(activity,1),isDark(activity)?Color.rgb(70,76,84):Color.rgb(213,220,229)); panel.setBackground(bg);
        TextView heading = label(activity,"Sources · " + sources.size(),13,true); panel.addView(heading,full());
        for (int i=0;i<sources.size();i++) {
            JanusChatPresentation.Source source=sources.get(i);
            LinearLayout row=new LinearLayout(activity); row.setOrientation(LinearLayout.VERTICAL); row.setPadding(dp(activity,10),dp(activity,8),dp(activity,10),dp(activity,8));
            GradientDrawable rbg=rounded(activity,isDark(activity)?Color.rgb(42,45,50):Color.WHITE,12); rbg.setStroke(dp(activity,1),isDark(activity)?Color.rgb(67,73,80):Color.rgb(224,228,234)); row.setBackground(rbg);
            row.addView(label(activity,(i+1)+". "+source.title,13,true),full());
            if (!source.domain.isEmpty()) row.addView(label(activity,source.domain + (source.url.isEmpty()?"":" · Tap to open"),11,false),full());
            if (!source.url.isEmpty()) { row.setClickable(true); row.setFocusable(true); row.setContentDescription("Open source " + source.title); row.setOnClickListener(v->openUrl(activity,source.url)); }
            LinearLayout.LayoutParams lp=full(); lp.setMargins(0,i==0?dp(activity,5):dp(activity,6),0,0); panel.addView(row,lp);
        }
        return panel;
    }

    private static TextView label(Activity a,String s,int size,boolean bold){ TextView t=new TextView(a); t.setText(s); t.setTextSize(size); t.setTypeface(Typeface.DEFAULT,bold?Typeface.BOLD:Typeface.NORMAL); t.setTextColor(isDark(a)?Color.WHITE:Color.rgb(35,42,50)); return t; }
    private static void openUrl(Activity a,String url){ try{ a.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }catch(Exception ignored){} }
    private static LinearLayout.LayoutParams full(){ return new LinearLayout.LayoutParams(-1,-2); }
    private static GradientDrawable rounded(Activity a,int color,int radius){ GradientDrawable d=new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(a,radius)); return d; }
    private static boolean isDark(Activity a){ int m=a.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK; return m==android.content.res.Configuration.UI_MODE_NIGHT_YES; }
    private static int dp(Activity a,int v){ return Math.round(v*a.getResources().getDisplayMetrics().density); }
}
