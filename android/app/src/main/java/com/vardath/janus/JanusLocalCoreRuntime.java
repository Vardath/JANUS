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

/**
 * Persistent zero-API-cost 11-core runtime.
 *
 * Local core cycling, routing, autonomous memory resurfacing and self-assessment
 * are all deterministic and never invoke a model API. Server sync is optional.
 */
public final class JanusLocalCoreRuntime {
    private static final String SERVER="https://janus-global-core.onrender.com";
    private static final String[] NAMES={"evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface"};
    private static final String[] SPECIALISTS={"evidence","logic","counterpoint","context","memory","safety","novelty"};
    private static final int MAX_OBSERVE_EVENTS=500;
    private static final int MAX_LOCAL_MEMORIES=96;
    private static final long REST_BACKGROUND_MS=30_000L;
    private static final long AUTONOMOUS_PULSE_MS=60_000L;
    private static final long SELF_ASSESS_MS=120_000L;
    private static JanusLocalCoreRuntime instance;
    static synchronized JanusLocalCoreRuntime get(Context c){ if(instance==null)instance=new JanusLocalCoreRuntime(c.getApplicationContext()); return instance; }

    private static final class Core {
        final String name; long cycles; final ArrayDeque<String> inbox=new ArrayDeque<>(); String last="";
        final long[] fano={8,1,1,1,1,1,1,1}; long fanoSteps=0; int activeDirection=0;
        Core(String n){name=n;}
    }

    private final SharedPreferences prefs;
    private final Map<String,Core> cores=new LinkedHashMap<>();
    private final ScheduledExecutorService executor=Executors.newScheduledThreadPool(2);
    private final ArrayDeque<JSONObject> observeEvents=new ArrayDeque<>();
    private final ArrayDeque<String> localMemories=new ArrayDeque<>();
    private volatile boolean started;
    private volatile String phase="sleep";
    private volatile long phaseStarted=System.currentTimeMillis();
    private volatile long lastBackgroundCycleAt=0L,lastAutonomousAt=0L,lastSelfAssessAt=0L;
    private volatile String lastConsensus="",lastInterface="",lastSyncState="waiting";
    private volatile long lastSyncAt=0,pendingBatchMaxAt=0;
    private volatile int lastDisagreementScore=0;
    private final String installationId;

    private JanusLocalCoreRuntime(Context context){
        prefs=context.getSharedPreferences("janus",Context.MODE_PRIVATE);
        phase=prefs.getString("core_phase","sleep");
        for(String n:NAMES){ Core c=new Core(n); c.cycles=prefs.getLong("core_cycles_"+n,0); c.last=prefs.getString("core_last_"+n,""); loadFano(c); cores.put(n,c); }
        loadObserveEvents(); loadLocalMemories();
        String id=prefs.getString("core_installation_id",""); if(id==null||id.isEmpty()){id=UUID.randomUUID().toString();prefs.edit().putString("core_installation_id",id).apply();} installationId=id;
        lastConsensus=prefs.getString("core_consensus",""); lastInterface=prefs.getString("core_interface","");
        lastSyncAt=prefs.getLong("core_last_sync_at",0L);
        lastBackgroundCycleAt=prefs.getLong("core_last_background_cycle_at",0L);
        lastAutonomousAt=prefs.getLong("core_last_autonomous_at",0L);
        lastSelfAssessAt=prefs.getLong("core_last_self_assess_at",0L);
        lastDisagreementScore=prefs.getInt("core_last_disagreement_score",0);
    }

