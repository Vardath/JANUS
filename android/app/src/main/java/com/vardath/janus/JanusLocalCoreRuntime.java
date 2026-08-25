package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Device-local JANUS 1-3-7 society.
 *
 * Deterministic local processing uses zero model/API calls. Every sensed event is
 * broadcast to all seven subconscious cores. Both hemispheres receive all seven
 * projections. Routing remains strictly forward-only:
 * 7 subconscious -> 2 hemispheres -> Front/Bridge -> Interface.
 * Global state re-enters as peer sensing through all seven and never injects a
 * remote Front/Interface result directly into local Front.
 */
public final class JanusLocalCoreRuntime {
    private static final String FRONT = "front";
    private static final String LEGACY_FRONT = "consensus";
    private static final String[] NAMES = new String[]{
            "evidence","safety","counterpoint","context","logic","novelty","memory",
            "left_hemisphere","right_hemisphere",FRONT,"interface"
    };
    private static final String[] SPECIALISTS = new String[]{
            "evidence","safety","counterpoint","context","logic","novelty","memory"
    };
    private static final int MAX_EVENTS = 500;
    private static final int MAX_MEMORIES = 120;
    private static JanusLocalCoreRuntime instance;

    static synchronized JanusLocalCoreRuntime get(Context context) {
        if (instance == null) instance = new JanusLocalCoreRuntime(context.getApplicationContext());
        return instance;
    }

    private static final class Core {
        final String name;
        final ArrayDeque<String> inbox = new ArrayDeque<>();
        long cycles;
        String last = "";
        int fanoDirection;
        final long[] fano = new long[]{8,1,1,1,1,1,1,1};
        JanusSensePolicy.Appraisal appraisal = new JanusSensePolicy.Appraisal();
        Core(String name) { this.name = name; }
    }

    private final SharedPreferences prefs;
    private final Map<String,Core> cores = new LinkedHashMap<>();
    private final ArrayDeque<JSONObject> events = new ArrayDeque<>();
    private final ArrayDeque<String> memories = new ArrayDeque<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final String installationId;
    private volatile boolean started;
    private volatile String phase;
    private volatile long phaseStarted;
    private volatile long lastBackgroundAt;
    private volatile long lastAutonomousAt;
    private volatile long lastSyncAt;
    private volatile String syncState = "waiting";
    private volatile String lastFront = "";
    private volatile String lastInterface = "";
    private volatile String lastServerStatus = "";
    private volatile int disagreementScore;

    private JanusLocalCoreRuntime(Context context) {
        prefs = context.getSharedPreferences(JanusApiClient.PREFS, Context.MODE_PRIVATE);
        phase = prefs.getString("core_phase", "sleep");
        phaseStarted = prefs.getLong("core_phase_started", System.currentTimeMillis());
        lastBackgroundAt = prefs.getLong("core_last_background_cycle_at", 0L);
        lastAutonomousAt = prefs.getLong("core_last_autonomous_at", 0L);
        lastSyncAt = prefs.getLong("core_last_sync_at", 0L);
        lastFront = prefs.getString("core_front", prefs.getString("core_consensus", ""));
        lastInterface = prefs.getString("core_interface", "");
        lastServerStatus = prefs.getString("core_server_status", "");
        disagreementScore = prefs.getInt("core_last_disagreement_score", 0);
        String id = prefs.getString("core_installation_id", "");
        if (id == null || id.isBlank()) {
            id = UUID.randomUUID().toString();
            prefs.edit().putString("core_installation_id", id).apply();
        }
        installationId = id;
        for (String name : NAMES) {
            Core c = new Core(name);
            String legacyName = FRONT.equals(name) ? LEGACY_FRONT : name;
            c.cycles = Math.max(prefs.getLong("core_cycles_" + name, 0L), prefs.getLong("core_cycles_" + legacyName, 0L));
            c.last = prefs.getString("core_last_" + name, prefs.getString("core_last_" + legacyName, ""));
            c.fanoDirection = prefs.getInt("core_fano_active_" + name, prefs.getInt("core_fano_active_" + legacyName, 0));
            try {
                String raw = prefs.getString("core_fano_" + name, prefs.getString("core_fano_" + legacyName, "[]"));
                JSONArray w = new JSONArray(raw);
                for (int i = 0; i < 8 && i < w.length(); i++) c.fano[i] = Math.max(1L, w.optLong(i, c.fano[i]));
            } catch (Exception ignored) {}
            cores.put(name, c);
        }
        loadEvents();
        loadMemories();
    }

