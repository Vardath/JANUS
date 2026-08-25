package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Recursive cognition inside each local top-level core with one outward Front stream.
 * Every outer core still owns an internal seven-position JANUS/Fano processor.
 */
public final class JanusRecursiveCoreEngine {
    private static final String PREFS = "janus_recursive_core_engine_v1";
    private static final String STATE_KEY = "states";
    private static final String[] NAMES = new String[]{
            "evidence","safety","counterpoint","context","logic","novelty","memory",
            "left_hemisphere","right_hemisphere","front","interface"
    };
    private static final String[] SPECIALISTS = new String[]{"evidence","safety","counterpoint","context","logic","novelty","memory"};
    private static final String[] FACULTY = new String[]{"reference","truth","valence","significance","pattern","understanding","possibility","continuity"};
    private static final int[][] BIASES = new int[][]{
            {0,0,0,0,0,0,0,0},{0,5,0,1,0,2,0,0},{0,0,5,2,0,0,0,1},{0,2,2,5,0,1,0,0},
            {0,0,0,0,5,0,2,1},{0,2,0,1,2,5,0,0},{0,0,2,0,2,1,5,0},{0,1,1,0,1,1,0,5},
            {0,3,0,2,0,5,0,1},{0,0,1,0,4,0,5,2},{0,0,3,4,0,2,1,3},{0,2,3,3,0,2,2,1},
    };
    private static JanusRecursiveCoreEngine instance;
    static synchronized JanusRecursiveCoreEngine get(Context context) { if (instance == null) instance = new JanusRecursiveCoreEngine(context.getApplicationContext()); return instance; }
    static synchronized void clearInstance() { if (instance != null) instance.stop(); instance = null; }

    private static final class Node {
        final String name; final long[] weights = new long[]{8,1,1,1,1,1,1,1};
        int active; long cycles,revisions,peerTurns,quiescent; String conclusion="",aiCounsel="",lastSignature="",lastUserStimulus="";
        Node(String name){this.name=name;}
    }

