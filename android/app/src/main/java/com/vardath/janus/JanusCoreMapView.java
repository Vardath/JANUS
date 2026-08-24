package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.View;

/** Readable, deliberately calm map of JANUS's forward-only 7 -> 2 -> 1 -> 1 runtime. */
public final class JanusCoreMapView extends View {
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint node = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint small = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF r = new RectF();

    private static final String[] SPECIALISTS = {
            "Evidence", "Logic", "Counterpoint", "Context", "Memory", "Safety", "Novelty"
    };

    public JanusCoreMapView(Context context) {
        super(context);
        setMinimumHeight(dp(360));
        setContentDescription("JANUS architecture: seven specialists feed two hemispheres, then Consensus, then Interface. Forward-only routing.");
        setPadding(dp(12), dp(12), dp(12), dp(12));
        setLayerType(View.LAYER_TYPE_SOFTWARE, null);
    }

    @Override protected void onDraw(Canvas c) {
        super.onDraw(c);
        boolean dark = isDark();
        int fg = dark ? Color.rgb(244,244,244) : Color.rgb(24,24,24);
        int muted = dark ? Color.rgb(168,172,178) : Color.rgb(100,104,110);
        int surface = dark ? Color.rgb(42,43,46) : Color.rgb(247,248,250);
        int edge = dark ? Color.rgb(92,98,106) : Color.rgb(185,190,198);
        int accent = accent();

        text.setColor(fg); text.setTextAlign(Paint.Align.CENTER); text.setTextSize(sp(12)); text.setFakeBoldText(true);
        small.setColor(muted); small.setTextAlign(Paint.Align.CENTER); small.setTextSize(sp(10)); small.setFakeBoldText(false);
        line.setColor(edge); line.setStrokeWidth(dp(1.5f)); line.setStyle(Paint.Style.STROKE);
        node.setStyle(Paint.Style.FILL); node.setColor(surface); node.setShadowLayer(dp(2), 0, dp(1), dark ? 0x55000000 : 0x22000000);

        float w = getWidth() - getPaddingLeft() - getPaddingRight();
        float left = getPaddingLeft();
        float top = getPaddingTop() + dp(8);
        float specialistY = top + dp(30);
        float hemiY = top + dp(160);
        float consensusY = top + dp(245);
        float interfaceY = top + dp(315);

        float specialistW = Math.max(dp(62), (w - dp(18)) / 4f);
        float specialistH = dp(42);
        float gap = dp(6);

        float[][] centers = new float[7][2];
        for (int i = 0; i < 7; i++) {
            int row = i < 4 ? 0 : 1;
            int col = row == 0 ? i : i - 4;
            int count = row == 0 ? 4 : 3;
            float rowWidth = count * specialistW + (count - 1) * gap;
            float x0 = left + (w - rowWidth) / 2f;
            float x = x0 + col * (specialistW + gap);
            float y = specialistY + row * dp(54);
            centers[i][0] = x + specialistW / 2f;
            centers[i][1] = y + specialistH / 2f;
            rounded(c, x, y, specialistW, specialistH, surface, dp(13));
            drawCentered(c, SPECIALISTS[i], centers[i][0], centers[i][1] + dp(4), text);
        }

        float hemiW = Math.min(dp(142), w * .39f);
        float hemiH = dp(50);
        float leftHemiX = left + w * .25f;
        float rightHemiX = left + w * .75f;
        float consensusX = left + w * .5f;

        // Forward routes. Safety (index 5) visibly advises both hemispheres.
        for (int i = 0; i < 7; i++) {
            float target = (i <= 2) ? leftHemiX : rightHemiX;
            if (i == 5) {
                route(c, centers[i][0], centers[i][1] + specialistH/2f, leftHemiX, hemiY - hemiH/2f, edge);
                route(c, centers[i][0], centers[i][1] + specialistH/2f, rightHemiX, hemiY - hemiH/2f, edge);
            } else {
                route(c, centers[i][0], centers[i][1] + specialistH/2f, target, hemiY - hemiH/2f, edge);
            }
        }

        roundedCentered(c, leftHemiX, hemiY, hemiW, hemiH, surface, dp(15));
        roundedCentered(c, rightHemiX, hemiY, hemiW, hemiH, surface, dp(15));
        drawCentered(c, "Left hemisphere", leftHemiX, hemiY + dp(4), text);
        drawCentered(c, "Right hemisphere", rightHemiX, hemiY + dp(4), text);

        route(c, leftHemiX, hemiY + hemiH/2f, consensusX, consensusY - dp(24), edge);
        route(c, rightHemiX, hemiY + hemiH/2f, consensusX, consensusY - dp(24), edge);

        roundedCentered(c, consensusX, consensusY, Math.min(dp(180), w*.56f), dp(48), accent, dp(16));
        Paint white = new Paint(text); white.setColor(Color.WHITE);
        drawCentered(c, "Consensus", consensusX, consensusY + dp(4), white);

        route(c, consensusX, consensusY + dp(24), consensusX, interfaceY - dp(23), edge);
        roundedCentered(c, consensusX, interfaceY, Math.min(dp(180), w*.56f), dp(46), surface, dp(16));
        drawCentered(c, "Interface", consensusX, interfaceY + dp(4), text);

        small.setTextAlign(Paint.Align.LEFT);
        c.drawText("Forward-only routing · global feedback re-enters through specialist review", left, getHeight() - dp(8), small);
    }

    private void route(Canvas c, float x1, float y1, float x2, float y2, int color) {
        line.setColor(color);
        Path p = new Path(); p.moveTo(x1,y1); p.lineTo(x2,y2); c.drawPath(p,line);
        float angle = (float)Math.atan2(y2-y1,x2-x1);
        float a = dp(6); float wing = .58f;
        Path arrow = new Path();
        arrow.moveTo(x2,y2);
        arrow.lineTo(x2 - a*(float)Math.cos(angle-wing), y2 - a*(float)Math.sin(angle-wing));
        arrow.moveTo(x2,y2);
        arrow.lineTo(x2 - a*(float)Math.cos(angle+wing), y2 - a*(float)Math.sin(angle+wing));
        c.drawPath(arrow,line);
    }

    private void rounded(Canvas c, float x,float y,float w,float h,int color,float radius) {
        node.setColor(color); r.set(x,y,x+w,y+h); c.drawRoundRect(r,radius,radius,node);
    }
    private void roundedCentered(Canvas c,float cx,float cy,float w,float h,int color,float radius){rounded(c,cx-w/2f,cy-h/2f,w,h,color,radius);}
    private void drawCentered(Canvas c,String s,float x,float y,Paint p){c.drawText(s,x,y,p);}

    private boolean isDark(){SharedPreferences p=getContext().getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);String m=p.getString("theme_mode","system");if("dark".equals(m))return true;if("light".equals(m))return false;return (getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK)==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private int accent(){SharedPreferences p=getContext().getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);switch(p.getString("accent","slate")){case"indigo":return Color.rgb(63,81,181);case"teal":return Color.rgb(0,121,107);case"amber":return Color.rgb(215,125,0);case"violet":return Color.rgb(123,31,162);default:return isDark()?Color.rgb(100,112,125):Color.rgb(60,72,84);}}
    private int dp(float v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private float sp(float v){return v*getResources().getDisplayMetrics().scaledDensity;}
}
