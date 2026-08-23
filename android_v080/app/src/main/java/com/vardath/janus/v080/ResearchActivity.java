package com.vardath.janus.v080;

import android.content.Context;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ResearchActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", TOKEN="access_token";
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private TextView status, body;
    private String token="";

    @Override protected void onCreate(@Nullable Bundle state){super.onCreate(state);token=getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(TOKEN,"");build();refresh();}
    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}

    private void build(){LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(16),dp(18),dp(16),dp(16));root.addView(text("JANUS Research Workspace",28,true),mw());root.addView(text("Evidence is kept visibly separated into established results, provisional hypotheses, negative results, open questions and proposed tests. Retrieval provenance is shown independently from JANUS private reasoning.",14,false),mw());status=text("Loading provenance…",13,false);root.addView(status,mw());Button refresh=new Button(this);refresh.setText("Refresh research + provenance");refresh.setAllCaps(false);refresh.setOnClickListener(v->refresh());root.addView(refresh,mw());Button digest=new Button(this);digest.setText("Create research digest artifact");digest.setAllCaps(false);digest.setOnClickListener(v->createDigest());root.addView(digest,mw());body=text("",14,false);ScrollView scroll=new ScrollView(this);scroll.addView(body,mw());root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);}

    private void refresh(){if(token.isBlank()){status.setText("Sign in through JANUS first.");body.setText("No authenticated research workspace is available until a JANUS session exists.");return;}status.setText("Refreshing…");io.execute(()->{HttpResult r=get("/research-provenance/status?limit=20");String out=r.ok()?format(r.body):"Research provenance unavailable · "+friendly(r);runOnUiThread(()->{status.setText(r.ok()?"Research provenance loaded":"Reduced capability");body.setText(out);});});}

    private String format(String raw){StringBuilder b=new StringBuilder();try{JSONObject j=new JSONObject(raw);JSONArray searches=j.optJSONArray("recent_searches");b.append("ESTABLISHED / RETRIEVED EVIDENCE\n");b.append("Material below is limited to completed or recorded external research. It does not turn hypotheses into facts.\n\n");if(searches==null||searches.length()==0)b.append("No recent research records.\n");else for(int i=0;i<searches.length();i++){JSONObject s=searches.getJSONObject(i);b.append("Research #").append(s.optInt("id")).append(" · ").append(s.optString("status","unknown")).append("\n").append(s.optString("query","Untitled query")).append("\nMode: ").append(s.optString("mode","unknown")).append(" · Core: ").append(s.optString("core_name","unknown")).append("\nSources: ").append(s.optInt("source_count",0)).append("\n").append(s.optString("result_preview","")).append("\n");JSONArray src=s.optJSONArray("sources");if(src!=null)for(int k=0;k<src.length()&&k<6;k++){Object x=src.get(k);if(x instanceof JSONObject){JSONObject so=(JSONObject)x;b.append("  • ").append(so.optString("title","Source")).append(" — ").append(so.optString("url","")).append("\n");}else b.append("  • ").append(String.valueOf(x)).append("\n");}b.append("\n");}
            b.append("PROVISIONAL HYPOTHESES\nKeep interpretation, model-building and unverified connections here until independently supported.\n\nNEGATIVE RESULTS\nFailed tests and ruled-out realizations remain valuable evidence and should stay visible rather than being silently discarded.\n\nOPEN QUESTIONS\nUnresolved claims remain open until a test or source closes them.\n\nPROPOSED TESTS\nRecord what observation, calculation or retrieval would discriminate between competing possibilities.\n\n");
            JSONObject usefulness=j.optJSONObject("usefulness");JSONObject compute=j.optJSONObject("external_compute");b.append("BACKGROUND RESEARCH / PROVENANCE\n");if(usefulness!=null)b.append("Usefulness audit: ").append(usefulness.toString()).append("\n");if(compute!=null)b.append("External compute: ").append(compute.toString()).append("\n");b.append(j.optString("provenance_notice","Sources and costs describe externalized research activity only."));
        }catch(Exception e){return raw;}return b.toString();}

    private void createDigest(){if(token.isBlank()){status.setText("Sign in through JANUS first.");return;}status.setText("Creating research digest…");io.execute(()->{HttpResult r=post("/artifacts","{\"kind\":\"research_digest\",\"title\":\"JANUS Research Digest\",\"research_limit\":12}");runOnUiThread(()->status.setText(r.ok()?"Research digest created · open JANUS Artifacts to export/share it":"Digest failed · "+friendly(r)));});}

    private HttpResult get(String path){return request("GET",path,null);} private HttpResult post(String path,String body){return request("POST",path,body);}
    private HttpResult request(String method,String path,@Nullable String body){HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(12000);c.setReadTimeout(60000);c.setRequestProperty("Accept","application/json");c.setRequestProperty("Connection","close");c.setRequestProperty("Authorization","Bearer "+token);if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");c.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));}int code=c.getResponseCode();InputStream s=code>=200&&code<400?c.getInputStream():c.getErrorStream();return new HttpResult(code,read(s),null);}catch(Exception e){return new HttpResult(0,"",e.getClass().getSimpleName()+": "+e.getMessage());}finally{if(c!=null)c.disconnect();}}
    private static String read(@Nullable InputStream s)throws Exception{if(s==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(s,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line).append('\n');}return b.toString().trim();}
    private String friendly(HttpResult r){if(r.error!=null&&!r.error.isBlank())return r.error;if(r.code==401)return"Authentication required.";if(r.code==502||r.code==503||r.code==504)return"JANUS temporarily unavailable (HTTP "+r.code+").";if(r.code>0)return"HTTP "+r.code;return"Network request failed.";}
    private TextView text(String v,int sp,boolean bold){TextView t=new TextView(this);t.setText(v);t.setTextSize(sp);t.setPadding(dp(4),dp(8),dp(4),dp(8));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}private LinearLayout.LayoutParams mw(){return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);}private record HttpResult(int code,String body,String error){boolean ok(){return code>=200&&code<300;}}
}