    private final SharedPreferences prefs;
    private final Map<String,Node> nodes = new LinkedHashMap<>();
    private ScheduledExecutorService scheduler; private JanusLocalCoreRuntime runtime; private volatile boolean started;
    private JanusRecursiveCoreEngine(Context context){ prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE); for(String n:NAMES)nodes.put(n,new Node(n)); restore(); }

    synchronized void start(JanusLocalCoreRuntime localRuntime){ runtime=localRuntime; if(started)return; started=true; scheduler=Executors.newSingleThreadScheduledExecutor(); scheduler.scheduleAtFixedRate(this::backgroundSafe,15,30,TimeUnit.SECONDS); }
    synchronized void stop(){ started=false; if(scheduler!=null)scheduler.shutdownNow(); scheduler=null; persist(); }

    /** User input always rouses foreground cognition even when scheduled background work is resting. */
    synchronized JSONObject foreground(String userMessage){
        String input=clip(userMessage,1800); for(Node n:nodes.values()) n.lastUserStimulus=input;
        processForeground(input); persist(); return snapshot();
    }
    synchronized void sense(String modality,String source,String content){
        String input="sense:"+clip(modality,30)+":"+clip(source,80)+" "+clip(content,1200);
        for(Node n:nodes.values()) n.lastUserStimulus=input;
        processForeground(input); persist();
    }

    synchronized void applyAiCounsel(JSONObject counsel){
        if(counsel==null)return;
        for(String name:NAMES){
            if("interface".equals(name)) continue;
            String text=counsel.optString(name,"").trim(); if(text.isEmpty())continue;
            Node n=nodes.get(name); if(!text.equals(n.aiCounsel)){ n.aiCounsel=clip(text,900); n.revisions++; }
        }
        Node front=nodes.get("front"); if(front!=null&&!front.aiCounsel.isBlank()) think(front,"Front AI counsel: "+front.aiCounsel,peerDigest("front"),true);
        Node face=nodes.get("interface"); if(front!=null&&face!=null) think(face,front.conclusion,"front:"+clip(front.conclusion,600),true);
        persist();
    }

    synchronized JSONObject snapshot(){ JSONObject root=new JSONObject(); try{
        root.put("recursive_core_engine",true); root.put("core_count",11); root.put("internal_fano_positions_per_core",7);
        root.put("background_model_calls",0); root.put("outward_route","7 specialists -> left/right -> front -> interface");
        root.put("interface_input_source","front"); root.put("rest_is_passive",true); root.put("foreground_can_rouse",true);
        JSONObject cores=new JSONObject(); for(Node n:nodes.values())cores.put(n.name,nodeJson(n)); root.put("cores",cores);
    }catch(Exception ignored){} return root; }

    private void backgroundSafe(){ try{ synchronized(this){ if(!started)return; String phase="wake";
        try{ if(runtime!=null)phase=runtime.statusJson().optString("phase","wake"); }catch(Exception ignored){}
        if("sleep".equalsIgnoreCase(phase)||"rest".equalsIgnoreCase(phase)){ persist(); return; }
        processBackground(); persist();
    }}catch(Exception ignored){} }

    /** Foreground route is strict: seven -> hemispheres -> Front -> Interface. */
    private void processForeground(String stimulus){
        Map<String,String> seven=new LinkedHashMap<>();
        for(String name:SPECIALISTS){ Node n=nodes.get(name); think(n,stimulus,"",true); seven.put(name,n.conclusion); }
        for(String name:SPECIALISTS){ Node n=nodes.get(name); String peers=peerDigestFrom(seven,name); n.peerTurns+=Math.max(0,seven.size()-1); if(think(n,stimulus,peers,false))n.revisions++; seven.put(name,n.conclusion); }
        String sevenDigest=peerDigestFrom(seven,"");
        Node left=nodes.get("left_hemisphere"), right=nodes.get("right_hemisphere");
        think(left,"integrate seven specialist results",sevenDigest,true); left.peerTurns+=7;
        think(right,"integrate seven specialist results",sevenDigest,true); right.peerTurns+=7;
        Node front=nodes.get("front"); String hemis="left_hemisphere:"+clip(left.conclusion,600)+" | right_hemisphere:"+clip(right.conclusion,600);
        think(front,"integrate left and right hemisphere results",hemis,true); front.peerTurns+=2;
        Node face=nodes.get("interface"); think(face,front.conclusion,"front:"+clip(front.conclusion,700),true); face.peerTurns++;
    }

    /** Background society may exchange broadly, but repeated state must decay to quiescence. */
    private void processBackground(){
        Map<String,String> initial=new LinkedHashMap<>(); int changed=0;
        for(Node n:nodes.values()){ if(think(n,n.conclusion.isBlank()?"retained background state":n.conclusion,"",false))changed++; initial.put(n.name,n.conclusion); }
        if(changed==0)return;
        processPeerRevision(initial);
    }

    /** Compatibility-named bounded peer pass; unlike the first implementation it never self-sustains unchanged traffic. */
    private void processPeerRevision(Map<String,String> initial){
        for(Node n:nodes.values()){ String peers=peerDigestFrom(initial,n.name); if(think(n,"background peer revision",peers,false)){ n.peerTurns+=Math.max(0,initial.size()-1); n.revisions++; } }
    }

    private String peerDigest(String forName){ Map<String,String> m=new LinkedHashMap<>(); for(Node n:nodes.values())m.put(n.name,n.conclusion); return peerDigestFrom(m,forName); }
    private static String peerDigestFrom(Map<String,String> src,String exclude){ StringBuilder b=new StringBuilder(); for(Map.Entry<String,String>e:src.entrySet()){ if(e.getKey().equals(exclude)||e.getValue()==null||e.getValue().isBlank())continue; if(b.length()>0)b.append(" | "); b.append(e.getKey()).append(':').append(clip(e.getValue(),180)); } return b.toString(); }

    private boolean think(Node n,String content,String peerText,boolean force){
        String sig=signature(content,peerText,n.aiCounsel); if(!force&&sig.equals(n.lastSignature)){ n.quiescent++; return false; } n.lastSignature=sig;
        String low=(content+" "+peerText).toLowerCase(Locale.ROOT); int[] scores=new int[8]; String[][] cues=new String[][]{{},
                {"evidence","source","fact","true","false","claim","support","verify","confidence"},
                {"want","prefer","good","bad","harm","benefit","safe","unsafe","privacy","boundary","goal"},
                {"important","urgent","risk","conflict","contradict","however","but","failure","consequence"},
                {"pattern","context","relationship","similar","structure","system","environment","analogy"},
                {"because","cause","logic","model","therefore","constraint","explain","predict","consistent"},
                {"could","might","possible","idea","alternative","imagine","create","explore","option","future"},
                {"remember","before","again","history","previous","continuity","memory","learned","past"}};
        int biasRow=indexOf(n.name)+1; for(int d=1;d<=7;d++){ int hits=0; for(String cue:cues[d])if(low.contains(cue))hits++; int score=2+hits*2+BIASES[biasRow][d]; scores[d]=score; n.weights[d]+=Math.max(1,score); }
        n.weights[0]++; int active=1; for(int d=2;d<=7;d++)if(scores[d]>scores[active])active=d; n.active=active; n.cycles++;
        String peerClause=peerText==null||peerText.isBlank()?"":"; revised against bounded peer conclusions"; String aiClause=n.aiCounsel.isBlank()?"":"; own AI counsel retained";
        n.conclusion=clip(n.name+" ran its complete internal JANUS/Fano structure; outer disposition="+role(n.name)+"; dominant internal d"+active+" "+FACULTY[active]+peerClause+aiClause+"; focus="+content,1300);
        for(int i=0;i<8;i++)if(n.weights[i]>5000)n.weights[i]=Math.max(1,n.weights[i]/2); return true;
    }

    private JSONObject nodeJson(Node n)throws Exception{ JSONObject x=new JSONObject(); x.put("recursive_janus",true);x.put("ai_capable",true);x.put("outer_disposition",role(n.name));x.put("active_direction",n.active);x.put("active_faculty",n.active>=0&&n.active<FACULTY.length?FACULTY[n.active]:"reference"); JSONArray w=new JSONArray();for(long v:n.weights)w.put(v);x.put("weights",w);x.put("cycles",n.cycles);x.put("revision_count",n.revisions);x.put("peer_turn_count",n.peerTurns);x.put("quiescent_count",n.quiescent);x.put("conclusion",n.conclusion);x.put("ai_last",n.aiCounsel);x.put("last_user_stimulus",n.lastUserStimulus);x.put("projection_1_3_4",new JSONObject().put("origin",n.weights[0]).put("line",n.weights[1]+n.weights[2]+n.weights[3]).put("off_line",n.weights[4]+n.weights[5]+n.weights[6]+n.weights[7]));return x; }
    private void persist(){try{prefs.edit().putString(STATE_KEY,snapshot().toString()).apply();}catch(Exception ignored){}}
    private void restore(){try{JSONObject root=new JSONObject(prefs.getString(STATE_KEY,"{}"));JSONObject cores=root.optJSONObject("cores");if(cores==null)return;for(Node n:nodes.values()){JSONObject x=cores.optJSONObject(n.name);if(x==null)continue;JSONArray w=x.optJSONArray("weights");if(w!=null)for(int i=0;i<8&&i<w.length();i++)n.weights[i]=Math.max(1,w.optLong(i,n.weights[i]));n.active=x.optInt("active_direction",0);n.cycles=x.optLong("cycles",0);n.revisions=x.optLong("revision_count",0);n.peerTurns=x.optLong("peer_turn_count",0);n.quiescent=x.optLong("quiescent_count",0);n.conclusion=x.optString("conclusion","");n.aiCounsel=x.optString("ai_last","");n.lastUserStimulus=x.optString("last_user_stimulus","");}}catch(Exception ignored){}}
    static void clearAccountBoundState(Context context){clearInstance();context.getApplicationContext().getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().clear().commit();}
    private static int indexOf(String name){for(int i=0;i<NAMES.length;i++)if(NAMES[i].equals(name))return i;return 0;}
    private static String role(String name){switch(name){case"evidence":return"grounding/evidence";case"safety":return"valence/welfare/boundaries";case"counterpoint":return"significance/conflict";case"context":return"pattern/context";case"logic":return"logic/model/causality";case"novelty":return"possibility/imagination";case"memory":return"continuity/experience";case"left_hemisphere":return"logic/discrimination/constraint";case"right_hemisphere":return"imagination/association/expansion";case"front":return"integrated stream of consciousness";default:return"expression/interaction/action";}}
    private static String clip(String value,int max){String x=value==null?"":value.replace('\n',' ').replace('\r',' ').trim();return x.length()<=max?x:x.substring(0,max)+"…";}
    private static String signature(String a,String b,String c){try{MessageDigest d=MessageDigest.getInstance("SHA-256");byte[] x=d.digest((clip(a,3000)+"\n"+clip(b,5000)+"\n"+clip(c,900)).getBytes(StandardCharsets.UTF_8));StringBuilder s=new StringBuilder();for(int i=0;i<12;i++)s.append(String.format(Locale.ROOT,"%02x",x[i]));return s.toString();}catch(Exception e){return String.valueOf((a+"|"+b+"|"+c).hashCode());}}
}