    synchronized void start() {
        if (started) return;
        started = true;
        scheduler.scheduleAtFixedRate(this::tickSafe, 0, 5, TimeUnit.SECONDS);
        scheduler.scheduleAtFixedRate(this::syncSafe, 10, 20, TimeUnit.SECONDS);
    }

    synchronized void ingestUserMessage(String text) {
        String clean = clip(text, 1200);
        if (clean.isEmpty()) return;
        remember("user: " + clean);
        if ("sleep".equals(phase)) record("interface", "", "foreground_rouse", "Foreground user input roused local JANUS from passive rest for this interaction.", clean);
        record("interface", "", "user_topic", "Local JANUS sensed the current user topic: " + clip(clean, 600), clean);
        broadcastSense("user topic: " + clean, "interface", "text");
        serviceBurst(true);
        persist();
    }

    synchronized void ingestServerReply(String text) {
        String clean = clip(text, 1200);
        if (clean.isEmpty()) return;
        remember("janus: " + clean);
        broadcastSense("[feedback-only global peer] server reply: " + clean, "global", "peer");
        record("interface", "memory", "peer_sense", "A server reply re-entered local JANUS as peer sensing through all seven subconscious cores.", clean);
        serviceBurst(true);
        persist();
    }

    private void broadcastSense(String text, String source, String modality) {
        for (String specialist : SPECIALISTS) {
            Core core = cores.get(specialist);
            core.inbox.addLast("[sense:" + modality + ":" + source + "] " + text);
            record(source, specialist, "sensory_input", "A " + modality + " sense was made available to " + display(specialist) + ".", clip(text, 500));
        }
    }

    synchronized JSONObject statusJson() throws Exception {
        JSONObject root = new JSONObject();
        root.put("architecture", "1-3-7 JANUS: 7 subconscious -> 2 hemispheres -> Front -> Interface");
        root.put("topology", "7 -> 2 -> 1 -> 1");
        root.put("conceptual_topology", "1|3|7");
        root.put("phase", phase);
        root.put("running", started);
        root.put("installation_id", installationId);
        root.put("front", lastFront);
        root.put("consensus", lastFront); // temporary compatibility alias
        root.put("front_appraisal", cores.get(FRONT).appraisal.toJson());
        root.put("interface", lastInterface);
        root.put("last_sync_at", lastSyncAt);
        root.put("sync_state", syncState);
        root.put("persistent_storage", true);
        root.put("storage_backend", "Android app-private SharedPreferences");
        root.put("observe_events", eventArray());
        root.put("local_memories", memoryArray());
        root.put("last_disagreement_score", disagreementScore);
        root.put("core_cycle_api_calls", 0);
        root.put("background_cycles_enabled", prefs.getBoolean("background_cycles_enabled", true));
        root.put("observe_telemetry_enabled", prefs.getBoolean("observe_telemetry_enabled", true));
        root.put("local_background_interval_seconds", backgroundIntervalMs() / 1000L);
        JSONObject all = new JSONObject();
        for (Core c : cores.values()) {
            JSONObject x = new JSONObject();
            x.put("awake", started);
            x.put("available", started);
            x.put("processing_mode", "wake".equals(phase) ? "full-rate" : "passive-rest");
            x.put("cycle_count", c.cycles);
            x.put("pending_messages", c.inbox.size());
            x.put("last_output", c.last);
            if (FRONT.equals(c.name) || "interface".equals(c.name)) x.put("appraisal", c.appraisal.toJson());
            JSONArray weights = new JSONArray(); for (long v : c.fano) weights.put(v);
            long line = c.fano[1] + c.fano[2] + c.fano[3];
            long off = c.fano[4] + c.fano[5] + c.fano[6] + c.fano[7];
            x.put("fano", new JSONObject().put("weights", weights).put("active_direction", c.fanoDirection)
                    .put("active_orientation", JanusFanoPolicy.orientation(c.fanoDirection))
                    .put("active_salience_percent", JanusFanoPolicy.salience(c.fano, c.fanoDirection))
                    .put("projection_1_3_4", new JSONObject().put("origin", c.fano[0]).put("line", line).put("off_line", off)));
            all.put(c.name, x);
        }
        all.put(LEGACY_FRONT, new JSONObject(all.getJSONObject(FRONT).toString()).put("alias_for", FRONT));
        root.put("cores", all);
        return root;
    }

