package com.vardath.janus.v080;

import android.content.Context;
import android.os.Bundle;
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
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MaintenanceActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", TOKEN="access_token";
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private TextView body,status; private int latestReviewId=-1;
    @Override protected void onCreate(@Nullable Bundle state){super.onCreate(state);build();load();}
    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}
    private String token(){return getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(TOKEN,"");}
    private void build(){LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(32,32,32,32);TextView h=new TextView(this);h.setText("JANUS Maintenance Review");h.setTextSize(28);root.addView(h);status=new TextView(this);status.setText("Loading owner maintenance state…");root.addView(status);body=new TextView(this);body.setTextSize(14);ScrollView scroll=new ScrollView(this);scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));for(String d:new String[]{"approved_for_manual_work","deferred","rejected"}){Button b=new Button(this);b.setAllCaps(false);b.setText(d.equals("approved_for_manual_work")?"Approve for manual work":"deferred".equals(d)?"Defer":"Reject");b.setOnClickListener(v->decide(d));root.addView(b);}TextView note=new TextView(this);note.setText("Decisions only record owner disposition. JANUS does not edit code, change models, install dependencies, alter configuration, or deploy automatically.");root.addView(note);setContentView(root);}
    private void load(){if(token().isBlank()){status.setText("Sign in through JANUS first.");return;}io.execute(()->{Result r=request("GET","/maintenance/status",null);String text;if(r.ok()){try{JSONObject j=new JSONObject(r.body);JSONArray reviews=j.optJSONArray("reviews");StringBuilder b=new StringBuilder("Owner approval required: ").append(j.optBoolean("owner_approval_required",true)).append("\nAutomatic changes: ").append(j.optBoolean("automatic_changes",false)).append("\n\n");if(reviews!=null&&reviews.length()>0){JSONObject x=reviews.getJSONObject(0);latestReviewId=x.optInt("id",-1);b.append("Latest review #").append(latestReviewId).append("\nState: ").append(x.optString("review_state","unknown")).append("\nCreated: ").append(x.optString("created_at","unknown")).append("\n\n");JSONObject rep=x.optJSONObject("report");if(rep!=null){b.append("Proposal: ").append(rep.optString("proposal_kind","maintenance review")).append("\nDeployed commit: ").append(rep.optString("deployed_commit","unknown")).append("\nPython: ").append(rep.optString("python","unknown")).append("\nPhase: ").append(rep.optString("phase","unknown")).append("\n\nRequested review sections:\n");JSONArray sections=rep.optJSONArray("review_sections");if(sections!=null)for(int i=0;i<sections.length();i++){JSONObject s=sections.getJSONObject(i);b.append("• ").append(s.optString("area")).append(": ").append(s.optString("request")).append("\n");}}}else b.append("No maintenance proposal is currently recorded.");text=b.toString();}catch(Exception e){text=r.body;}}else text="Maintenance unavailable · HTTP "+r.code+" · "+r.body;String f=text;runOnUiThread(()->{body.setText(f);status.setText(r.ok()?"Maintenance state loaded":"Maintenance state unavailable");});});}
    private void decide(String decision){if(latestReviewId<0){status.setText("No review selected.");return;}status.setText("Recording decision…");io.execute(()->{String payload="{\"decision\":\""+decision+"\"}";Result r=request("POST","/maintenance/reviews/"+latestReviewId+"/decision",payload);runOnUiThread(()->{status.setText(r.ok()?"Decision recorded · no automatic changes performed":"Decision failed · HTTP "+r.code);if(r.ok())load();});});}
    private Result request(String method,String path,@Nullable String payload){HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(12000);c.setReadTimeout(45000);c.setRequestProperty("Accept","application/json");c.setRequestProperty("Authorization","Bearer "+token());if(payload!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream o=c.getOutputStream()){o.write(payload.getBytes(StandardCharsets.UTF_8));}}int code=c.getResponseCode();InputStream in=code>=200&&code<400?c.getInputStream():c.getErrorStream();return new Result(code,read(in));}catch(Exception e){return new Result(0,e.getClass().getSimpleName()+": "+e.getMessage());}finally{if(c!=null)c.disconnect();}}
    private static String read(@Nullable InputStream in)throws Exception{if(in==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line).append('\n');}return b.toString().trim();}
    private record Result(int code,String body){boolean ok(){return code>=200&&code<300;}}
}
