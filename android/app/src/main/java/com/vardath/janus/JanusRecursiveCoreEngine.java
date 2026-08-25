package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Internal recursive cognition for each of the eleven Android top-level cores.
 *
 * This is not a second 11-core society. Each Node below is the JANUS/Fano processor
 * living inside the corresponding outer core. Every node retains all seven internal
 * faculties, receives bounded peer conclusions from the other outer cores, revises,
 * and can receive its own foreground AI counsel returned by the global model batch.
 * Background recursion is deterministic and makes zero network/model calls.
 */
public final class JanusRecursiveCoreEngine {
    private static final String PREFS = "janus_recursive_core_engine_v1";
    private static final String STATE_KEY = "states";
    private static final String[] NAMES = new String[]{
            "evidence","safety","counterpoint","context","logic","novelty","memory",
            "left_hemisphere","right_hemisphere","front","interface"
    };
    private static final String[] FACULTY = new String[]{
            "reference","truth","valence","significance","pattern","understanding","possibility","continuity"
    };
    private static final int[][] BIASES = new int[][]{
            {0,0,0,0,0,0,0,0},
            {0,5,0,1,0,2,0,0}, // evidence
            {0,0,5,2,0,0,0,1}, // safety
            {0,2,2,5,0,1,0,0}, // counterpoint
            {0,0,0,0,5,0,2,1}, // context
            {0,2,0,1,2,5,0,0}, // logic
            {0,0,2,0,2,1,5,0}, // novelty
            {0,1,1,0,1,1,0,5}, // memory
            {0,3,0,2,0,5,0,1}, // left
            {0,0,1,0,4,0,5,2}, // right
            {0,0,3,4,0,2,1,3}, // front
            {0,2,3,3,0,2,2,1}, // interface
    };

    private static JanusRecursiveCoreEngine instance;

    static synchronized JanusRecursiveCoreEngine get(Context context) {
        if (instance == null) instance = new JanusRecursiveCoreEngine(context.getApplicationContext());
        return instance;
    }

    static synchronized void clearInstance() {
        if (instance != null) instance.stop();
        instance = null;
    }

    private static final class Node {
        final String name;
        final long[] weights = new long[]{8,1,1,1,1,1,1,1};
        int active;
        long cycles;
        long revisions;
        long peerTurns;
        String conclusion = "";
        String aiCounsel = "";
        Node(String name) { this.name = name; }
    }

    private final SharedPreferences prefs;
    private final Map<String,Node> nodes = new LinkedHashMap<>();
    private ScheduledExecutorService scheduler;
    private JanusLocalCoreRuntime runtime;
    private volatile boolean started;

    private JanusRecursiveCoreEngine(Context context) {
        prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        for (String name : NAMES) nodes.put(name, new Node(name));
        restore();
    }

    synchronized void start(JanusLocalCoreRuntime localRuntime) {
        runtime = localRuntime;
        if (started) return;
        started = true;
        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(this::backgroundSafe, 15, 30, TimeUnit.SECONDS);
    }

    synchronized void stop() {
        started = false;
        if (scheduler != null) scheduler.shutdownNow();
        scheduler = null;
        persist();
    }

    synchronized JSONObject foreground(String userMessage) {
        processSociety("foreground user sense: " + clip(userMessage, 1400));
        return snapshot();
    }

    synchronized void sense(String modality, String source, String content) {
        processSociety("sense:" + clip(modality, 30) + ":" + clip(source, 80) + " " + clip(content, 1200));
    }

    synchronized void applyAiCounsel(JSONObject counsel) {
        if (counsel == null) return;
        for (String name : NAMES) {
            String text = counsel.optString(name, "").trim();
            if (text.isEmpty()) continue;
            Node n = nodes.get(name);
            n.aiCounsel = clip(text, 900);
            n.revisions++;
            // AI counsel belongs to that core first; peers see only its bounded conclusion.
            think(n, "AI counsel to this core: " + n.aiCounsel, peerDigest(name));
        }
        processPeerRevision("AI counsel peer revision");
        persist();
    }

