package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Persistent zero-API-cost 11-core runtime; every active core contains an 8-state Fano/JANUS unit. */
public final class JanusLocalCoreRuntime {
    private static final String SERVER="https://janus-global-core.onrender.com";
    private static final String[] NAMES={"evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface"};
    private static JanusLocalCoreRuntime instance;
    static synchronized JanusLocalCoreRuntime get(Context c){ if(instance==null)instance=new JanusLocalCoreRuntime(c.getApplicationContext()); return instance; }

    private static final class Core {
        final String name; long cycles; final ArrayDeque<String> inbox=new ArrayDeque<>(); String last="";
        final long[] fano={8,1,1,1,1,1,1,1}; long fanoSteps=0; int activeDirection=0;
        Core(String n){name=n;}
    }

    private final SharedPreferences prefs; private final Map<String,Core> cores=new LinkedHashMap<>();
    private final ScheduledExecutorService executor=Executors.newScheduledThreadPool(2);
    private volatile boolean started; private volatile String phase="sleep"; private volatile long phaseStarted=System.currentTimeMillis();
    private volatile String lastConsensus="",lastInterface="",lastSyncState="waiting"; private volatile long lastSyncAt=0; private final String installationId;

    private JanusLocalCoreRuntime(Context context){
        prefs=context.getSharedPreferences("janus",Context.MODE_PRIVATE); phase=prefs.getString("core_phase","sleep");
        for(String n:NAMES){ Core c=new Core(n); c.cycles=prefs.getLong("core_cycles_"+n,0); c.last=prefs.getString("core_last_"+n,""); loadFano(c); cores.put(n,c); }
        String id=prefs.getString("core_installation_id",""); if(id==null||id.isEmpty()){id=UUID.randomUUID().toString();prefs.edit().putString("core_installation_id",id).apply();} installationId=id;
        lastConsensus=prefs.getString("core_consensus",""); lastInterface=prefs.getString("core_interface","");
    }

    synchronized void start(){ if(started)return; started=true; executor.scheduleAtFixedRate(this::tickSafe,0,5,TimeUnit.SECONDS); executor.scheduleAtFixedRate(this::syncSafe,20,60,TimeUnit.SECONDS); }
    private void tickSafe(){try{tick();}catch(Exception ignored){}}
    private synchronized void tick(){
        long now=System.currentTimeMillis(),elapsed=now-phaseStarted;
        if("wake".equals(phase)&&elapsed>=5*60_000L){phase="sleep";phaseStarted=now;persist();return;}
        if("sleep".equals(phase)&&elapsed>=10*60_000L){phase="wake";phaseStarted=now;}
        if(!"wake".equals(phase))return;
        for(String n:NAMES){Core c=cores.get(n);String t=think(c);c.last=t;c.cycles++;route(n,t);} persist();
    }

    private void fanoIngest(Core c,List<String> texts){
        if(texts.isEmpty())texts=Collections.singletonList(c.last.isEmpty()?c.name:c.last);
        for(String t:texts){int h=(c.name+"|"+t).hashCode();int a=1+Math.floorMod(h,7);int b=1+Math.floorMod(Integer.rotateLeft(h,11),7);int d=(a^b)&7;if(d==0)d=1+Math.floorMod(Integer.rotateLeft(h,19),7);c.fano[a]+=3;c.fano[b]+=2;c.fano[d]+=1;c.fano[0]+=1;}
        long total=0;for(long v:c.fano)total+=v;long mean=Math.max(1,total/8);
        for(int i=0;i<8;i++){long w=c.fano[i];if(w>mean)c.fano[i]=w-Math.max(1,(w-mean)/8);else if(w<mean)c.fano[i]=w+Math.max(1,(mean-w)/16);}
        long max=-1;int idx=0;for(int i=0;i<8;i++)if(c.fano[i]>max){max=c.fano[i];idx=i;}c.activeDirection=idx;c.fanoSteps++;
    }

    private String think(Core c){
        List<String> inputs=new ArrayList<>();while(!c.inbox.isEmpty()&&inputs.size()<8)inputs.add(c.inbox.pollLast());c.inbox.clear();fanoIngest(c,inputs);
        long line=c.fano[1]+c.fano[2]+c.fano[3],off=c.fano[4]+c.fano[5]+c.fano[6]+c.fano[7];
        String role=c.name;if("left_hemisphere".equals(role))role="analytic hemisphere";else if("right_hemisphere".equals(role))role="contextual hemisphere";else if("consensus".equals(role))role="consensus reader/giver";else if("interface".equals(role))role="main interface";
        return role+": Fano d"+c.activeDirection+" 1|3|4="+c.fano[0]+"|"+line+"|"+off+"; processed "+inputs.size()+" peer inputs";
    }

