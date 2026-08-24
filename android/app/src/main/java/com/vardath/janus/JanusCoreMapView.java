package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

/** Hardware-safe architecture map for JANUS' forward-only 1-3-7 / 7 -> 2 -> 1 -> 1 runtime. */
public final class JanusCoreMapView extends View {
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF box = new RectF();
    private static final String[] SPECIALISTS = {"1 Evidence","2 Safety","3 Counter","4 Context","5 Logic","6 Novelty","7 Memory"};

    public JanusCoreMapView(Context context) {
        super(context);
        setMinimumHeight(dp(350));
        setContentDescription("JANUS 1-3-7 architecture: seven subconscious Fano cores all feed both logic and imagination hemispheres, then Front appraisal, then Interface. Forward-only routing.");
        setPadding(dp(10), dp(10), dp(10), dp(10));
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        try { drawMap(canvas); }
        catch (Throwable ignored) { drawFallback(canvas); }
    }

    private void drawMap(Canvas c) {
        float w = getWidth() - getPaddingLeft() - getPaddingRight();
        float h = getHeight() - getPaddingTop() - getPaddingBottom();
        if (w < dp(120) || h < dp(220)) { drawFallback(c); return; }
        boolean dark = isDark();
        int fg = dark ? Color.rgb(244,244,244) : Color.rgb(24,24,24);
        int muted = dark ? Color.rgb(150,154,160) : Color.rgb(112,116,122);
        int surface = dark ? Color.rgb(43,44,47) : Color.rgb(246,247,249);
        int accent = accent();

        text.setTextAlign(Paint.Align.CENTER); text.setTextSize(sp(10.0f)); text.setColor(fg);
        fill.setStyle(Paint.Style.FILL);
        stroke.setStyle(Paint.Style.STROKE); stroke.setStrokeWidth(dp(1.2f)); stroke.setColor(muted);

        float left = getPaddingLeft();
        float top = getPaddingTop();
        float nodeW = Math.max(dp(62), Math.min(dp(96), (w - dp(18)) / 4f));
        float nodeH = dp(38); float gap = dp(6);
        float[][] centers = new float[7][2];
        for (int i=0;i<7;i++) {
            int row = i < 4 ? 0 : 1;
            int col = row == 0 ? i : i-4;
            int count = row == 0 ? 4 : 3;
            float rowWidth = count*nodeW + (count-1)*gap;
            float x = left + (w-rowWidth)/2f + col*(nodeW+gap);
            float y = top + dp(12) + row*dp(50);
            centers[i][0]=x+nodeW/2f; centers[i][1]=y+nodeH/2f;
            rounded(c,x,y,nodeW,nodeH,surface,dp(10));
            c.drawText(SPECIALISTS[i],centers[i][0],centers[i][1]+dp(4),text);
        }

        float leftH = left+w*.28f, rightH = left+w*.72f;
        float hemiY = top+dp(142), frontY=top+dp(225), interfaceY=top+dp(292);
        for (int i=0;i<7;i++) {
            line(c,centers[i][0],centers[i][1]+nodeH/2f,leftH,hemiY-dp(22));
            line(c,centers[i][0],centers[i][1]+nodeH/2f,rightH,hemiY-dp(22));
        }
        roundedCentered(c,leftH,hemiY,Math.min(dp(132),w*.39f),dp(44),surface,dp(12));
        roundedCentered(c,rightH,hemiY,Math.min(dp(132),w*.39f),dp(44),surface,dp(12));
        c.drawText("Left · logic",leftH,hemiY+dp(4),text); c.drawText("Right · imagination",rightH,hemiY+dp(4),text);
        line(c,leftH,hemiY+dp(22),left+w*.5f,frontY-dp(22)); line(c,rightH,hemiY+dp(22),left+w*.5f,frontY-dp(22));
        roundedCentered(c,left+w*.5f,frontY,Math.min(dp(180),w*.58f),dp(44),accent,dp(13));
        Paint inverse = new Paint(text); inverse.setColor(Color.WHITE); c.drawText("Front · appraisal / intent",left+w*.5f,frontY+dp(4),inverse);
        line(c,left+w*.5f,frontY+dp(22),left+w*.5f,interfaceY-dp(21));
        roundedCentered(c,left+w*.5f,interfaceY,Math.min(dp(180),w*.58f),dp(42),surface,dp(13));
        c.drawText("Interface · expression / action",left+w*.5f,interfaceY+dp(4),text);
    }

    private void drawFallback(Canvas c) {
        text.setColor(isDark()?Color.LTGRAY:Color.DKGRAY); text.setTextAlign(Paint.Align.CENTER); text.setTextSize(sp(11.5f));
        c.drawText("7 Fano senses → Left/Right → Front → Interface", getWidth()/2f, Math.max(dp(32),getHeight()/2f), text);
    }
    private void line(Canvas c,float x1,float y1,float x2,float y2){c.drawLine(x1,y1,x2,y2,stroke);}
    private void rounded(Canvas c,float x,float y,float w,float h,int color,float radius){fill.setColor(color);box.set(x,y,x+w,y+h);c.drawRoundRect(box,radius,radius,fill);c.drawRoundRect(box,radius,radius,stroke);}
    private void roundedCentered(Canvas c,float cx,float cy,float w,float h,int color,float radius){rounded(c,cx-w/2f,cy-h/2f,w,h,color,radius);}
    private boolean isDark(){SharedPreferences p=getContext().getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);String m=p.getString("theme_mode","system");if("dark".equals(m))return true;if("light".equals(m))return false;return (getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK)==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private int accent(){SharedPreferences p=getContext().getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);switch(p.getString("accent","slate")){case"indigo":return Color.rgb(63,81,181);case"teal":return Color.rgb(0,121,107);case"amber":return Color.rgb(190,112,0);case"violet":return Color.rgb(123,31,162);default:return isDark()?Color.rgb(100,112,125):Color.rgb(70,78,86);}}
    private int dp(float v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private float sp(float v){return v*getResources().getDisplayMetrics().scaledDensity;}
}
