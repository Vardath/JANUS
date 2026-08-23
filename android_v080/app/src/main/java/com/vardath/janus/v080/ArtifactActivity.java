package com.vardath.janus.v080;

import android.content.Context;
import android.content.Intent;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ArtifactActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", TOKEN="access_token";
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private LinearLayout list;
    private TextView status;
    private String token="";

    @Override protected void onCreate(@Nullable Bundle state){super.onCreate(state);token=getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(TOKEN,"");buildUi();loadArtifacts();}
    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}

    private void buildUi(){LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(16),dp(18),dp(16),dp(14));TextView title=text("JANUS Artifacts",30,true);root.addView(title,mw());status=text("Loading generated artifacts…",14,false);root.addView(status,mw());
        LinearLayout create=new LinearLayout(this);create.setOrientation(LinearLayout.VERTICAL);EditText note=new EditText(this);note.setHint("Optional working note text");Button continuity=button("Create continuity report"),research=button("Create research digest"),working=button("Create working note");create.addView(note,mw());create.addView(continuity,mw());create.addView(research,mw());create.addView(working,mw());root.addView(create,mw());
        ScrollView scroll=new ScrollView(this);list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);scroll.addView(list,mw());root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));Button refresh=button("Refresh artifacts");root.addView(refresh,mw());setContentView(root);
        refresh.setOnClickListener(v->loadArtifacts());continuity.setOnClickListener(v->createArtifact("continuity_report","JANUS Continuity Report",""));research.setOnClickListener(v->createArtifact("research_digest","JANUS Research Digest",""));working.setOnClickListener(v->{String n=note.getText().toString().trim();if(n.isEmpty()){toast("Enter note text first.");return;}createArtifact("working_note","JANUS Working Note",n);note.setText("");});}

    private void createArtifact(String kind,String title,String note){status.setText("Creating "+title+"…");io.execute(()->{try{JSONObject b=new JSONObject();b.put("kind",kind);b.put("title",title);if(!note.isBlank())b.put("note",note);HttpResult r=request("POST","/artifacts",b.toString());runOnUiThread(()->{status.setText(r.ok()?"Artifact created":"Artifact creation failed · "+friendly(r));if(r.ok())loadArtifacts();});}catch(Exception e){runOnUiThread(()->status.setText("Artifact creation failed · "+e.getClass().getSimpleName()));}});}

    private void loadArtifacts(){status.setText("Loading generated artifacts…");io.execute(()->{HttpResult r=request("GET","/artifacts",null);runOnUiThread(()->{list.removeAllViews();if(!r.ok()){status.setText("Artifacts unavailable · "+friendly(r));return;}try{JSONArray items=new JSONObject(r.body).optJSONArray("items");if(items==null||items.length()==0){list.addView(text("No generated artifacts yet.",16,false),mw());status.setText("No artifacts");return;}for(int i=0;i<items.length();i++){JSONObject a=items.getJSONObject(i);addArtifactRow(a);}status.setText(items.length()+" artifact"+(items.length()==1?"":"s"));}catch(Exception e){status.setText("Artifact response unreadable");}});});}

    private void addArtifactRow(JSONObject a){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.VERTICAL);String title=a.optString("title","JANUS artifact"),kind=a.optString("kind","artifact"),path=a.optString("download_path",""),filename=a.optString("original_name",title+".md"),mime=a.optString("mime_type","text/markdown");row.addView(text(title+"\n"+kind,16,true),mw());LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);Button open=button("Open"),share=button("Share"),export=button("Export");actions.addView(open,new LinearLayout.LayoutParams(0,-2,1));actions.addView(share,new LinearLayout.LayoutParams(0,-2,1));actions.addView(export,new LinearLayout.LayoutParams(0,-2,1));row.addView(actions,mw());list.addView(row,mw());open.setOnClickListener(v->downloadAndUse(path,filename,mime,"open"));share.setOnClickListener(v->downloadAndUse(path,filename,mime,"share"));export.setOnClickListener(v->downloadAndUse(path,filename,mime,"export"));}

    private void downloadAndUse(String path,String filename,String mime,String mode){if(path==null||path.isBlank()){toast("Artifact file is unavailable.");return;}status.setText("Preparing "+filename+"…");io.execute(()->{BytesResult r=download(path);if(!r.ok()){runOnUiThread(()->status.setText("Artifact download failed · "+r.error));return;}try{File dir=new File(getCacheDir(),"exports");if(!dir.exists())dir.mkdirs();String safe=filename.replaceAll("[^A-Za-z0-9._-]","-");File out=new File(dir,safe);try(FileOutputStream f=new FileOutputStream(out)){f.write(r.bytes);}Uri uri=FileProvider.getUriForFile(this,BuildConfig.APPLICATION_ID+".files",out);runOnUiThread(()->launchFile(uri,safe,mime,mode));}catch(Exception e){runOnUiThread(()->status.setText("Unable to prepare artifact · "+e.getClass().getSimpleName()));}});}

    private void launchFile(Uri uri,String filename,String mime,String mode){status.setText("Artifact ready · "+filename);Intent i;if("share".equals(mode)){i=new Intent(Intent.ACTION_SEND);i.setType(mime);i.putExtra(Intent.EXTRA_STREAM,uri);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,"Share JANUS artifact"));return;}if("export".equals(mode)){i=new Intent(Intent.ACTION_SEND);i.setType(mime);i.putExtra(Intent.EXTRA_STREAM,uri);i.putExtra(Intent.EXTRA_TITLE,filename);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,"Export JANUS artifact"));return;}i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,mime);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);try{startActivity(i);}catch(Exception e){toast("No app is available to open this artifact. Use Share or Export.");}}

    private HttpResult request(String method,String path,@Nullable String body){HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(12000);c.setReadTimeout(60000);c.setRequestProperty("Accept","application/json");c.setRequestProperty("Connection","close");if(!token.isBlank())c.setRequestProperty("Authorization","Bearer "+token);if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");try(OutputStream o=c.getOutputStream()){o.write(body.getBytes(StandardCharsets.UTF_8));}}int code=c.getResponseCode();InputStream s=code>=200&&code<400?c.getInputStream():c.getErrorStream();return new HttpResult(code,readText(s),null);}catch(Exception e){return new HttpResult(0,"",e.getClass().getSimpleName()+": "+e.getMessage());}finally{if(c!=null)c.disconnect();}}
    private BytesResult download(String path){HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod("GET");c.setConnectTimeout(12000);c.setReadTimeout(60000);c.setRequestProperty("Connection","close");c.setRequestProperty("Authorization","Bearer "+token);int code=c.getResponseCode();if(code<200||code>=300)return new BytesResult(null,"HTTP "+code);try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] buf=new byte[32768];int n;while((n=in.read(buf))!=-1)out.write(buf,0,n);return new BytesResult(out.toByteArray(),null);}}catch(Exception e){return new BytesResult(null,e.getClass().getSimpleName()+": "+e.getMessage());}finally{if(c!=null)c.disconnect();}}
    private static String readText(@Nullable InputStream s)throws Exception{if(s==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(s,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line).append('\n');}return b.toString().trim();}
    private String friendly(HttpResult r){if(r.error!=null)return r.error;if(r.code==401)return"Authentication required.";if(r.code>0)return"HTTP "+r.code;return"Network request failed.";}
    private TextView text(String v,int sp,boolean bold){TextView t=new TextView(this);t.setText(v);t.setTextSize(sp);t.setPadding(dp(4),dp(8),dp(4),dp(8));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}private Button button(String l){Button b=new Button(this);b.setText(l);b.setAllCaps(false);return b;}private void toast(String m){Toast.makeText(this,m,Toast.LENGTH_SHORT).show();}private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}private LinearLayout.LayoutParams mw(){return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);}
    private record HttpResult(int code,String body,String error){boolean ok(){return code>=200&&code<300;}}private record BytesResult(byte[] bytes,String error){boolean ok(){return bytes!=null&&error==null;}}
}
