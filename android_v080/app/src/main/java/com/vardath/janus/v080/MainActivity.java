package com.vardath.janus.v080;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends AppCompatActivity {
    private static final int PICK_FILE = 4080;
    private static final int MAX_FILE_BYTES = 8 * 1024 * 1024;
    private static final String PREFS = "janus_v080", TOKEN = "access_token", PROFILE = "profile";
    private final ExecutorService io = Executors.newCachedThreadPool();
    private WebView web;

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    @Override protected void onCreate(@Nullable Bundle state) {
        ThemePrefs.applyGlobal(this); super.onCreate(state);
        web = new WebView(this); setContentView(web);
        WebSettings s = web.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                String token = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(TOKEN, "");
                String profile = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(PROFILE, "");
                String js = "window.googleComingSoon=function(){Android.googleSignIn();};window.__janusV080=true;window.__janusProductVersion='0.80-dev2';";
                if (token != null && !token.isBlank() && profile != null && !profile.isBlank()) js += "localStorage.janusToken="+quote(token)+";localStorage.janusProfile="+quote(profile)+";if(window.login)login.classList.add('hidden');if(window.profileLabel)profileLabel.textContent='Signed in as '+"+quote(profile)+";if(window.show)show('chat');if(window.refresh){refresh('options');refresh('messages');}";
                view.evaluateJavascript(js, null);
            }
        });
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override protected void onDestroy(){io.shutdownNow();if(web!=null)web.destroy();super.onDestroy();}
    @Override protected void onActivityResult(int requestCode,int resultCode,@Nullable Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode!=PICK_FILE)return;if(resultCode!=RESULT_OK||data==null||data.getData()==null){eval("if(window.__janusFilePickError)window.__janusFilePickError('File selection was cancelled.')");return;}deliverFile(data.getData());}
    private void eval(String js){runOnUiThread(()->{if(web!=null)web.evaluateJavascript(js,null);});}
    private void startFilePicker(){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");startActivityForResult(i,PICK_FILE);}

    private void deliverFile(Uri uri){io.execute(()->{try{byte[] bytes=readBytes(uri,MAX_FILE_BYTES);String name=displayName(uri),mime=getContentResolver().getType(uri);if(mime==null||mime.isBlank())mime="application/octet-stream";JSONObject j=new JSONObject();j.put("filename",name);j.put("mime_type",mime);j.put("data_base64",Base64.encodeToString(bytes,Base64.NO_WRAP));eval("if(window.__janusFilePicked)window.__janusFilePicked(JSON.parse("+quote(j.toString())+"))");}catch(Exception e){eval("if(window.__janusFilePickError)window.__janusFilePickError("+quote(e.getMessage())+")");}});}
    private byte[] readBytes(Uri uri,int max)throws Exception{try(InputStream in=getContentResolver().openInputStream(uri);ByteArrayOutputStream out=new ByteArrayOutputStream()){if(in==null)throw new IllegalArgumentException("The selected file could not be opened.");byte[] buf=new byte[32768];int n,total=0;while((n=in.read(buf))!=-1){total+=n;if(total>max)throw new IllegalArgumentException("JANUS currently accepts files up to 8 MB.");out.write(buf,0,n);}if(total==0)throw new IllegalArgumentException("Empty files are not supported.");return out.toByteArray();}}
    private String displayName(Uri uri){String name="attachment";try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst()&&c.getString(0)!=null&&!c.getString(0).isBlank())name=c.getString(0);}catch(Exception ignored){}return name;}
    private String extractToken(String json){try{return new JSONObject(json==null?"{}":json).optString("_janus_token","");}catch(Exception ignored){return"";}}
    private void rememberSession(String body){try{JSONObject j=new JSONObject(body);String token=j.optString("access_token",j.optString("token",""));String profile=j.optString("username",j.optString("profile_id",""));JSONObject account=j.optJSONObject("account");if(profile.isBlank()&&account!=null)profile=account.optString("username","");if(!token.isBlank()&&!profile.isBlank())getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(TOKEN,token).putString(PROFILE,profile).apply();}catch(Exception ignored){}}

    public final class Bridge {
        @JavascriptInterface public void googleSignIn(){runOnUiThread(()->startActivity(new Intent(MainActivity.this,GoogleAuthActivity.class)));}
        @JavascriptInterface public void pickFile(){runOnUiThread(MainActivity.this::startFilePicker);}
        @JavascriptInterface public void clearSession(){getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().clear().apply();}
        @JavascriptInterface public String localCoreStatus(){return "{\"architecture\":\"11-core\",\"topology\":\"7 → 2 → 1 → 1\",\"phase\":\"server-backed\",\"sync_state\":\"connected-client\",\"cores\":{}}";}
        @JavascriptInterface public String serverCoreStatus(){return "";}
        @JavascriptInterface public String serverUrl(){return BuildConfig.SERVER_BASE_URL;}
        @JavascriptInterface public void exportArtifact(String fileId,String filename,String mime){runOnUiThread(()->startActivity(new Intent(MainActivity.this,ArtifactActivity.class)));}
        @JavascriptInterface public void shareArtifact(String fileId,String filename,String mime){runOnUiThread(()->startActivity(new Intent(MainActivity.this,ArtifactActivity.class)));}
        @JavascriptInterface public void request(String id,String method,String path,String json){io.execute(()->{HttpURLConnection c=null;try{String body=json==null?"{}":json;String token=extractToken(body);if(token.isBlank())token=getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(TOKEN,"");c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(15000);c.setReadTimeout("/desktop/chat".equals(path)?120000:45000);c.setRequestProperty("Accept","application/json");c.setRequestProperty("Connection","close");if(token!=null&&!token.isBlank())c.setRequestProperty("Authorization","Bearer "+token);if(!"GET".equalsIgnoreCase(method)){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");try(OutputStream o=c.getOutputStream()){o.write(body.getBytes(StandardCharsets.UTF_8));}}int code=c.getResponseCode();String response=read(code>=200&&code<400?c.getInputStream():c.getErrorStream());if(code>=200&&code<300&&("/auth/login".equals(path)||"/auth/register".equals(path)))rememberSession(response);String result="{\"ok\":"+(code>=200&&code<300)+",\"status\":"+code+",\"body\":"+quote(response)+"}";eval("window.__janusResult("+quote(id)+","+result+")");}catch(Exception e){String result="{\"ok\":false,\"status\":0,\"body\":"+quote("{\"detail\":\""+safe(e.getMessage())+"\"}")+"}";eval("window.__janusResult("+quote(id)+","+result+")");}finally{if(c!=null)c.disconnect();}});}
    }

    private static String read(@Nullable InputStream in)throws Exception{if(in==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){String line;while((line=r.readLine())!=null)b.append(line).append('\n');}return b.toString().trim();}
    private static String safe(String s){return s==null?"Network request failed":s.replace("\"","'").replace("\n"," ");}
    private static String quote(String s){if(s==null)s="";return"\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";}
}