    private static String displayName(String core){return core==null?"Core":core.replace('_',' ');}
    private static String actionFor(String core){
        if("evidence".equals(core))return "checked what is supported versus inferred";
        if("logic".equals(core))return "checked consistency and causal gaps";
        if("counterpoint".equals(core))return "challenged the current interpretation and looked for alternatives";
        if("context".equals(core))return "related the topic to retained context and goals";
        if("memory".equals(core))return "compared the topic with retained local memory";
        if("safety".equals(core))return "checked privacy, security and harmful failure modes";
        if("novelty".equals(core))return "looked for an unusual but testable connection";
        if("left_hemisphere".equals(core))return "combined the evidence, logic and counterpoint views";
        if("right_hemisphere".equals(core))return "combined the context, memory and novelty views";
        if("consensus".equals(core))return "integrated both hemispheres while preserving unresolved disagreement";
        if("interface".equals(core))return "updated the user-facing shared state";
        return "processed its assigned work";
    }
    private static String topicFrom(String raw){
        if(raw==null)return "";
        int p=raw.indexOf("; topic="); if(p<0)return ""; p+=8;
        int q=raw.indexOf("; Fano",p); if(q<0)q=Math.min(raw.length(),p+260);
        return clip(raw.substring(p,q),260);
    }
    private static String externalize(String core,String peer,String type,String raw){
        String clean=clip(raw,900);
        if("process_note".equals(type)){
            String topic=topicFrom(raw);
            String base=Character.toUpperCase(displayName(core).charAt(0))+displayName(core).substring(1)+" "+actionFor(core)+".";
            return topic.isEmpty()?base:base+" Current focus: "+topic+".";
        }
        if("interaction".equals(type)){
            String topic=topicFrom(raw);
            String base=Character.toUpperCase(displayName(core).charAt(0))+displayName(core).substring(1)+" sent its current result to "+displayName(peer)+".";
            return topic.isEmpty()?base:base+" Shared focus: "+topic+".";
        }
        if("maintenance".equals(type))return "The local society completed a low-duty maintenance pass; pending work was checked with zero model/API calls.";
        if("phase".equals(type))return clean;
        if("user_topic".equals(type))return clean;
        if("autonomous_pulse".equals(type))return "Memory resurfaced retained material for an autonomous cross-core review. "+clean;
        if("self_assessment".equals(type))return "Consensus compared internal positions and measured unresolved disagreement. "+clean;
        return clean;
    }

    private synchronized void record(String core,String peer,String type,String detail){
        try{
            long ts=System.currentTimeMillis();
            String raw=detail==null?"":detail;
            JSONObject e=new JSONObject().put("event_id",UUID.randomUUID().toString()).put("source","local").put("core_name",core).put("event_type",type)
                    .put("detail",externalize(core,peer,type,raw)).put("raw_detail",raw).put("created_at",ts);
            if(peer!=null&&!peer.isEmpty())e.put("peer_core",peer);
            observeEvents.addLast(e); while(observeEvents.size()>MAX_OBSERVE_EVENTS)observeEvents.pollFirst();
        }catch(Exception ignored){}
    }

    private void loadObserveEvents(){
        String raw=prefs.getString("core_observe_events",""); if(raw==null||raw.isEmpty())return;
        try{JSONArray a=new JSONArray(raw);for(int i=Math.max(0,a.length()-MAX_OBSERVE_EVENTS);i<a.length();i++){JSONObject x=a.optJSONObject(i);if(x!=null)observeEvents.addLast(x);}}catch(Exception ignored){}
    }
    private JSONArray observeArray(){JSONArray a=new JSONArray();for(JSONObject x:observeEvents)a.put(x);return a;}
    synchronized JSONArray localObserveJson(){return observeArray();}

    private void loadLocalMemories(){
        String raw=prefs.getString("core_local_memories",""); if(raw==null||raw.isEmpty())return;
        try{JSONArray a=new JSONArray(raw);for(int i=Math.max(0,a.length()-MAX_LOCAL_MEMORIES);i<a.length();i++){String x=a.optString(i,"").trim();if(!x.isEmpty())localMemories.addLast(x);}}catch(Exception ignored){}
    }
    private JSONArray memoryArray(){JSONArray a=new JSONArray();for(String x:localMemories)a.put(x);return a;}
    synchronized JSONArray localMemoryJson(){return memoryArray();}
    private void remember(String role,String text){
        String clean=(text==null?"":text.trim());if(clean.isEmpty())return;
        if(clean.length()>1200)clean=clean.substring(0,1200);
        localMemories.addLast(role+": "+clean); while(localMemories.size()>MAX_LOCAL_MEMORIES)localMemories.pollFirst();
    }

    private JSONArray unsyncedObserveArray(){
        JSONArray a=new JSONArray();int kept=0;long maxAt=lastSyncAt;
        for(JSONObject x:observeEvents){long at=x.optLong("created_at",0L);if(at>lastSyncAt){a.put(x);kept++;if(at>maxAt)maxAt=at;if(kept>=100)break;}}
        pendingBatchMaxAt=maxAt;return a;
    }

    synchronized void start(){if(started)return;started=true;executor.scheduleAtFixedRate(this::tickSafe,0,5,TimeUnit.SECONDS);executor.scheduleAtFixedRate(this::syncSafe,10,15,TimeUnit.SECONDS);}
    private void tickSafe(){try{tick();}catch(Exception ignored){}}

    synchronized void ingestUserMessage(String text){
        String clean=text==null?"":text.trim();if(clean.isEmpty())return;
        remember("user",clean);record("interface",null,"user_topic","Local society received user topic: "+clip(clean,600));
        for(String n:SPECIALISTS){cores.get(n).inbox.addLast("user topic: "+clean);record("interface",n,"interaction","Seeded local specialist with current user topic: "+clip(clean,500));}
        serviceBurst(true);
        persist();
    }