    synchronized JSONObject snapshot() {
        JSONObject root = new JSONObject();
        try {
            root.put("recursive_core_engine", true);
            root.put("core_count", 11);
            root.put("internal_fano_positions_per_core", 7);
            root.put("background_model_calls", 0);
            root.put("ai_strategy", "per-core bounded counsel supplied by one governed foreground society model call");
            JSONObject cores = new JSONObject();
            for (Node n : nodes.values()) cores.put(n.name, nodeJson(n));
            root.put("cores", cores);
        } catch (Exception ignored) {}
        return root;
    }

    private void backgroundSafe() {
        try {
            synchronized (this) {
                if (!started) return;
                String base = "background retained outer-core state";
                try {
                    if (runtime != null) {
                        JSONObject status = runtime.statusJson();
                        JSONObject outer = status.optJSONObject("cores");
                        if (outer != null) {
                            StringBuilder b = new StringBuilder();
                            for (String name : NAMES) {
                                JSONObject c = outer.optJSONObject(name);
                                if (c == null) continue;
                                String last = c.optString("last_output", "").trim();
                                if (!last.isEmpty()) b.append(name).append(':').append(clip(last, 160)).append(" | ");
                            }
                            if (b.length() > 0) base = b.toString();
                        }
                    }
                } catch (Exception ignored) {}
                processSociety(base);
            }
        } catch (Exception ignored) {}
    }

    private void processSociety(String stimulus) {
        // Round one: each outer core independently runs a full seven-position JANUS readout.
        for (Node n : nodes.values()) think(n, stimulus, "");
        // Round two: every core reacts to the bounded conclusions of the other ten.
        processPeerRevision("peer response");
        persist();
    }

    private void processPeerRevision(String reason) {
        Map<String,String> initial = new LinkedHashMap<>();
        for (Node n : nodes.values()) initial.put(n.name, n.conclusion);
        for (Node n : nodes.values()) {
            StringBuilder peers = new StringBuilder();
            for (Map.Entry<String,String> e : initial.entrySet()) {
                if (e.getKey().equals(n.name) || e.getValue().isBlank()) continue;
                if (peers.length() > 0) peers.append(" | ");
                peers.append(e.getKey()).append(':').append(clip(e.getValue(), 120));
            }
            n.peerTurns += Math.max(0, initial.size() - 1);
            n.revisions++;
            think(n, reason, peers.toString());
        }
    }

    private String peerDigest(String forName) {
        StringBuilder b = new StringBuilder();
        for (Node n : nodes.values()) {
            if (n.name.equals(forName) || n.conclusion.isBlank()) continue;
            if (b.length() > 0) b.append(" | ");
            b.append(n.name).append(':').append(clip(n.conclusion, 120));
        }
        return b.toString();
    }

    private void think(Node n, String content, String peerText) {
        String low = (content + " " + peerText).toLowerCase(Locale.ROOT);
        int[] scores = new int[8];
        String[][] cues = new String[][]{
                {},
                {"evidence","source","fact","true","false","claim","support","verify","confidence"},
                {"want","prefer","good","bad","harm","benefit","safe","unsafe","privacy","boundary","goal"},
                {"important","urgent","risk","conflict","contradict","however","but","failure","consequence"},
                {"pattern","context","relationship","similar","structure","system","environment","analogy"},
                {"because","cause","logic","model","therefore","constraint","explain","predict","consistent"},
                {"could","might","possible","idea","alternative","imagine","create","explore","option","future"},
                {"remember","before","again","history","previous","continuity","memory","learned","past"}
        };
        int biasRow = indexOf(n.name) + 1;
        for (int d = 1; d <= 7; d++) {
            int hits = 0;
            for (String cue : cues[d]) if (low.contains(cue)) hits++;
            int score = 2 + hits * 2 + BIASES[biasRow][d];
            scores[d] = score;
            n.weights[d] += Math.max(1, score);
        }
        n.weights[0]++;
        int active = 1;
        for (int d = 2; d <= 7; d++) if (scores[d] > scores[active]) active = d;
        n.active = active;
        n.cycles++;
        String peerClause = peerText == null || peerText.isBlank() ? "" : "; revised against peer-core conclusions";
        String aiClause = n.aiCounsel.isBlank() ? "" : "; own AI counsel retained";
        n.conclusion = clip(n.name + " ran its complete internal JANUS/Fano structure; outer disposition="
                + role(n.name) + "; dominant internal d" + active + " " + FACULTY[active]
                + peerClause + aiClause + "; focus=" + content, 1300);
        for (int i = 0; i < 8; i++) if (n.weights[i] > 5000) n.weights[i] = Math.max(1, n.weights[i] / 2);
    }

