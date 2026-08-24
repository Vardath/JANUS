package com.vardath.janus;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.text.util.Linkify;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/** App-wide native chrome/readability layer. v1.04 makes all decoration idempotent and debounced. */
public final class JanusUiPolish {
    private static final Set<Activity> INSTALLED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<View> BASE_POLISHED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<LinearLayout> CHAT_ENHANCED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<LinearLayout> CORE_MAP_HOSTS = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Set<LinearLayout> OBSERVE_GUIDE_HOSTS = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Map<Activity, Runnable> PENDING = new WeakHashMap<>();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final long POLISH_DEBOUNCE_MS = 180L;

    private JanusUiPolish() {}

    public static void install(Activity activity) {
        if (activity == null || INSTALLED.contains(activity)) return;
        INSTALLED.add(activity);
        Window window = activity.getWindow();
        WindowCompat.setDecorFitsSystemWindows(window, false);
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);
        View content = activity.findViewById(android.R.id.content);
        if (content != null) {
            ViewCompat.setOnApplyWindowInsetsListener(content, (view, insets) -> {
                Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
                Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, ime.bottom));
                return insets;
            });
            ViewCompat.requestApplyInsets(content);
        }
        applySystemBarContrast(activity);
        View decor = activity.getWindow().getDecorView();
        decor.post(() -> runPolish(activity));
        decor.getViewTreeObserver().addOnGlobalLayoutListener(() -> schedulePolish(activity));
    }

    private static synchronized void schedulePolish(Activity activity) {
        Runnable old = PENDING.remove(activity);
        if (old != null) MAIN.removeCallbacks(old);
        Runnable next = () -> {
            synchronized (JanusUiPolish.class) { PENDING.remove(activity); }
            runPolish(activity);
        };
        PENDING.put(activity, next);
        MAIN.postDelayed(next, POLISH_DEBOUNCE_MS);
    }

    private static void runPolish(Activity activity) {
        if (activity == null || activity.isFinishing() || activity.isDestroyed()) return;
        View root = activity.findViewById(android.R.id.content);
        if (root != null) polishTree(activity, root);
    }

    private static void applySystemBarContrast(Activity activity) {
        boolean dark = isDark(activity);
        WindowInsetsControllerCompat c = WindowCompat.getInsetsController(activity.getWindow(), activity.getWindow().getDecorView());
        if (c != null) { c.setAppearanceLightStatusBars(!dark); c.setAppearanceLightNavigationBars(!dark); }
    }

    private static void polishTree(Activity activity, View view) {
        boolean first = BASE_POLISHED.add(view);
        if (first) {
            if (view instanceof Button) styleButton(activity, (Button) view);
            else if (view instanceof EditText) styleInput(activity, (EditText) view);
            else if (view instanceof TextView) styleText((TextView) view);
            if (view instanceof ImageView) styleImage(activity, (ImageView) view);
            if (view instanceof LinearLayout) styleSurface(activity, (LinearLayout) view);
        }
        if (view instanceof LinearLayout) {
            LinearLayout layout = (LinearLayout) view;
            enhanceChatCard(activity, layout);
            enhanceRuntimeCard(activity, layout);
            enhanceObserveCard(activity, layout);
            injectArchitectureMap(activity, layout);
            injectObserveGuide(activity, layout);
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) polishTree(activity, group.getChildAt(i));
        }
    }

    private static void styleButton(Activity activity, Button button) {
        button.setAllCaps(false);
        button.setMinHeight(dp(activity, 46));
        button.setTextSize(14);
        button.setPadding(dp(activity, 12), dp(activity, 7), dp(activity, 12), dp(activity, 7));
        Object tag = button.getTag();
        boolean nav = tag instanceof String && ("Chat".equals(tag) || "Messages".equals(tag) || "Observe".equals(tag) || "Options".equals(tag));
        String label = String.valueOf(button.getText());
        boolean chip = label.startsWith("× ") || "+".equals(label);
        int surface = elevatedSurface(activity);
        int text = textColor(activity);
        if (nav) {
            boolean selected = button.getAlpha() > 0.9f;
            button.setBackgroundTintList(ColorStateList.valueOf(selected ? withAlpha(accent(activity), 235) : surface));
            button.setTextColor(selected ? Color.WHITE : text);
            button.setMinHeight(dp(activity, 52));
        } else if (chip) {
            button.setBackgroundTintList(ColorStateList.valueOf(withAlpha(accent(activity), isDark(activity) ? 95 : 40)));
            button.setTextColor(text);
            button.setMinHeight(dp(activity, 40));
        } else {
            button.setBackgroundTintList(ColorStateList.valueOf(surface));
            button.setTextColor(text);
        }
    }

    private static void styleInput(Activity activity, EditText input) {
        input.setMinHeight(dp(activity, 52));
        input.setTextColor(textColor(activity));
        input.setHintTextColor(mutedColor(activity));
        input.setPadding(dp(activity, 14), dp(activity, 10), dp(activity, 14), dp(activity, 10));
        GradientDrawable bg = rounded(activity, elevatedSurface(activity), 16);
        bg.setStroke(dp(activity, 1), withAlpha(mutedColor(activity), 90));
        input.setBackground(bg);
    }

    private static void styleText(TextView text) {
        CharSequence value = text.getText();
        if (value != null) {
            String s = value.toString();
            if (s.contains("http")) { text.setAutoLinkMask(Linkify.WEB_URLS); text.setLinksClickable(true); }
            if (s.startsWith("Fano direction d")) {
                int d = parseFano(s);
                if (d >= 0) text.setText(fanoName(d) + " · d" + d + " · processing orientation, not a truth score");
            }
        }
        text.setLineSpacing(0f, 1.10f);
    }

    private static int parseFano(String s) {
        try {
            String marker = "Fano direction d";
            int start = s.indexOf(marker) + marker.length();
            int end = start;
            while (end < s.length() && Character.isDigit(s.charAt(end))) end++;
            return Integer.parseInt(s.substring(start, end));
        } catch (Exception ignored) { return -1; }
    }

    private static String fanoName(int d) {
        switch (d) {
            case 0: return "Neutral / conservative";
            case 1: return "Grounding";
            case 2: return "Structure";
            case 3: return "Synthesis";
            case 4: return "Alternative / counterfactual";
            case 5: return "Continuity / memory";
            case 6: return "Novelty / exploration";
            case 7: return "Boundary / uncertainty";
            default: return "Fano orientation";
        }
    }

    private static void styleSurface(Activity activity, LinearLayout layout) {
        if (!(layout.getBackground() instanceof ColorDrawable)) return;
        int existing = ((ColorDrawable) layout.getBackground()).getColor();
        int surface = isDark(activity) ? Color.rgb(37,37,37) : Color.rgb(243,243,243);
        int user = isDark(activity) ? Color.rgb(37,55,76) : Color.rgb(222,237,255);
        if (existing != surface && existing != user) return;
        GradientDrawable d = rounded(activity, existing, 18);
        if (existing == surface) d.setStroke(dp(activity,1), withAlpha(mutedColor(activity),45));
        layout.setBackground(d);
        layout.setElevation(dp(activity,1));
    }

    private static void enhanceChatCard(Activity activity, LinearLayout layout) {
        if (CHAT_ENHANCED.contains(layout) || layout.getChildCount() < 2) return;
        if (!(layout.getChildAt(0) instanceof TextView) || !(layout.getChildAt(1) instanceof TextView)) return;
        String who = String.valueOf(((TextView) layout.getChildAt(0)).getText());
        if (!("JANUS".equals(who) || "You".equals(who) || "System".equals(who))) return;
        CHAT_ENHANCED.add(layout);
        TextView body = (TextView) layout.getChildAt(1);
        body.setTextIsSelectable(true);
        body.setPadding(body.getPaddingLeft(), dp(activity,4), body.getPaddingRight(), dp(activity,8));
        if ("JANUS".equals(who)) {
            LinearLayout actions = new LinearLayout(activity);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
            Button copy = compactButton(activity, "Copy");
            Button share = compactButton(activity, "Share");
            copy.setOnClickListener(v -> {
                ClipboardManager cm = (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);
                if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("JANUS response", body.getText()));
                Toast.makeText(activity, "Copied JANUS response.", Toast.LENGTH_SHORT).show();
            });
            share.setOnClickListener(v -> {
                Intent send = new Intent(Intent.ACTION_SEND);
                send.setType("text/plain");
                send.putExtra(Intent.EXTRA_TEXT, body.getText().toString());
                activity.startActivity(Intent.createChooser(send, "Share JANUS response"));
            });
            actions.addView(copy); actions.addView(share);
            layout.addView(actions, new LinearLayout.LayoutParams(-1, -2));
        } else if ("System".equals(who)) {
            layout.setAlpha(.88f);
            ((TextView) layout.getChildAt(0)).setText("Delivery status");
        }
    }

    private static void enhanceRuntimeCard(Activity activity, LinearLayout layout) {
        if (layout.getChildCount() == 0 || !(layout.getChildAt(0) instanceof TextView) || layout.getChildAt(0) instanceof Button) return;
        TextView title = (TextView) layout.getChildAt(0);
        String label = String.valueOf(title.getText());
        if (label.startsWith("THIS DEVICE · LOCAL JANUS")) {
            title.setText("● THIS DEVICE · LOCAL JANUS"); title.setTextColor(accent(activity)); outline(layout, activity, accent(activity), 105);
        } else if (label.startsWith("ONLINE · GLOBAL JANUS")) {
            title.setText("◆ ONLINE · GLOBAL JANUS"); title.setTextColor(textColor(activity)); outline(layout, activity, mutedColor(activity), 70);
        }
    }

    private static void enhanceObserveCard(Activity activity, LinearLayout layout) {
        if (layout.getChildCount() < 3) return;
        View metaView = layout.getChildAt(2);
        if (!(metaView instanceof TextView) || metaView instanceof Button) return;
        TextView meta = (TextView) metaView;
        String s = String.valueOf(meta.getText());
        if (s.contains(" · This device") && !s.contains("LOCAL ·")) {
            meta.setText("LOCAL · " + s.replace(" · This device", "")); meta.setTextColor(accent(activity)); outline(layout, activity, accent(activity), 80);
        } else if ((s.contains("Global JANUS") || s.contains("global")) && !s.contains("GLOBAL ·")) {
            meta.setText("GLOBAL · " + s.replace(" · Global JANUS", "")); meta.setTextColor(mutedColor(activity)); outline(layout, activity, mutedColor(activity), 55);
        }
    }

    private static void injectArchitectureMap(Activity activity, LinearLayout layout) {
        if (CORE_MAP_HOSTS.contains(layout)) return;
        int titleIndex = directTextIndex(layout, "Runtime Cores");
        if (titleIndex < 0) return;
        CORE_MAP_HOSTS.add(layout);
        LinearLayout panel = new LinearLayout(activity);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(activity,10),dp(activity,6),dp(activity,10),dp(activity,8));
        TextView hint = new TextView(activity);
        hint.setText("Architecture map · local and global JANUS share the same permitted forward topology");
        hint.setTextColor(mutedColor(activity)); hint.setTextSize(12); hint.setPadding(dp(activity,4),0,dp(activity,4),dp(activity,4));
        panel.addView(hint, new LinearLayout.LayoutParams(-1,-2));
        JanusCoreMapView map = new JanusCoreMapView(activity);
        panel.addView(map, new LinearLayout.LayoutParams(-1, dp(activity,350)));
        layout.addView(panel, Math.min(titleIndex + 1, layout.getChildCount()), new LinearLayout.LayoutParams(-1,-2));
    }

    private static void injectObserveGuide(Activity activity, LinearLayout layout) {
        if (OBSERVE_GUIDE_HOSTS.contains(layout)) return;
        int titleIndex = directTextIndex(layout, "Observe");
        if (titleIndex < 0) return;
        OBSERVE_GUIDE_HOSTS.add(layout);
        TextView guide = new TextView(activity);
        guide.setText("Stable snapshot · LOCAL and GLOBAL activity stay visually distinct · Refresh only when you choose");
        guide.setTextColor(mutedColor(activity)); guide.setTextSize(12);
        guide.setPadding(dp(activity,6),dp(activity,2),dp(activity,6),dp(activity,5));
        layout.addView(guide, Math.min(titleIndex + 2, layout.getChildCount()), new LinearLayout.LayoutParams(-1,-2));
    }

    private static int directTextIndex(LinearLayout layout, String value) {
        for (int i=0;i<layout.getChildCount();i++) {
            View child = layout.getChildAt(i);
            if (child instanceof TextView && !(child instanceof Button) && value.equals(String.valueOf(((TextView) child).getText()))) return i;
        }
        return -1;
    }

    private static void outline(LinearLayout layout, Activity activity, int color, int alpha) {
        GradientDrawable d = rounded(activity, elevatedSurface(activity), 18);
        d.setStroke(dp(activity,1), withAlpha(color,alpha));
        layout.setBackground(d); layout.setElevation(dp(activity,1));
    }

    private static Button compactButton(Activity activity, String label) {
        Button b = new Button(activity);
        b.setText(label); b.setAllCaps(false); b.setTextSize(12); b.setMinHeight(dp(activity,38));
        b.setBackgroundTintList(ColorStateList.valueOf(elevatedSurface(activity)));
        b.setTextColor(textColor(activity));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, dp(activity,40));
        lp.setMargins(dp(activity,6),0,0,0); b.setLayoutParams(lp); return b;
    }

    private static void styleImage(Activity activity, ImageView image) {
        image.setPadding(dp(activity,4),dp(activity,4),dp(activity,4),dp(activity,4));
        GradientDrawable frame = rounded(activity, elevatedSurface(activity), 18);
        frame.setStroke(dp(activity,1),withAlpha(mutedColor(activity),60));
        image.setBackground(frame);
        image.setElevation(dp(activity,2));
    }

    private static GradientDrawable rounded(Context context,int color,int radiusDp){GradientDrawable d=new GradientDrawable();d.setShape(GradientDrawable.RECTANGLE);d.setColor(color);d.setCornerRadius(dp(context,radiusDp));return d;}
    private static boolean isDark(Context context){SharedPreferences p=context.getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);String m=p.getString("theme_mode","system");if("dark".equals(m))return true;if("light".equals(m))return false;return (context.getResources().getConfiguration().uiMode&android.content.res.Configuration.UI_MODE_NIGHT_MASK)==android.content.res.Configuration.UI_MODE_NIGHT_YES;}
    private static int accent(Context context){SharedPreferences p=context.getSharedPreferences(JanusApiClient.PREFS,Context.MODE_PRIVATE);switch(p.getString("accent","slate")){case"indigo":return Color.rgb(63,81,181);case"teal":return Color.rgb(0,121,107);case"amber":return Color.rgb(230,135,0);case"violet":return Color.rgb(123,31,162);default:return isDark(context)?Color.rgb(105,115,125):Color.rgb(58,68,78);}}
    private static int elevatedSurface(Context c){return isDark(c)?Color.rgb(46,46,48):Color.rgb(247,247,249);}
    private static int textColor(Context c){return isDark(c)?Color.rgb(244,244,244):Color.rgb(24,24,24);}
    private static int mutedColor(Context c){return isDark(c)?Color.rgb(180,180,184):Color.rgb(102,102,108);}
    private static int withAlpha(int color,int alpha){return Color.argb(Math.max(0,Math.min(255,alpha)),Color.red(color),Color.green(color),Color.blue(color));}
    private static int dp(Context c,int value){return Math.round(value*c.getResources().getDisplayMetrics().density);}
}
