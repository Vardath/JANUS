package com.vardath.janus.v080;

import android.content.Context;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

public final class SettingsActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", BG="background_enabled", OBS="observe_enabled", INTERVAL="background_interval";
    private LinearLayout root;
    @Override protected void onCreate(@Nullable Bundle state){super.onCreate(state);build();}
    private android.content.SharedPreferences prefs(){return getSharedPreferences(PREFS,Context.MODE_PRIVATE);}
    private void build(){root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(32,32,32,32);root.addView(label("JANUS Options · Themes & Background",28));root.addView(label("Theme mode: "+ThemePrefs.mode(this),16));for(String m:new String[]{"system","light","dark"}){Button b=button("Theme · "+m);b.setOnClickListener(v->{ThemePrefs.saveMode(this,m);recreate();});root.addView(b);}root.addView(label("Accent: "+ThemePrefs.accent(this),16));for(String a:new String[]{"indigo","teal","amber","violet","slate"}){Button b=button("Accent · "+a);b.setOnClickListener(v->{ThemePrefs.saveAccent(this,a);ThemePrefs.applyAccent(root,this);});root.addView(b);}boolean bg=prefs().getBoolean(BG,true),obs=prefs().getBoolean(OBS,true);Button bgBtn=button("Background cycles: "+(bg?"on":"off"));bgBtn.setOnClickListener(v->{boolean n=!prefs().getBoolean(BG,true);prefs().edit().putBoolean(BG,n).apply();bgBtn.setText("Background cycles: "+(n?"on":"off"));});root.addView(bgBtn);Button obBtn=button("Observe telemetry: "+(obs?"on":"off"));obBtn.setOnClickListener(v->{boolean n=!prefs().getBoolean(OBS,true);prefs().edit().putBoolean(OBS,n).apply();obBtn.setText("Observe telemetry: "+(n?"on":"off"));});root.addView(obBtn);root.addView(label("Local background cadence affects this device's client work only. It does not overwrite JANUS server cognition or protected identity state.",14));for(int minutes:new int[]{5,15,30,60}){Button b=button("Local background interval · "+minutes+" min");b.setOnClickListener(v->prefs().edit().putInt(INTERVAL,minutes).apply());root.addView(b);}setContentView(root);ThemePrefs.applyAccent(root,this);}
    private TextView label(String s,int sp){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setPadding(8,12,8,12);return t;}private Button button(String s){Button b=new Button(this);b.setText(s);b.setAllCaps(false);return b;}
}