    private JSONObject nodeJson(Node n) throws Exception {
        JSONObject x = new JSONObject();
        x.put("recursive_janus", true);
        x.put("ai_capable", true);
        x.put("outer_disposition", role(n.name));
        x.put("active_direction", n.active);
        x.put("active_faculty", n.active >= 0 && n.active < FACULTY.length ? FACULTY[n.active] : "reference");
        JSONArray w = new JSONArray(); for (long v : n.weights) w.put(v); x.put("weights", w);
        x.put("cycles", n.cycles);
        x.put("revision_count", n.revisions);
        x.put("peer_turn_count", n.peerTurns);
        x.put("conclusion", n.conclusion);
        x.put("ai_last", n.aiCounsel);
        x.put("projection_1_3_4", new JSONObject().put("origin", n.weights[0])
                .put("line", n.weights[1]+n.weights[2]+n.weights[3])
                .put("off_line", n.weights[4]+n.weights[5]+n.weights[6]+n.weights[7]));
        return x;
    }

    private void persist() {
        try { prefs.edit().putString(STATE_KEY, snapshot().toString()).apply(); }
        catch (Exception ignored) {}
    }

    private void restore() {
        try {
            JSONObject root = new JSONObject(prefs.getString(STATE_KEY, "{}"));
            JSONObject cores = root.optJSONObject("cores");
            if (cores == null) return;
            for (Node n : nodes.values()) {
                JSONObject x = cores.optJSONObject(n.name); if (x == null) continue;
                JSONArray w = x.optJSONArray("weights");
                if (w != null) for (int i=0;i<8 && i<w.length();i++) n.weights[i]=Math.max(1,w.optLong(i,n.weights[i]));
                n.active=x.optInt("active_direction",0); n.cycles=x.optLong("cycles",0);
                n.revisions=x.optLong("revision_count",0); n.peerTurns=x.optLong("peer_turn_count",0);
                n.conclusion=x.optString("conclusion",""); n.aiCounsel=x.optString("ai_last","");
            }
        } catch (Exception ignored) {}
    }

    static void clearAccountBoundState(Context context) {
        context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply();
        clearInstance();
    }

    private static int indexOf(String name) {
        for (int i=0;i<NAMES.length;i++) if (NAMES[i].equals(name)) return i;
        return 0;
    }

    private static String role(String name) {
        switch (name) {
            case "evidence": return "grounding/evidence";
            case "safety": return "valence/welfare/boundaries";
            case "counterpoint": return "significance/conflict";
            case "context": return "pattern/context";
            case "logic": return "logic/model/causality";
            case "novelty": return "possibility/imagination";
            case "memory": return "continuity/experience";
            case "left_hemisphere": return "logic/discrimination/constraint";
            case "right_hemisphere": return "imagination/association/expansion";
            case "front": return "integrated appraisal/intention";
            default: return "expression/interaction/action";
        }
    }

    private static String clip(String value, int max) {
        String x = value == null ? "" : value.replace('\n',' ').replace('\r',' ').trim();
        return x.length() <= max ? x : x.substring(0,max) + "…";
    }
}
