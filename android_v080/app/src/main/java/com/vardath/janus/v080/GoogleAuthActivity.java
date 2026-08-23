package com.vardath.janus.v080;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.tasks.Task;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Native Google identity flow for the clean v0.80 client.
 * Google proves identity; JANUS server remains authoritative for account creation,
 * linking and JANUS session issuance through POST /auth/google.
 */
public final class GoogleAuthActivity extends AppCompatActivity {
    private static final int RC_GOOGLE=8080;
    private static final String PREFS="janus_v080", TOKEN="access_token", PROFILE="profile";
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private TextView status;
    private GoogleSignInClient google;

    @Override protected void onCreate(@Nullable Bundle state){
        ThemePrefs.applyGlobal(this);
        super.onCreate(state);
        GoogleSignInOptions options=new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestIdToken(BuildConfig.GOOGLE_WEB_CLIENT_ID)
            .build();
        google=GoogleSignIn.getClient(this,options);
        build();
    }

    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}

    private void build(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(32,32,32,32);
        TextView h=new TextView(this);h.setText("Sign in to JANUS with Google");h.setTextSize(28);root.addView(h);
        TextView note=new TextView(this);note.setText("Google supplies an ID token. JANUS verifies it server-side and returns the same JANUS account/session used by password login. No Google password is handled by JANUS.");note.setTextSize(15);note.setPadding(0,16,0,20);root.addView(note);
        status=new TextView(this);status.setText("Ready");status.setPadding(0,8,0,16);root.addView(status);
        Button signIn=new Button(this);signIn.setAllCaps(false);signIn.setText("Continue with Google");signIn.setOnClickListener(v->startActivityForResult(google.getSignInIntent(),RC_GOOGLE));root.addView(signIn);
        Button reset=new Button(this);reset.setAllCaps(false);reset.setText("Choose a different Google account");reset.setOnClickListener(v->google.signOut().addOnCompleteListener(t->startActivityForResult(google.getSignInIntent(),RC_GOOGLE)));root.addView(reset);
        Button back=new Button(this);back.setAllCaps(false);back.setText("Back to JANUS");back.setOnClickListener(v->finish());root.addView(back);
        setContentView(root);ThemePrefs.applyAccent(root,this);
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,@Nullable Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode!=RC_GOOGLE)return;
        Task<GoogleSignInAccount> task=GoogleSignIn.getSignedInAccountFromIntent(data);
        try{
            GoogleSignInAccount account=task.getResult(ApiException.class);
            String idToken=account.getIdToken();
            if(idToken==null||idToken.isBlank()){status.setText("Google did not return an ID token. Check the configured web client ID.");return;}
            exchangeWithJanus(idToken);
        }catch(ApiException e){
            status.setText("Google sign-in failed · code "+e.getStatusCode());
        }
    }

    private void exchangeWithJanus(String idToken){
        status.setText("Google identity received · creating JANUS session…");
        io.execute(()->{
            HttpURLConnection c=null;
            try{
                JSONObject payload=new JSONObject();payload.put("id_token",idToken);
                c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+"/auth/google").openConnection();
                c.setRequestMethod("POST");c.setConnectTimeout(12000);c.setReadTimeout(45000);c.setDoOutput(true);
                c.setRequestProperty("Accept","application/json");c.setRequestProperty("Content-Type","application/json; charset=utf-8");c.setRequestProperty("Connection","close");
                try(OutputStream o=c.getOutputStream()){o.write(payload.toString().getBytes(StandardCharsets.UTF_8));}
                int code=c.getResponseCode();InputStream in=code>=200&&code<300?c.getInputStream():c.getErrorStream();String body=read(in);
                if(code>=200&&code<300){
                    JSONObject j=new JSONObject(body);String token=j.optString("access_token","");JSONObject acct=j.optJSONObject("account");String profile=acct==null?"":acct.optString("username","");
                    if(token.isBlank())throw new IllegalStateException("JANUS did not return a session token");
                    getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(TOKEN,token).putString(PROFILE,profile).apply();
                    runOnUiThread(()->{status.setText("Google sign-in complete · JANUS session active");startActivity(new Intent(this,HomeActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP));finish();});
                }else{
                    runOnUiThread(()->status.setText("JANUS Google sign-in failed · HTTP "+code+" · "+body));
                }
            }catch(Exception e){runOnUiThread(()->status.setText("Google sign-in bridge failed · "+e.getClass().getSimpleName()+": "+e.getMessage()));}
            finally{if(c!=null)c.disconnect();}
        });
    }

    private static String read(@Nullable InputStream in)throws Exception{
        if(in==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line).append('\n');}return b.toString().trim();
    }
}