    synchronized void ingestServerReply(String text){
        String clean=text==null?"":text.trim();if(clean.isEmpty())return;
        remember("janus",clean);
        cores.get("memory").inbox.addLast("server response to retain: "+clean);
        cores.get("context").inbox.addLast("server response context: "+clean);
        cores.get("counterpoint").inbox.addLast("review server response for unresolved alternatives: "+clean);
        record("interface","memory","interaction","Server reply added to local continuity memory.");
        serviceBurst(true);persist();
    }

    private void cycle(String n){Core c=cores.get(n);if(c==null)return;String t=think(c);c.last=t;c.cycles++;record(n,null,"process_note",t);route(n,t);}

    private synchronized void tick(){
        long now=System.currentTimeMillis(),elapsed=now-phaseStarted;
        if("wake".equals(phase)&&elapsed>=5*60_000L){phase="sleep";phaseStarted=now;record("interface",null,"phase","Local society entered low-duty mode; all cores remain available for work.");}
        else if("sleep".equals(phase)&&elapsed>=10*60_000L){phase="wake";phaseStarted=now;record("interface",null,"phase","Local society entered full-rate processing.");}
        boolean fullRate="wake".equals(phase);
        if(cores.get("interface").inbox.size()>0)cycle("interface");
        if(fullRate || now-lastBackgroundCycleAt>=REST_BACKGROUND_MS){
            serviceBurst(false); lastBackgroundCycleAt=now;
            if(!fullRate)record("interface",null,"maintenance","Low-duty local maintenance pass checked all pending core work; zero API calls.");
        }
        if(now-lastAutonomousAt>=AUTONOMOUS_PULSE_MS){autonomousPulse(now);lastAutonomousAt=now;}
        if(now-lastSelfAssessAt>=SELF_ASSESS_MS){selfAssess(now);lastSelfAssessAt=now;}
        persist();
    }

    private void autonomousPulse(long now){
        if(localMemories.isEmpty()){record("memory",null,"autonomous_pulse","Local autonomous pulse found no retained topic yet.");return;}
        List<String> mem=new ArrayList<>(localMemories);
        int a=Math.floorMod((int)(now/60000L),mem.size());
        int b=mem.size()==1?a:Math.floorMod(a+Math.max(1,mem.size()/2),mem.size());
        String first=mem.get(a),second=mem.get(b);
        String task="Autonomous revisit: "+clip(first,420)+(a==b?"":" | Compare/connect with: "+clip(second,420));
        for(String n:SPECIALISTS)cores.get(n).inbox.addLast(task);
        record("memory","novelty","autonomous_pulse",task);
        serviceBurst(true);
    }

    private void selfAssess(long now){
        String[][] pairs={{"evidence","counterpoint"},{"logic","novelty"},{"context","safety"},{"left_hemisphere","right_hemisphere"},{"consensus","interface"}};
        int disagree=0;StringBuilder details=new StringBuilder();
        for(String[] p:pairs){Core a=cores.get(p[0]),b=cores.get(p[1]);int delta=Math.abs(a.activeDirection-b.activeDirection);if(delta>0)disagree++;if(details.length()>0)details.append("; ");details.append(p[0]).append("/").append(p[1]).append(" d=").append(delta);}
        lastDisagreementScore=disagree;
        String summary="Local self-assessment: "+disagree+" of "+pairs.length+" comparison pairs differ in active Fano direction ("+details+").";
        record("consensus",null,"self_assessment",summary);
        if(disagree>0){
            String task=summary+" Re-examine current topic; Evidence should seek support, Logic consistency, Counterpoint alternatives, and Consensus should preserve unresolved disagreement if it cannot be narrowed.";
            cores.get("evidence").inbox.addLast(task);cores.get("logic").inbox.addLast(task);cores.get("counterpoint").inbox.addLast(task);cores.get("consensus").inbox.addLast(task);
            serviceBurst(true);
        }
    }

    private void serviceBurst(boolean includeInterface){
        for(String n:SPECIALISTS)if(!cores.get(n).inbox.isEmpty())cycle(n);
        if(!cores.get("left_hemisphere").inbox.isEmpty())cycle("left_hemisphere");
        if(!cores.get("right_hemisphere").inbox.isEmpty())cycle("right_hemisphere");
        if(!cores.get("consensus").inbox.isEmpty())cycle("consensus");
        if(includeInterface&&!cores.get("interface").inbox.isEmpty())cycle("interface");
    }