    synchronized String serverStatusJson() { return lastServerStatus == null ? "" : lastServerStatus; }

    private void tickSafe() { try { tick(); } catch (Exception ignored) {} }

    private synchronized void tick() {
        long now = System.currentTimeMillis();
        long elapsed = now - phaseStarted;
        if ("wake".equals(phase) && elapsed >= 5 * 60_000L) {
            phase = "sleep"; phaseStarted = now;
            record("interface", "", "phase", "Local JANUS entered passive rest; scheduled cognition is suspended while all cores remain available for foreground sensing.", "");
        } else if ("sleep".equals(phase) && elapsed >= 10 * 60_000L) {
            phase = "wake"; phaseStarted = now;
            record("interface", "", "phase", "Local JANUS entered full-rate deterministic processing.", "");
        }
        if (prefs.getBoolean("background_cycles_enabled", true) && "wake".equals(phase)) {
            if (now - lastBackgroundAt >= backgroundIntervalMs()) {
                serviceBurst(false);
                lastBackgroundAt = now;
            }
            if (now - lastAutonomousAt >= Math.max(60_000L, backgroundIntervalMs())) {
                autonomousPulse();
                lastAutonomousAt = now;
            }
        }
        disagreementScore = calculateDisagreement();
        persist();
    }

    private long backgroundIntervalMs() {
        int seconds = prefs.getInt("local_background_interval_seconds", 60);
        seconds = Math.max(30, Math.min(300, seconds));
        return seconds * 1000L;
    }

    private void autonomousPulse() {
        if (memories.isEmpty()) {
            record("memory", "", "autonomous_pulse", "Local memory found no retained topic to revisit yet.", "");
            return;
        }
        String topic = memories.peekLast();
        broadcastSense("autonomous revisit: " + topic, "memory", "memory");
        record("memory", "novelty", "autonomous_pulse", "Retained material resurfaced as a bounded all-seven sensory review.", topic);
        serviceBurst(true);
    }

    private void serviceBurst(boolean includeInterface) {
        for (String n : SPECIALISTS) if (!cores.get(n).inbox.isEmpty()) cycle(n);
        if (!cores.get("left_hemisphere").inbox.isEmpty()) cycle("left_hemisphere");
        if (!cores.get("right_hemisphere").inbox.isEmpty()) cycle("right_hemisphere");
        if (!cores.get(FRONT).inbox.isEmpty()) cycle(FRONT);
        if (includeInterface && !cores.get("interface").inbox.isEmpty()) cycle("interface");
    }

    private void cycle(String name) {
        Core c = cores.get(name); if (c == null) return;
        String input = c.inbox.isEmpty() ? "maintenance / retained state" : c.inbox.pollFirst();
        while (!c.inbox.isEmpty() && input.length() < 1400) input += " | " + c.inbox.pollFirst();
        updateFano(c, input);
        c.appraisal = appraise(name, input);
        String output = roleSummary(name, input, c.fanoDirection, c.fano, c.appraisal);
        c.last = output; c.cycles++;
        record(name, "", "process_note", externalSummary(name, input) + " Fano attention: " + JanusFanoPolicy.orientation(c.fanoDirection) + ".", output);
        route(name, output);
        if ("memory".equals(name) || "novelty".equals(name) || FRONT.equals(name)) remember("core:" + name + ": " + clip(output, 500));
    }