    private void send(String from,String to,String text){Core t=cores.get(to);if(t!=null&&!from.equals(to))t.inbox.addLast(from+": "+text);}
    private void route(String from,String text){
        if(Arrays.asList("evidence","logic","counterpoint").contains(from))send(from,"left_hemisphere",text);
        else if(Arrays.asList("context","memory","novelty").contains(from))send(from,"right_hemisphere",text);
        else if("safety".equals(from)){send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);send(from,"consensus",text);send(from,"interface",text);}
        else if("left_hemisphere".equals(from)){send(from,"right_hemisphere",text);send(from,"consensus",text);}
        else if("right_hemisphere".equals(from)){send(from,"left_hemisphere",text);send(from,"consensus",text);}
        else if("consensus".equals(from)){lastConsensus=text;send(from,"interface",text);send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);}
        else if("interface".equals(from)){lastInterface=text;send(from,"consensus",text);}
    }

    private void loadFano(Core c){
        String raw=prefs.getString("core_fano_"+c.name,"");if(raw==null||raw.isEmpty())return;
        try{JSONArray a=new JSONArray(raw);for(int i=0;i<8&&i<a.length();i++)c.fano[i]=Math.max(1,a.optLong(i,1));c.fanoSteps=prefs.getLong("core_fano_steps_"+c.name,0);c.activeDirection=prefs.getInt("core_fano_active_"+c.name,0);}catch(Exception ignored){}
    }
    private void persist(){SharedPreferences.Editor e=prefs.edit().putString("core_phase",phase).putString("core_consensus",lastConsensus).putString("core_interface",lastInterface);for(Core c:cores.values()){e.putLong("core_cycles_"+c.name,c.cycles).putString("core_last_"+c.name,c.last);JSONArray a=new JSONArray();for(long v:c.fano)a.put(v);e.putString("core_fano_"+c.name,a.toString()).putLong("core_fano_steps_"+c.name,c.fanoSteps).putInt("core_fano_active_"+c.name,c.activeDirection);}e.apply();}

    synchronized JSONObject statusJson() throws Exception{
        JSONObject root=new JSONObject().put("architecture","11 Fano/JANUS cores").put("topology","7 -> 2 -> 1 -> 1").put("phase",phase).put("running",started).put("installation_id",installationId).put("consensus",lastConsensus).put("interface",lastInterface).put("last_sync_at",lastSyncAt).put("sync_state",lastSyncState).put("persistent_storage",true).put("storage_backend","Android app-private SharedPreferences");
        JSONObject cj=new JSONObject();for(Core c:cores.values()){JSONObject x=new JSONObject().put("cycle_count",c.cycles).put("pending_messages",c.inbox.size()).put("last_output",c.last);JSONArray w=new JSONArray();for(long v:c.fano)w.put(v);long line=c.fano[1]+c.fano[2]+c.fano[3],off=c.fano[4]+c.fano[5]+c.fano[6]+c.fano[7];x.put("fano",new JSONObject().put("weights",w).put("step_count",c.fanoSteps).put("active_direction",c.activeDirection).put("projection_1_3_4",new JSONObject().put("origin",c.fano[0]).put("line",line).put("off_line",off)));cj.put(c.name,x);}root.put("cores",cj);return root;
    }

    private JSONObject summary() throws Exception{JSONObject cycles=new JSONObject();for(Core c:cores.values())cycles.put(c.name,c.cycles);return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles);}
    private void syncSafe(){try{sync();}catch(Exception e){lastSyncState="offline";}}
    private void sync() throws Exception{
        String token=prefs.getString("access_token","");if(token==null||token.trim().isEmpty()){lastSyncState="not-signed-in";return;}
        HttpURLConnection c=(HttpURLConnection)new URL(SERVER+"/core-sync/exchange").openConnection();c.setRequestMethod("POST");c.setDoOutput(true);c.setConnectTimeout(15000);c.setReadTimeout(30000);c.setRequestProperty("Content-Type","application/json");c.setRequestProperty("Authorization","Bearer "+token.trim());try(OutputStream os=c.getOutputStream()){os.write(summary().toString().getBytes(StandardCharsets.UTF_8));}
        int code=c.getResponseCode();BufferedReader r=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=r.readLine())!=null)b.append(line);r.close();if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");if(!rc.isEmpty())send("interface","consensus","global: "+rc);if(!ri.isEmpty())send("consensus","interface","global: "+ri);}lastSyncAt=System.currentTimeMillis();lastSyncState="connected";}else lastSyncState="server-error-"+code;
    }
}