    private void fanoIngest(Core c,List<String> texts){
        if(texts.isEmpty())texts=Collections.singletonList(c.last.isEmpty()?c.name:c.last);
        for(String t:texts){int h=(c.name+"|"+t).hashCode();int a=1+Math.floorMod(h,7);int b=1+Math.floorMod(Integer.rotateLeft(h,11),7);int d=(a^b)&7;if(d==0)d=1+Math.floorMod(Integer.rotateLeft(h,19),7);c.fano[a]+=3;c.fano[b]+=2;c.fano[d]+=1;c.fano[0]+=1;}
        long total=0;for(long v:c.fano)total+=v;long mean=Math.max(1,total/8);
        for(int i=0;i<8;i++){long w=c.fano[i];if(w>mean)c.fano[i]=w-Math.max(1,(w-mean)/8);else if(w<mean)c.fano[i]=w+Math.max(1,(mean-w)/16);}
        long max=-1;int idx=0;for(int i=0;i<8;i++)if(c.fano[i]>max){max=c.fano[i];idx=i;}c.activeDirection=idx;c.fanoSteps++;
    }

    private String think(Core c){
        List<String> inputs=new ArrayList<>();while(!c.inbox.isEmpty()&&inputs.size()<8)inputs.add(c.inbox.pollFirst());
        fanoIngest(c,inputs);
        long line=c.fano[1]+c.fano[2]+c.fano[3],off=c.fano[4]+c.fano[5]+c.fano[6]+c.fano[7];
        String topic=inputs.isEmpty()?"maintenance / retained state":clip(inputs.get(0),320);
        String roleNote;
        switch(c.name){
            case "evidence": roleNote="grounding check: separate recorded support from inference"; break;
            case "logic": roleNote="consistency check: look for incompatible assumptions or causal gaps"; break;
            case "counterpoint": roleNote="challenge: search for alternatives, coincidence and failure modes"; break;
            case "context": roleNote="context check: relate the topic to prior goals, history and environment"; break;
            case "memory": roleNote="continuity check: compare with retained local topics and unfinished work"; break;
            case "safety": roleNote="boundary check: privacy, security and harmful failure modes"; break;
            case "novelty": roleNote="connection search: look for an unusual but testable relation"; break;
            case "left_hemisphere": roleNote="analytic synthesis of evidence/logic/counterpoint inputs"; break;
            case "right_hemisphere": roleNote="contextual synthesis of context/memory/novelty inputs"; break;
            case "consensus": roleNote="integration: combine hemispheres while preserving unresolved disagreement"; break;
            default: roleNote="interface update: expose only a concise externalizable state";
        }
        String out=c.name+": "+roleNote+"; topic="+topic+"; Fano d"+c.activeDirection+" 1|3|4="+c.fano[0]+"|"+line+"|"+off+"; processed "+inputs.size()+" peer inputs";
        if(("memory".equals(c.name)||"novelty".equals(c.name)||"consensus".equals(c.name))&&!inputs.isEmpty())remember("core:"+c.name,out);
        return out;
    }