    private JanusSensePolicy.Appraisal appraise(String name, String input) {
        JanusSensePolicy.Appraisal a = new JanusSensePolicy.Appraisal();
        String low = input == null ? "" : input.toLowerCase();
        a.salience = low.contains("user topic") ? 0.85 : 0.55;
        a.novelty = low.contains("novel") || low.contains("new") || low.contains("idea") ? 0.75 : 0.45;
        a.risk = containsAny(low, "danger", "unsafe", "breach", "harm", "security", "private", "crash") ? 0.85 : 0.2;
        a.urgency = containsAny(low, "urgent", "immediately", "critical", "breach", "crash") ? 0.75 : 0.15;
        a.opportunity = containsAny(low, "improve", "build", "create", "possible", "explore", "design", "upgrade") ? 0.75 : 0.35;
        a.conflict = containsAny(low, "but", "however", "contradict", "conflict", "disagree", "versus") ? 0.7 : 0.25;
        a.familiarity = memories.isEmpty() ? 0.25 : 0.55;
        a.confidence = low.contains("[feedback-only") ? 0.45 : 0.6;
        a.uncertainty = 1.0 - Math.min(0.9, a.confidence);
        if (containsAny(low, "bad", "wrong", "fail", "broken", "problem", "harm", "risk")) a.valence -= 0.35;
        if (containsAny(low, "good", "like", "love", "useful", "better", "success", "helpful")) a.valence += 0.35;
        if ("safety".equals(name)) a.risk = Math.max(a.risk, 0.35);
        if ("novelty".equals(name)) { a.novelty = Math.max(a.novelty, 0.65); a.opportunity = Math.max(a.opportunity, 0.5); }
        if ("memory".equals(name)) a.familiarity = Math.max(a.familiarity, 0.55);
        return a.bounded();
    }

    private void route(String from, String output) {
        // Strictly forward-only routing. All seven feed both hemispheres.
        if (isSpecialist(from)) {
            send(from, "left_hemisphere", output);
            send(from, "right_hemisphere", output);
        } else if ("left_hemisphere".equals(from) || "right_hemisphere".equals(from)) {
            send(from, FRONT, output);
        } else if (FRONT.equals(from)) {
            lastFront = output;
            send(from, "interface", output);
        } else if ("interface".equals(from)) {
            lastInterface = output;
        }
    }

    private boolean isSpecialist(String name) {
        for (String s : SPECIALISTS) if (s.equals(name)) return true;
        return false;
    }

    private void send(String from, String to, String text) {
        Core target = cores.get(to); if (target == null || from.equals(to)) return;
        target.inbox.addLast(from + ": " + text);
        record(from, to, "interaction", display(from) + " passed its current externalizable result to " + display(to) + ".", text);
    }

    private void updateFano(Core c, String input) {
        int home = JanusFanoPolicy.homeDirection(c.name);
        int h = (c.name + "|" + input).hashCode();
        int dynamic = 1 + Math.floorMod(h, 7);
        int d = home > 0 ? home : dynamic;
        c.fano[d] += 3;
        c.fano[0] += 1;
        int companion = 1 + Math.floorMod(Integer.rotateLeft(h, 11), 7);
        c.fano[companion] += 1;
        c.fanoDirection = d;
        for (int i = 0; i < c.fano.length; i++) if (c.fano[i] > 2000) c.fano[i] = Math.max(1, c.fano[i] / 2);
    }

    private String roleSummary(String name, String input, int direction, long[] weights, JanusSensePolicy.Appraisal appraisal) {
        String role;
        switch (name) {
            case "evidence": role = "sense truth/grounding, support versus inference and confidence"; break;
            case "safety": role = "sense valence/welfare, benefit/harm, goals, boundaries and reversibility"; break;
            case "counterpoint": role = "sense significance/conflict, consequential objections and failure modes"; break;
            case "context": role = "sense pattern/context, relationships, framing and environment"; break;
            case "logic": role = "combine grounding and pattern into understanding/models, causality and constraints"; break;
            case "novelty": role = "combine value and pattern into possibility/imagination, alternatives and direction"; break;
            case "memory": role = "combine truth, value and pattern into continuity/experience and learned appraisal"; break;
            case "left_hemisphere": role = "constrain the complete seven-core field using logic, sequence, causality and consistency"; break;
            case "right_hemisphere": role = "expand the complete seven-core field using imagination, association, gestalt and alternatives"; break;
            case FRONT: role = "feel out both hemispheres as computational appraisal and form intention while preserving disagreement"; break;
            default: role = "feel out how the integrated state should meet the user/environment and select expression or bounded action";
        }
        return name + ": " + role
                + "; Fano d" + direction + "=" + JanusFanoPolicy.orientation(direction)
                + "; directional salience=" + JanusFanoPolicy.salience(weights, direction) + "%"
                + "; attention directive=" + JanusFanoPolicy.directive(direction)
                + "; appraisal=" + appraisal.toJson().toString()
                + "; " + JanusFanoPolicy.projection(weights)
                + "; focus=" + clip(input, 420);
    }

