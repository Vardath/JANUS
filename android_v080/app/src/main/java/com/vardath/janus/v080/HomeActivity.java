package com.vardath.janus.v080;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

/** Single coherent v0.80 launcher. Feature activities remain ordinary internal screens. */
public final class HomeActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", TOKEN="access_token", PROFILE="profile";

    @Override protected void onCreate(@Nullable Bundle state){
        ThemePrefs.applyGlobal(this);
        super.onCreate(state);
        build();
    }

    @Override protected void onResume(){super.onResume();build();}

    private android.content.SharedPreferences prefs(){return getSharedPreferences(PREFS,Context.MODE_PRIVATE);}

    private void build(){
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32,32,32,32);
        TextView title=label("JANUS · v0.80",30,true);root.addView(title);
        String profile=prefs().getString(PROFILE,"");
        boolean signedIn=!prefs().getString(TOKEN,"").isBlank();
        root.addView(label("11-core architecture · 7 specialists → 2 hemispheres → Consensus → Interface",15,false));
        root.addView(label(signedIn?("Signed in · "+(profile.isBlank()?"JANUS account":profile)):"Not signed in · use password/account sign-in or Google",14,false));

        if(!signedIn){
            root.addView(nav("Continue with Google",GoogleAuthActivity.class));
        }
        root.addView(nav("Chat · Account · Messages · Observe · System",MainActivity.class));
        root.addView(nav("Research workspace",ResearchActivity.class));
        root.addView(nav("Artifacts · Open · Share · Export",ArtifactActivity.class));
        root.addView(nav("Maintenance review",MaintenanceActivity.class));
        root.addView(nav("Themes · Background · Options",SettingsActivity.class));

        root.addView(label("Google identity is verified by the JANUS server through /auth/google; the resulting session is the same account-bound JANUS session used by password login.",13,false));
        root.addView(label("This is the clean native v0.80 client. The server-side JANUS cognition, continuity, memory, research and 7→2→1→1 routing remain the shared JANUS core.",14,false));
        root.addView(label("Maintenance is advisory and owner-gated. Device theme/background settings remain local and do not overwrite protected JANUS cognition state.",13,false));
        setContentView(root);
        ThemePrefs.applyAccent(root,this);
    }

    private Button nav(String text,Class<?> activity){
        Button b=new Button(this);b.setAllCaps(false);b.setText(text);b.setOnClickListener(v->startActivity(new Intent(this,activity)));return b;
    }
    private TextView label(String text,int sp,boolean bold){TextView t=new TextView(this);t.setText(text);t.setTextSize(sp);t.setPadding(8,12,8,12);if(bold)t.setTypeface(null,android.graphics.Typeface.BOLD);return t;}
}
