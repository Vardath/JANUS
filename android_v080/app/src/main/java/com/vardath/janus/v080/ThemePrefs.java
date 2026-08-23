package com.vardath.janus.v080;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import androidx.appcompat.app.AppCompatDelegate;

final class ThemePrefs {
    private static final String PREFS="janus_v080", MODE="theme_mode", ACCENT="theme_accent";
    private ThemePrefs(){}

    static void applyGlobal(Context context){
        String mode=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(MODE,"system");
        int night=AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM;
        if("light".equals(mode)) night=AppCompatDelegate.MODE_NIGHT_NO;
        else if("dark".equals(mode)) night=AppCompatDelegate.MODE_NIGHT_YES;
        AppCompatDelegate.setDefaultNightMode(night);
    }

    static void saveMode(Context context,String mode){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(MODE,mode).apply();applyGlobal(context);}
    static String mode(Context context){return context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(MODE,"system");}
    static void saveAccent(Context context,String accent){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(ACCENT,accent).apply();}
    static String accent(Context context){return context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(ACCENT,"indigo");}
    static int accentColor(Context context){
        return switch(accent(context)){
            case "teal" -> Color.rgb(0,121,107);
            case "amber" -> Color.rgb(245,124,0);
            case "violet" -> Color.rgb(106,27,154);
            case "slate" -> Color.rgb(69,90,100);
            default -> Color.rgb(63,81,181);
        };
    }
    static void applyAccent(View view,Context context){
        if(view instanceof Button) ((Button)view).setBackgroundTintList(ColorStateList.valueOf(accentColor(context)));
        if(view instanceof ViewGroup){ViewGroup g=(ViewGroup)view;for(int i=0;i<g.getChildCount();i++)applyAccent(g.getChildAt(i),context);}
    }
}