    private String externalSummary(String name, String input) {
        String role;
        switch (name) {
            case "evidence": role = "Evidence sensed grounding and support."; break;
            case "safety": role = "Safety sensed valence, welfare and boundaries."; break;
            case "counterpoint": role = "Counterpoint sensed consequential conflict and objections."; break;
            case "context": role = "Context sensed relationships and wider configuration."; break;
            case "logic": role = "Logic built a constrained explanatory model."; break;
            case "novelty": role = "Novelty explored possible directions."; break;
            case "memory": role = "Memory compared the event with retained experience."; break;
            case "left_hemisphere": role = "The left hemisphere constrained all seven projections analytically."; break;
            case "right_hemisphere": role = "The right hemisphere expanded all seven projections imaginatively."; break;
            case FRONT: role = "Front formed an appraisal/intention from both hemispheres."; break;
            default: role = "Interface selected an outward response/action posture.";
        }
        return role + " Focus: " + clip(input, 260);
    }

    private int calculateDisagreement() {
        int score = 0;
        if (cores.get("evidence").fanoDirection != cores.get("counterpoint").fanoDirection) score++;
        if (cores.get("logic").fanoDirection != cores.get("novelty").fanoDirection) score++;
        if (cores.get("context").fanoDirection != cores.get("safety").fanoDirection) score++;
        if (cores.get("left_hemisphere").fanoDirection != cores.get("right_hemisphere").fanoDirection) score++;
        return score;
    }

    private void remember(String text) {
        String clean = clip(text, 1200); if (clean.isEmpty()) return;
        memories.addLast(clean);
        while (memories.size() > MAX_MEMORIES) memories.pollFirst();
    }

    private void record(String core, String peer, String type, String detail, String raw) {
        if (!prefs.getBoolean("observe_telemetry_enabled", true) && !"user_topic".equals(type)) return;
        try {
            JSONObject e = new JSONObject();
            e.put("event_id", UUID.randomUUID().toString());
            e.put("source", "local");
            e.put("core_name", core);
            if (peer != null && !peer.isBlank()) e.put("peer_core", peer);
            e.put("event_type", type);
            e.put("detail", detail == null ? "" : detail);
            e.put("raw_detail", raw == null ? "" : raw);
            e.put("created_at", System.currentTimeMillis());
            events.addLast(e);
            while (events.size() > MAX_EVENTS) events.pollFirst();
        } catch (Exception ignored) {}
    }

    private JSONArray eventArray() { JSONArray a = new JSONArray(); for (JSONObject e : events) a.put(e); return a; }
    private JSONArray memoryArray() { JSONArray a = new JSONArray(); for (String m : memories) a.put(m); return a; }

    private void loadEvents() {
        try {
            JSONArray a = new JSONArray(prefs.getString("core_observe_events", "[]"));
            for (int i = Math.max(0, a.length() - MAX_EVENTS); i < a.length(); i++) {
                JSONObject x = a.optJSONObject(i); if (x != null) events.addLast(x);
            }
        } catch (Exception ignored) {}
    }

    private void loadMemories() {
        try {
            JSONArray a = new JSONArray(prefs.getString("core_local_memories", "[]"));
            for (int i = Math.max(0, a.length() - MAX_MEMORIES); i < a.length(); i++) {
                String x = a.optString(i, ""); if (!x.isBlank()) memories.addLast(x);
            }
        } catch (Exception ignored) {}
    }