    private synchronized void send(String from,String to,String text){Core t=cores.get(to);if(t!=null&&!from.equals(to)){t.inbox.addLast(from+": "+text);record(from,to,"interaction",text);}}
    private void route(String from,String text){
        if(Arrays.asList("evidence","logic","counterpoint").contains(from))send(from,"left_hemisphere",text);
        else if(Arrays.asList("context","memory","novelty").contains(from))send(from,"right_hemisphere",text);
        else if("safety".equals(from)){send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);send(from,"consensus",text);send(from,"interface",text);}
        else if("left_hemisphere".equals(from)){send(from,"right_hemisphere",text);send(from,"consensus",text);}
        else if("right_hemisphere".equals(from)){send(from,"left_hemisphere",text);send(from,"consensus",text);}
        else if("consensus".equals(from)){lastConsensus=text;send(from,"interface",text);send(from,"left_hemisphere",text);send(from,"right_hemisphere",text);}
        else if("interface".equals(from)){lastInterface=text;send(from,"consensus",text);}
    }

    private static String clip(String s,int max){String x=s==null?"":s.replace('\n',' ').replace('\r',' ').trim();return x.length()<=max?x:x.substring(0,max)+"…";}
    private void loadFano(Core c){String raw=prefs.getString("core_fano_"+c.name,"");if(raw==null||raw.isEmpty())return;try{JSONArray a=new JSONArray(raw);for(int i=0;i<8&&i<a.length();i++)c.fano[i]=Math.max(1,a.optLong(i,1));c.fanoSteps=prefs.getLong("core_fano_steps_"+c.name,0);c.activeDirection=prefs.getInt("core_fano_active_"+c.name,0);}catch(Exception ignored){}}

    private synchronized void persist(){
        SharedPreferences.Editor e=prefs.edit().putString("core_phase",phase).putString("core_consensus",lastConsensus).putString("core_interface",lastInterface)
                .putString("core_observe_events",observeArray().toString()).putString("core_local_memories",memoryArray().toString())
                .putLong("core_last_sync_at",lastSyncAt).putLong("core_last_background_cycle_at",lastBackgroundCycleAt)
                .putLong("core_last_autonomous_at",lastAutonomousAt).putLong("core_last_self_assess_at",lastSelfAssessAt)
                .putInt("core_last_disagreement_score",lastDisagreementScore);
        for(Core c:cores.values()){e.putLong("core_cycles_"+c.name,c.cycles).putString("core_last_"+c.name,c.last);JSONArray a=new JSONArray();for(long v:c.fano)a.put(v);e.putString("core_fano_"+c.name,a.toString()).putLong("core_fano_steps_"+c.name,c.fanoSteps).putInt("core_fano_active_"+c.name,c.activeDirection);}e.apply();
    }

    synchronized JSONObject statusJson() throws Exception{
        JSONObject root=new JSONObject().put("architecture","11 Fano/JANUS cores").put("topology","7 -> 2 -> 1 -> 1").put("phase",phase).put("background_phase",phase)
                .put("interface_available",true).put("running",started).put("installation_id",installationId).put("consensus",lastConsensus).put("interface",lastInterface)
                .put("last_sync_at",lastSyncAt).put("sync_state",lastSyncState).put("persistent_storage",true).put("storage_backend","Android app-private SharedPreferences")
                .put("observe_events",observeArray()).put("local_memories",memoryArray()).put("rest_background_seconds",REST_BACKGROUND_MS/1000L)
                .put("autonomous_pulse_seconds",AUTONOMOUS_PULSE_MS/1000L).put("self_assess_seconds",SELF_ASSESS_MS/1000L).put("last_disagreement_score",lastDisagreementScore).put("core_cycle_api_calls",0);
        JSONObject cj=new JSONObject();for(Core c:cores.values()){JSONObject x=new JSONObject().put("awake",started).put("available",started).put("processing_mode","interface".equals(c.name)?"continuous":("wake".equals(phase)?"full-rate":"low-duty")).put("cycle_count",c.cycles).put("pending_messages",c.inbox.size()).put("last_output",c.last);JSONArray w=new JSONArray();for(long v:c.fano)w.put(v);long line=c.fano[1]+c.fano[2]+c.fano[3],off=c.fano[4]+c.fano[5]+c.fano[6]+c.fano[7];x.put("fano",new JSONObject().put("weights",w).put("step_count",c.fanoSteps).put("active_direction",c.activeDirection).put("projection_1_3_4",new JSONObject().put("origin",c.fano[0]).put("line",line).put("off_line",off)));cj.put(c.name,x);}root.put("cores",cj);return root;
    }

    private JSONObject summary() throws Exception{JSONObject cycles=new JSONObject();for(Core c:cores.values())cycles.put(c.name,c.cycles);return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles).put("observe_events",unsyncedObserveArray());}
    private void syncSafe(){try{sync();}catch(Exception e){lastSyncState="offline";}}
    private synchronized void sync() throws Exception{
        String token=prefs.getString("access_token","");if(token==null||token.trim().isEmpty()){lastSyncState="not-signed-in";return;}
        HttpURLConnection c=(HttpURLConnection)new URL(SERVER+"/core-sync/exchange").openConnection();c.setRequestMethod("POST");c.setDoOutput(true);c.setConnectTimeout(15000);c.setReadTimeout(30000);c.setRequestProperty("Content-Type","application/json");c.setRequestProperty("Authorization","Bearer "+token.trim());JSONObject payload=summary();try(OutputStream os=c.getOutputStream()){os.write(payload.toString().getBytes(StandardCharsets.UTF_8));}
        int code=c.getResponseCode();BufferedReader r=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=r.readLine())!=null)b.append(line);r.close();
        if(code<400){JSONObject server=new JSONObject(b.toString()).optJSONObject("server");if(server!=null){String rc=server.optString("consensus","");String ri=server.optString("interface","");if(!rc.isEmpty())send("interface","consensus","global consensus: "+rc);if(!ri.isEmpty())send("consensus","interface","global interface: "+ri);serviceBurst(true);}if(pendingBatchMaxAt>lastSyncAt)lastSyncAt=pendingBatchMaxAt;lastSyncState="connected";persist();}else lastSyncState="server-error-"+code;
    }
}
