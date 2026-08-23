package com.vardath.janus.v080;

import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URLEncoder;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Clean native reconstruction of the JANUS app the user already designed.
 * Product surface: Chat / Messages / Observe / Options.
 * Core architecture remains server-side 7→2→1→1; this client does not simulate a replacement JANUS.
 */
public final class MainActivity extends AppCompatActivity {
    private static final String PREFS="janus_v080", TOKEN="access_token", PROFILE="profile", QUEUE="chat_queue";
    private static final int PICK_FILE=4080, MAX_ATTACHMENTS=4, MAX_FILE_BYTES=8*1024*1024;
    private static final long[] RETRY={8000L,25000L,60000L};
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final Set<String> inFlight=new HashSet<>();
    private final List<Attachment> draftAttachments=new ArrayList<>();
    private LinearLayout root, page, bottomNav, chatList, attachmentRow;
    private TextView status, attachmentStatus;
    private ScrollView chatScroll;
    private String accessToken="", profile="", activeTab="Chat";

    @Override protected void onCreate(@Nullable Bundle state){
        ThemePrefs.applyGlobal(this);
        super.onCreate(state);
        accessToken=prefs().getString(TOKEN,""); profile=prefs().getString(PROFILE,"");
        if(accessToken.isBlank())showAuth(); else validateSession();
    }
    @Override protected void onResume(){super.onResume(); if(!accessToken.isBlank()&&root!=null)ThemePrefs.applyAccent(root,this);}
    @Override protected void onDestroy(){io.shutdownNow();super.onDestroy();}
    @Override protected void onActivityResult(int requestCode,int resultCode,@Nullable Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode==PICK_FILE&&resultCode==RESULT_OK&&data!=null&&data.getData()!=null)uploadPickedFile(data.getData());}
    private android.content.SharedPreferences prefs(){return getSharedPreferences(PREFS,Context.MODE_PRIVATE);}

    // ---------- AUTH: same simple JANUS sign-in surface ----------
    private void showAuth(){
        accessToken=""; profile="";
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(24),dp(28),dp(24),dp(24));root.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(label("JANUS",36,true),mw());
        root.addView(label("Sign in to continue your JANUS identity and memory.",16,false),mw());
        LinearLayout tabs=new LinearLayout(this);tabs.setOrientation(LinearLayout.HORIZONTAL);Button signTab=button("Sign in"),regTab=button("Create account");tabs.addView(signTab,new LinearLayout.LayoutParams(0,-2,1));tabs.addView(regTab,new LinearLayout.LayoutParams(0,-2,1));root.addView(tabs,mw());
        LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);root.addView(form,mw());
        TextView authMsg=label("",13,false);root.addView(authMsg,mw());
        Button google=button("Continue with Google");google.setOnClickListener(v->startActivity(new Intent(this,GoogleAuthActivity.class)));root.addView(google,mw());
        root.addView(label("Your account owns JANUS continuity across devices. Google and password sign-in lead to the same JANUS account/session.",12,false),mw());
        signTab.setOnClickListener(v->renderSignIn(form,authMsg));regTab.setOnClickListener(v->renderRegister(form,authMsg));
        renderSignIn(form,authMsg);setContentView(root);ThemePrefs.applyAccent(root,this);checkHealth(authMsg);
    }
    private void renderSignIn(LinearLayout form,TextView msg){form.removeAllViews();EditText id=input("Username or email"),pw=input("Password");pw.setInputType(0x81);Button go=button("Sign in");form.addView(id,mw());form.addView(pw,mw());form.addView(go,mw());go.setOnClickListener(v->{if(id.getText().toString().trim().isEmpty()||pw.getText().toString().isEmpty()){msg.setText("Enter username/email and password.");return;}JSONObject b=new JSONObject();try{b.put("identifier",id.getText().toString().trim());b.put("password",pw.getText().toString());}catch(Exception ignored){}authenticate("/auth/login",b,msg);});}
    private void renderRegister(LinearLayout form,TextView msg){form.removeAllViews();EditText u=input("Username"),e=input("Email"),pw=input("Password (8+ characters)");pw.setInputType(0x81);Button go=button("Create account");form.addView(u,mw());form.addView(e,mw());form.addView(pw,mw());form.addView(go,mw());go.setOnClickListener(v->{if(u.getText().toString().trim().isEmpty()||e.getText().toString().trim().isEmpty()||pw.getText().toString().isEmpty()){msg.setText("Enter username, email and password.");return;}JSONObject b=new JSONObject();try{b.put("username",u.getText().toString().trim());b.put("email",e.getText().toString().trim());b.put("password",pw.getText().toString());}catch(Exception ignored){}authenticate("/auth/register",b,msg);});}
    private void authenticate(String path,JSONObject body,TextView msg){msg.setText("Connecting to JANUS…");io.execute(()->{HttpResult r=request("POST",path,body.toString(),false);if(r.ok()){try{JSONObject j=new JSONObject(r.body);String t=j.optString("access_token","");JSONObject a=j.optJSONObject("account");String p=a==null?"":a.optString("username","");if(!t.isBlank()){saveSession(t,p);ui.post(this::showApp);return;}}catch(Exception ignored){}}ui.post(()->msg.setText("Sign-in failed · "+friendly(r)));});}
    private void validateSession(){io.execute(()->{HttpResult r=request("GET","/auth/me",null,true);ui.post(()->{if(r.ok()){try{JSONObject a=new JSONObject(r.body).optJSONObject("account");if(a!=null){profile=a.optString("username",profile);prefs().edit().putString(PROFILE,profile).apply();}}catch(Exception ignored){}showApp();}else{clearSession();showAuth();}});});}
    private void saveSession(String token,String name){accessToken=token;profile=name;prefs().edit().putString(TOKEN,token).putString(PROFILE,name).apply();}
    private void clearSession(){accessToken="";profile="";draftAttachments.clear();prefs().edit().remove(TOKEN).remove(PROFILE).apply();}

    // ---------- ORIGINAL JANUS SHELL ----------
    private void showApp(){
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(0,0,0,0);
        LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);top.setGravity(Gravity.CENTER_VERTICAL);top.setPadding(dp(14),dp(10),dp(14),dp(8));
        top.addView(label("JANUS · 11 cores · 7→2→1→1",16,true),new LinearLayout.LayoutParams(0,-2,1));status=label("Interface active",12,false);top.addView(status,ww());root.addView(top,mw());
        page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);page.setPadding(dp(12),dp(8),dp(12),dp(8));root.addView(page,new LinearLayout.LayoutParams(-1,0,1));
        bottomNav=new LinearLayout(this);bottomNav.setOrientation(LinearLayout.HORIZONTAL);bottomNav.setPadding(dp(8),dp(4),dp(8),dp(10));root.addView(bottomNav,mw());
        for(String n:new String[]{"Chat","Messages","Observe","Options"}){Button b=button(n);b.setTag(n);b.setOnClickListener(v->showTab((String)v.getTag()));bottomNav.addView(b,new LinearLayout.LayoutParams(0,dp(60),1));}
        setContentView(root);ThemePrefs.applyAccent(root,this);showTab("Chat");checkCapabilities();flushSoon(500);
    }
    private void showTab(String tab){activeTab=tab;page.removeAllViews();for(int i=0;i<bottomNav.getChildCount();i++){Button b=(Button)bottomNav.getChildAt(i);b.setTypeface(null,tab.equals(b.getTag())?Typeface.BOLD:Typeface.NORMAL);}if(tab.equals("Messages"))showMessages();else if(tab.equals("Observe"))showObserve();else if(tab.equals("Options"))showOptions();else showChat();}

    // ---------- CHAT ----------
    private void showChat(){page.addView(label("Chat",30,true),mw());chatList=new LinearLayout(this);chatList.setOrientation(LinearLayout.VERTICAL);chatScroll=new ScrollView(this);chatScroll.addView(chatList,mw());page.addView(chatScroll,new LinearLayout.LayoutParams(-1,0,1));renderQueued();
        attachmentRow=new LinearLayout(this);attachmentRow.setOrientation(LinearLayout.HORIZONTAL);HorizontalScrollView hs=new HorizontalScrollView(this);hs.addView(attachmentRow,mw());page.addView(hs,mw());attachmentStatus=label("",11,false);page.addView(attachmentStatus,mw());renderAttachmentChips();
        LinearLayout composer=new LinearLayout(this);composer.setOrientation(LinearLayout.HORIZONTAL);composer.setGravity(Gravity.CENTER_VERTICAL);Button plus=button("＋");EditText msg=input("Message JANUS");msg.setSingleLine(false);Button send=button("Send");composer.addView(plus,new LinearLayout.LayoutParams(dp(48),dp(58)));composer.addView(msg,new LinearLayout.LayoutParams(0,dp(58),1));composer.addView(send,new LinearLayout.LayoutParams(dp(78),dp(58)));page.addView(composer,mw());plus.setOnClickListener(v->pickFile());send.setOnClickListener(v->{String body=msg.getText().toString().trim();if(body.isEmpty()&&draftAttachments.isEmpty())return;if(body.isEmpty())body="Please assess the attached file or files.";List<Attachment> files=new ArrayList<>(draftAttachments);draftAttachments.clear();renderAttachmentChips();msg.setText("");enqueue(body,files);});}
    private void addBubble(String who,String body,boolean user){LinearLayout wrap=new LinearLayout(this);wrap.setOrientation(LinearLayout.VERTICAL);wrap.setPadding(dp(14),dp(10),dp(14),dp(10));GradientDrawable bg=new GradientDrawable();bg.setCornerRadius(dp(16));bg.setColor(user?Color.rgb(220,236,255):Color.rgb(238,238,238));wrap.setBackground(bg);TextView h=label(who,14,true);TextView t=label(body,16,false);wrap.addView(h,mw());wrap.addView(t,mw());LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(user?dp(46):0,dp(7),user?0:dp(24),dp(7));chatList.addView(wrap,lp);chatScroll.post(()->chatScroll.fullScroll(View.FOCUS_DOWN));}
    private void enqueue(String message,List<Attachment> files){long now=System.currentTimeMillis();List<Q> q=loadQueue();String sig=attachmentSignature(files);for(Q x:q)if(x.message.equals(message)&&x.attachmentSignature().equals(sig)&&now-x.created<120000){status.setText("Already queued · duplicate suppressed");return;}Q x=new Q(UUID.randomUUID().toString(),message,0,now,files);q.add(x);saveQueue(q);addBubble("You",message+(files.isEmpty()?"":"\nAttachments: "+attachmentNames(files)),true);status.setText("Sending…");sendQueued(x.id);}
    private void sendQueued(String id){if(inFlight.contains(id))return;Q x=find(id);if(x==null)return;inFlight.add(id);io.execute(()->{JSONObject b=new JSONObject();try{b.put("message",x.message);b.put("client_message_id",x.id);JSONArray ids=new JSONArray();for(Attachment a:x.attachments)ids.put(a.id);b.put("attachment_ids",ids);}catch(Exception ignored){}HttpResult r=request("POST","/desktop/chat",b.toString(),true);inFlight.remove(id);if(r.ok()){String reply;try{JSONObject j=new JSONObject(r.body);reply=j.optString("reply",r.body);JSONArray grounded=j.optJSONArray("attachments");if(grounded!=null&&grounded.length()>0)reply+="\n\nGrounded attachments: "+grounded.length();}catch(Exception e){reply=r.body;}remove(id);String finalReply=reply;ui.post(()->{if(activeTab.equals("Chat")&&chatList!=null)addBubble("JANUS",finalReply,false);status.setText("Interface active");});}else{int a=increment(id);ui.post(()->status.setText("Queued locally · retry "+Math.min(a,RETRY.length)+"/"+RETRY.length));if(a<=RETRY.length)flushSoon(RETRY[a-1]);}});}
    private void flushSoon(long delay){ui.postDelayed(()->{if(accessToken.isBlank())return;for(Q x:loadQueue())if(x.attempts<=RETRY.length)sendQueued(x.id);},delay);}
    private void renderQueued(){for(Q x:loadQueue())addBubble("You",x.message+(x.attachments.isEmpty()?"":"\nAttachments: "+attachmentNames(x.attachments))+"\nQueued locally",true);}

    // ---------- ATTACHMENTS ----------
    private void pickFile(){if(draftAttachments.size()>=MAX_ATTACHMENTS){toast("At most "+MAX_ATTACHMENTS+" attachments per turn.");return;}Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");startActivityForResult(i,PICK_FILE);}
    private void uploadPickedFile(Uri uri){String name=fileName(uri),mime=getContentResolver().getType(uri);if(mime==null)mime="application/octet-stream";String fm=mime;status.setText("Uploading "+name+"…");io.execute(()->{try{byte[] bytes=readBytes(uri,MAX_FILE_BYTES);JSONObject b=new JSONObject();b.put("filename",name);b.put("mime_type",fm);b.put("data_base64",Base64.encodeToString(bytes,Base64.NO_WRAP));HttpResult r=request("POST","/files/upload",b.toString(),true);if(!r.ok()){ui.post(()->status.setText("Upload failed · "+friendly(r)));return;}JSONObject f=new JSONObject(r.body).optJSONObject("file");if(f==null)throw new IllegalStateException("No file response");Attachment a=new Attachment(f.optString("id"),f.optString("filename",name),f.optString("mime_type",fm),f.optLong("size_bytes",bytes.length),f.optString("extraction_status","unknown"));ui.post(()->{draftAttachments.add(a);renderAttachmentChips();status.setText("Attachment ready");});}catch(Exception e){ui.post(()->status.setText("Upload failed · "+e.getMessage()));}});}
    private void renderAttachmentChips(){if(attachmentRow==null)return;attachmentRow.removeAllViews();for(Attachment a:new ArrayList<>(draftAttachments)){Button chip=button("× "+a.name);chip.setOnClickListener(v->{draftAttachments.removeIf(x->x.id.equals(a.id));renderAttachmentChips();});attachmentRow.addView(chip,ww());}if(attachmentStatus!=null)attachmentStatus.setText(draftAttachments.isEmpty()?"":draftAttachments.size()+" / "+MAX_ATTACHMENTS+" attached");}
    private byte[] readBytes(Uri uri,int max)throws Exception{try(InputStream in=getContentResolver().openInputStream(uri);ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] buf=new byte[32768];int n,total=0;while((n=in.read(buf))!=-1){total+=n;if(total>max)throw new IllegalArgumentException("File exceeds 8 MB");out.write(buf,0,n);}return out.toByteArray();}}
    private String fileName(Uri uri){String n="attachment";try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst()&&!c.getString(0).isBlank())n=c.getString(0);}catch(Exception ignored){}return n;}

    // ---------- MESSAGES ----------
    private void showMessages(){page.addView(label("Messages",30,true),mw());page.addView(label("JANUS's outbox: questions, observations, memories and follow-ups created outside the immediate chat turn.",13,false),mw());TextView body=label("Loading…",15,false);ScrollView s=new ScrollView(this);s.addView(body,mw());page.addView(s,new LinearLayout.LayoutParams(-1,0,1));Button refresh=button("Refresh");page.addView(refresh,mw());refresh.setOnClickListener(v->loadMessages(body));loadMessages(body);}
    private void loadMessages(TextView view){if(profile.isBlank()){view.setText("No JANUS profile loaded.");return;}io.execute(()->{HttpResult r=request("GET","/desktop/messages?username="+enc(profile)+"&limit=50",null,true);String out;if(r.ok()){StringBuilder b=new StringBuilder();try{JSONObject j=new JSONObject(r.body);JSONArray items=j.optJSONArray("items");b.append(j.optInt("unread",0)).append(" unread\n\n");if(items!=null)for(int i=0;i<items.length();i++){JSONObject x=items.getJSONObject(i);b.append(x.optString("message_type","Message")).append("\n").append(x.optString("detail","")).append("\n\n");}if(items==null||items.length()==0)b.append("No JANUS messages yet.");}catch(Exception e){b.append(r.body);}out=b.toString();}else out="Messages unavailable · "+friendly(r);String f=out;ui.post(()->view.setText(f));});}

    // ---------- OBSERVE ----------
    private void showObserve(){page.addView(label("Observe",30,true),mw());page.addView(label("A readable journal of externalizable JANUS core activity. Stable snapshot only; no rapid refresh or private chain-of-thought.",13,false),mw());TextView body=label("Loading core activity…",15,false);ScrollView s=new ScrollView(this);s.addView(body,mw());page.addView(s,new LinearLayout.LayoutParams(-1,0,1));Button refresh=button("Refresh thoughts");page.addView(refresh,mw());refresh.setOnClickListener(v->loadObserve(body));loadObserve(body);}
    private void loadObserve(TextView view){io.execute(()->{HttpResult r=request("GET","/desktop/runtime-cores?username="+enc(profile),null,true);String out;if(r.ok()){try{JSONObject j=new JSONObject(r.body),rt=j.optJSONObject("runtime");StringBuilder b=new StringBuilder();b.append("11 live runtime cores\n7 specialists → 2 hemispheres → Consensus → Interface\n\n");if(rt!=null){b.append("Phase: ").append(rt.optString("phase","unknown")).append("\n");b.append("Core count: ").append(rt.opt("core_count")).append("\n");b.append("Presence: ").append(rt.optString("presence_state","unknown")).append("\n");b.append("Remote clients: ").append(rt.optInt("remote_clients",0)).append("\n");b.append("Server runtime: ").append(rt.optBoolean("server_runtime_thread_alive",false)?"active":"dormant").append("\n");}b.append("\nThe specialist/hemisphere/consensus/interface telemetry is functional processing, not a claim of subjective awareness.");out=b.toString();}catch(Exception e){out=r.body;}}else out="Observe unavailable · "+friendly(r);String f=out;ui.post(()->view.setText(f));});}

    // ---------- OPTIONS: advanced features live here, as in the original app ----------
    private void showOptions(){page.addView(label("Options",30,true),mw());TextView health=label("Loading JANUS status…",14,false);page.addView(card(health),mw());addOption("Cores","11 live runtime cores: 7 specialists → 2 hemispheres → consensus → interface",v->showTab("Observe"));addOption("Memory","Trace → working → episodic → core",v->toast("Memory remains server-owned and protected; detailed memory browser is next parity pass."));addOption("Activity","Conversation, reflections, decisions and events",v->showTab("Messages"));addOption("System status","Server, sync, memory and capability health",v->loadSystemStatus(health));addOption("Artifacts","Continuity reports, research digests, project snapshots and working notes",v->startActivity(new Intent(this,ArtifactActivity.class)));addOption("Research workspace","Established results, hypotheses, negative results, evidence and open questions",v->startActivity(new Intent(this,ResearchActivity.class)));addOption("Maintenance review","Quarterly upgrade/security proposals; owner approval required",v->startActivity(new Intent(this,MaintenanceActivity.class)));addOption("Settings","Theme colours, background cycles and display controls",v->startActivity(new Intent(this,SettingsActivity.class)));addOption("Sign out",profile.isBlank()?"JANUS account":profile,v->{clearSession();showAuth();});loadSystemStatus(health);}
    private void addOption(String title,String subtitle,View.OnClickListener listener){Button b=button(title+"\n"+subtitle);b.setGravity(Gravity.START|Gravity.CENTER_VERTICAL);b.setPadding(dp(14),dp(12),dp(14),dp(12));b.setOnClickListener(listener);page.addView(b,mw());}
    private LinearLayout card(TextView t){LinearLayout c=new LinearLayout(this);c.setPadding(dp(14),dp(10),dp(14),dp(10));GradientDrawable bg=new GradientDrawable();bg.setCornerRadius(dp(14));bg.setStroke(dp(1),Color.LTGRAY);c.setBackground(bg);c.addView(t,mw());return c;}
    private void loadSystemStatus(TextView view){io.execute(()->{HttpResult r=request("GET","/diagnostics/runtime-health",null,false);String out;if(r.ok()){try{JSONObject j=new JSONObject(r.body);boolean main=j.optBoolean("main_app_loaded",false),db=j.optBoolean("database_ok",false),schema=j.optBoolean("auth_schema_ok",false),persist=j.optBoolean("core_persistence_ok",false);String level=main&&db&&schema&&persist?"Healthy":main?"Reduced capability":"Needs attention";out=level+"\nServer: "+(main?"online":"degraded")+" · Database: "+(db?"healthy":"attention")+"\nCore persistence: "+(persist?"healthy":"attention")+" · Phase: "+j.optString("core_phase","unknown")+" · Cores: "+j.opt("core_count");}catch(Exception e){out="Reduced capability";}}else out="Needs attention · "+friendly(r);String f=out;ui.post(()->view.setText(f));});}

    // ---------- QUEUE PERSISTENCE ----------
    private List<Q> loadQueue(){List<Q> out=new ArrayList<>();try{JSONArray a=new JSONArray(prefs().getString(QUEUE,"[]"));for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);List<Attachment> fs=new ArrayList<>();JSONArray fa=o.optJSONArray("attachments");if(fa!=null)for(int k=0;k<fa.length();k++){JSONObject f=fa.getJSONObject(k);fs.add(new Attachment(f.optString("id"),f.optString("name"),f.optString("mime"),f.optLong("size"),f.optString("extraction")));}out.add(new Q(o.optString("id"),o.optString("message"),o.optInt("attempts"),o.optLong("created_at"),fs));}}catch(Exception ignored){}return out;}
    private void saveQueue(List<Q> q){JSONArray a=new JSONArray();try{for(Q x:q){JSONObject o=new JSONObject();o.put("id",x.id);o.put("message",x.message);o.put("attempts",x.attempts);o.put("created_at",x.created);JSONArray fs=new JSONArray();for(Attachment f:x.attachments){JSONObject z=new JSONObject();z.put("id",f.id);z.put("name",f.name);z.put("mime",f.mime);z.put("size",f.size);z.put("extraction",f.extraction);fs.put(z);}o.put("attachments",fs);a.put(o);}}catch(Exception ignored){}prefs().edit().putString(QUEUE,a.toString()).apply();}
    private Q find(String id){for(Q x:loadQueue())if(x.id.equals(id))return x;return null;}private int increment(String id){List<Q> q=loadQueue();int n=0;for(int i=0;i<q.size();i++){Q x=q.get(i);if(x.id.equals(id)){n=x.attempts+1;q.set(i,new Q(x.id,x.message,n,x.created,x.attachments));}}saveQueue(q);return n;}private void remove(String id){List<Q> q=loadQueue();q.removeIf(x->x.id.equals(id));saveQueue(q);}
    private String attachmentSignature(List<Attachment> a){StringBuilder b=new StringBuilder();for(Attachment x:a)b.append(x.id).append('|');return b.toString();}private String attachmentNames(List<Attachment>a){StringBuilder b=new StringBuilder();for(int i=0;i<a.size();i++){if(i>0)b.append(", ");b.append(a.get(i).name);}return b.toString();}

    // ---------- NETWORK / UI HELPERS ----------
    private void checkHealth(TextView target){io.execute(()->{HttpResult r=request("GET","/health",null,false);ui.post(()->{if(!r.ok())target.setText("JANUS server unavailable · "+friendly(r));});});}
    private void checkCapabilities(){io.execute(()->{HttpResult r=request("GET","/protocol/capabilities",null,false);ui.post(()->status.setText(r.ok()?"Interface active":"Interface active · compatibility check reduced"));});}
    private HttpResult request(String method,String path,@Nullable String body,boolean auth){HttpURLConnection c=null;try{c=(HttpURLConnection)new URL(BuildConfig.SERVER_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(12000);c.setReadTimeout(45000);c.setRequestProperty("Accept","application/json");c.setRequestProperty("Connection","close");if(auth&&!accessToken.isBlank())c.setRequestProperty("Authorization","Bearer "+accessToken);if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");try(OutputStream o=c.getOutputStream()){o.write(body.getBytes(StandardCharsets.UTF_8));}}int code=c.getResponseCode();InputStream s=code>=200&&code<400?c.getInputStream():c.getErrorStream();return new HttpResult(code,read(s),null);}catch(Exception e){return new HttpResult(0,"",e.getClass().getSimpleName()+": "+e.getMessage());}finally{if(c!=null)c.disconnect();}}
    private static String read(@Nullable InputStream s)throws Exception{if(s==null)return"";StringBuilder b=new StringBuilder();try(BufferedReader r=new BufferedReader(new InputStreamReader(s,StandardCharsets.UTF_8))){String l;while((l=r.readLine())!=null)b.append(l).append('\n');}return b.toString().trim();}
    private String friendly(HttpResult r){if(r.error!=null)return r.error;if(r.code==401)return"Session expired.";if(r.code==429)return"Rate limited; try again shortly.";if(r.code==502||r.code==503||r.code==504)return"JANUS server temporarily unavailable (HTTP "+r.code+").";return r.code>0?"HTTP "+r.code:"Network request failed.";}
    private String enc(String s){return URLEncoder.encode(s,StandardCharsets.UTF_8);}
    private TextView label(String s,int sp,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setPadding(dp(4),dp(7),dp(4),dp(7));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}private EditText input(String hint){EditText e=new EditText(this);e.setHint(hint);e.setSingleLine(true);e.setPadding(dp(12),dp(8),dp(12),dp(8));return e;}private Button button(String s){Button b=new Button(this);b.setText(s);b.setAllCaps(false);return b;}private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}private LinearLayout.LayoutParams mw(){return new LinearLayout.LayoutParams(-1,-2);}private LinearLayout.LayoutParams ww(){return new LinearLayout.LayoutParams(-2,-2);}
    private record HttpResult(int code,String body,String error){boolean ok(){return code>=200&&code<300;}}private record Attachment(String id,String name,String mime,long size,String extraction){}private record Q(String id,String message,int attempts,long created,List<Attachment>attachments){String attachmentSignature(){StringBuilder b=new StringBuilder();for(Attachment a:attachments)b.append(a.id).append('|');return b.toString();}}
}