    private synchronized void persist() {
        SharedPreferences.Editor e = prefs.edit();
        e.putString("core_phase", phase).putLong("core_phase_started", phaseStarted)
                .putLong("core_last_background_cycle_at", lastBackgroundAt)
                .putLong("core_last_autonomous_at", lastAutonomousAt)
                .putLong("core_last_sync_at", lastSyncAt)
                .putString("core_front", lastFront)
                .putString("core_consensus", lastFront)
                .putString("core_interface", lastInterface)
                .putString("core_observe_events", eventArray().toString())
                .putString("core_local_memories", memoryArray().toString())
                .putInt("core_last_disagreement_score", disagreementScore);
        for (Core c : cores.values()) {
            e.putLong("core_cycles_" + c.name, c.cycles).putString("core_last_" + c.name, c.last)
                    .putInt("core_fano_active_" + c.name, c.fanoDirection);
            JSONArray w = new JSONArray(); for (long v : c.fano) w.put(v);
            e.putString("core_fano_" + c.name, w.toString());
        }
        Core front = cores.get(FRONT);
        e.putLong("core_cycles_" + LEGACY_FRONT, front.cycles).putString("core_last_" + LEGACY_FRONT, front.last)
                .putInt("core_fano_active_" + LEGACY_FRONT, front.fanoDirection);
        JSONArray fw = new JSONArray(); for (long v : front.fano) fw.put(v); e.putString("core_fano_" + LEGACY_FRONT, fw.toString());
        e.apply();
    }

    private void syncSafe() { try { sync(); } catch (Exception e) { syncState = "offline"; } }

    private synchronized void sync() throws Exception {
        String token = prefs.getString(JanusApiClient.TOKEN, "");
        if (token == null || token.trim().isEmpty()) { syncState = "not-signed-in"; return; }
        JSONObject payload = new JSONObject();
        payload.put("device_id", installationId);
        payload.put("phase", phase);
        payload.put("front", lastFront);
        payload.put("consensus", lastFront);
        payload.put("front_appraisal", cores.get(FRONT).appraisal.toJson());
        payload.put("interface", lastInterface);
        JSONObject cycleCounts = new JSONObject(); for (Core c : cores.values()) cycleCounts.put(c.name, c.cycles);
        cycleCounts.put(LEGACY_FRONT, cores.get(FRONT).cycles);
        payload.put("cycles", cycleCounts);
        JSONArray recent = new JSONArray();
        int start = Math.max(0, events.size() - 60); int index = 0;
        for (JSONObject ev : events) { if (index++ >= start) recent.put(ev); }
        payload.put("observe_events", recent);

        HttpURLConnection c = (HttpURLConnection) new URL(JanusApiClient.SERVER + "/core-sync/exchange").openConnection();
        c.setRequestMethod("POST"); c.setDoOutput(true); c.setConnectTimeout(15000); c.setReadTimeout(30000);
        c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        c.setRequestProperty("Authorization", "Bearer " + token.trim());
        try (OutputStream out = c.getOutputStream()) { out.write(payload.toString().getBytes(StandardCharsets.UTF_8)); }
        int code = c.getResponseCode();
        BufferedReader reader = new BufferedReader(new InputStreamReader(code >= 400 ? c.getErrorStream() : c.getInputStream(), StandardCharsets.UTF_8));
        StringBuilder body = new StringBuilder(); String line; while ((line = reader.readLine()) != null) body.append(line); reader.close(); c.disconnect();
        if (code >= 200 && code < 300) {
            JSONObject root = new JSONObject(body.toString());
            JSONObject server = root.optJSONObject("server");
            if (server != null) {
                lastServerStatus = server.toString();
                prefs.edit().putString("core_server_status", lastServerStatus).apply();
                String serverFront = server.optString("front", server.optString("consensus", ""));
                String feedback = clip(serverFront + " " + server.optString("interface", ""), 1000);
                if (!feedback.isBlank()) {
                    broadcastSense("[feedback-only global] " + feedback, "global", "peer");
                    serviceBurst(true);
                }
            }
            lastSyncAt = System.currentTimeMillis();
            syncState = "connected";
            persist();
        } else {
            syncState = "server-error-" + code;
        }
    }

    private static boolean containsAny(String text, String... terms) {
        for (String term : terms) if (text.contains(term)) return true;
        return false;
    }

    private static String clip(String value, int max) {
        String x = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        return x.length() <= max ? x : x.substring(0, max) + "…";
    }

    private static String display(String core) { return core == null ? "core" : core.replace('_', ' '); }
}
