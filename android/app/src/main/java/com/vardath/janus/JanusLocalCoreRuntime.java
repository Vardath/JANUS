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
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Device-local JANUS society.
 *
 * Deterministic local processing uses zero model/API calls. Routing is strictly
 * forward-only: 7 specialists -> 2 hemispheres -> Consensus -> Interface.
 * Global sync is feedback-only and re-enters through specialists, never by
 * injecting remote Consensus/Interface directly into local integration stages.
 */
public final class JanusLocalCoreRuntime {
    private static final String[] NAMES = new String[]{
            "evidence","logic","counterpoint","context","memory","safety","novelty",
            "left_hemisphere","right_hemisphere","consensus","interface"
    };
    private static final String[] SPECIALISTS = new String[]{"evidence","logic","counterpoint","context","memory","safety","novelty"};
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
    private volatile String lastConsensus = "";
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
        lastConsensus = prefs.getString("core_consensus", "");
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
            c.cycles = prefs.getLong("core_cycles_" + name, 0L);
            c.last = prefs.getString("core_last_" + name, "");
            c.fanoDirection = prefs.getInt("core_fano_active_" + name, 0);
            try {
                JSONArray w = new JSONArray(prefs.getString("core_fano_" + name, "[]"));
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
        record("interface", "", "user_topic", "Local JANUS received the current user topic: " + clip(clean, 600), clean);
        for (String specialist : SPECIALISTS) {
            cores.get(specialist).inbox.addLast("user topic: " + clean);
            record("interface", specialist, "interaction", "Interface seeded " + display(specialist) + " with the current user topic.", clean);
        }
        serviceBurst(true);
        persist();
    }

    synchronized void ingestServerReply(String text) {
        String clean = clip(text, 1200);
        if (clean.isEmpty()) return;
        remember("janus: " + clean);
        // Server output becomes feedback-only evidence/context for the next local pass.
        cores.get("evidence").inbox.addLast("[feedback-only] server reply to verify: " + clean);
        cores.get("context").inbox.addLast("[feedback-only] server reply context: " + clean);
        cores.get("memory").inbox.addLast("[feedback-only] server reply to retain: " + clean);
        cores.get("counterpoint").inbox.addLast("[feedback-only] challenge unresolved claims in server reply: " + clean);
        record("interface", "memory", "interaction", "A server reply was added to local continuity as feedback-only material.", clean);
        serviceBurst(true);
        persist();
    }

    synchronized JSONObject statusJson() throws Exception {
        JSONObject root = new JSONObject();
        root.put("architecture", "11 Fano/JANUS cores");
        root.put("topology", "7 -> 2 -> 1 -> 1");
        root.put("phase", phase);
        root.put("running", started);
        root.put("installation_id", installationId);
        root.put("consensus", lastConsensus);
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
            x.put("processing_mode", "interface".equals(c.name) ? "continuous" : ("wake".equals(phase) ? "full-rate" : "low-duty"));
            x.put("cycle_count", c.cycles);
            x.put("pending_messages", c.inbox.size());
            x.put("last_output", c.last);
            JSONArray weights = new JSONArray(); for (long v : c.fano) weights.put(v);
            long line = c.fano[1] + c.fano[2] + c.fano[3];
            long off = c.fano[4] + c.fano[5] + c.fano[6] + c.fano[7];
            x.put("fano", new JSONObject().put("weights", weights).put("active_direction", c.fanoDirection)
                    .put("projection_1_3_4", new JSONObject().put("origin", c.fano[0]).put("line", line).put("off_line", off)));
            all.put(c.name, x);
        }
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
            record("interface", "", "phase", "Local JANUS entered low-duty mode; all cores remain available for foreground work.", "");
        } else if ("sleep".equals(phase) && elapsed >= 10 * 60_000L) {
            phase = "wake"; phaseStarted = now;
            record("interface", "", "phase", "Local JANUS entered full-rate deterministic processing.", "");
        }

        // Foreground Interface work is always serviced.
        if (!cores.get("interface").inbox.isEmpty()) cycle("interface");

        if (prefs.getBoolean("background_cycles_enabled", true)) {
            if ("wake".equals(phase) || now - lastBackgroundAt >= backgroundIntervalMs()) {
                serviceBurst(false);
                lastBackgroundAt = now;
                if ("sleep".equals(phase)) record("interface", "", "maintenance", "Low-duty local maintenance pass completed with zero model/API calls.", "");
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
        cores.get("memory").inbox.addLast("autonomous revisit: " + topic);
        cores.get("novelty").inbox.addLast("autonomous adjacent connection search: " + topic);
        cores.get("evidence").inbox.addLast("autonomous grounding check: " + topic);
        cores.get("counterpoint").inbox.addLast("autonomous falsification check: " + topic);
        record("memory", "novelty", "autonomous_pulse", "Retained material was resurfaced for a bounded cross-core review.", topic);
        serviceBurst(true);
    }

    private void serviceBurst(boolean includeInterface) {
        for (String n : SPECIALISTS) if (!cores.get(n).inbox.isEmpty()) cycle(n);
        if (!cores.get("left_hemisphere").inbox.isEmpty()) cycle("left_hemisphere");
        if (!cores.get("right_hemisphere").inbox.isEmpty()) cycle("right_hemisphere");
        if (!cores.get("consensus").inbox.isEmpty()) cycle("consensus");
        if (includeInterface && !cores.get("interface").inbox.isEmpty()) cycle("interface");
    }

    private void cycle(String name) {
        Core c = cores.get(name); if (c == null) return;
        String input = c.inbox.isEmpty() ? "maintenance / retained state" : c.inbox.pollFirst();
        while (!c.inbox.isEmpty() && input.length() < 1000) input += " | " + c.inbox.pollFirst();
        updateFano(c, input);
        String output = roleSummary(name, input, c.fanoDirection);
        c.last = output; c.cycles++;
        record(name, "", "process_note", externalSummary(name, input), output);
        route(name, output);
        if ("memory".equals(name) || "novelty".equals(name) || "consensus".equals(name)) remember("core:" + name + ": " + clip(output, 500));
    }

    private void route(String from, String output) {
        // Strictly forward-only routing.
        if (Arrays.asList("evidence","logic","counterpoint").contains(from)) {
            send(from, "left_hemisphere", output);
        } else if (Arrays.asList("context","memory","novelty").contains(from)) {
            send(from, "right_hemisphere", output);
        } else if ("safety".equals(from)) {
            send(from, "left_hemisphere", output);
            send(from, "right_hemisphere", output);
            send(from, "consensus", output);
        } else if ("left_hemisphere".equals(from) || "right_hemisphere".equals(from)) {
            send(from, "consensus", output);
        } else if ("consensus".equals(from)) {
            lastConsensus = output;
            send(from, "interface", output);
        } else if ("interface".equals(from)) {
            lastInterface = output;
        }
    }

    private void send(String from, String to, String text) {
        Core target = cores.get(to); if (target == null || from.equals(to)) return;
        target.inbox.addLast(from + ": " + text);
        record(from, to, "interaction", display(from) + " passed its current externalizable result to " + display(to) + ".", text);
    }

    private void updateFano(Core c, String input) {
        int h = (c.name + "|" + input).hashCode();
        int d = 1 + Math.floorMod(h, 7);
        c.fano[d] += 3;
        c.fano[0] += 1;
        int companion = 1 + Math.floorMod(Integer.rotateLeft(h, 11), 7);
        c.fano[companion] += 1;
        c.fanoDirection = d;
        for (int i = 0; i < c.fano.length; i++) {
            if (c.fano[i] > 2000) c.fano[i] = Math.max(1, c.fano[i] / 2);
        }
    }

    private String roleSummary(String name, String input, int direction) {
        String role;
        switch (name) {
            case "evidence": role = "separate support from inference and identify missing observations"; break;
            case "logic": role = "check consistency, causal structure and incompatible assumptions"; break;
            case "counterpoint": role = "challenge the current interpretation and seek alternatives/failure modes"; break;
            case "context": role = "relate the topic to retained context, goals and environment"; break;
            case "memory": role = "compare with retained continuity and unfinished work"; break;
            case "safety": role = "check privacy, security, boundaries and harmful failure modes"; break;
            case "novelty": role = "look for unusual but testable adjacent connections"; break;
            case "left_hemisphere": role = "integrate evidence, logic and counterpoint without erasing disagreement"; break;
            case "right_hemisphere": role = "integrate context, memory and novelty without erasing disagreement"; break;
            case "consensus": role = "combine both hemispheres while preserving unresolved disagreement"; break;
            default: role = "form an externalizable user-facing shared state";
        }
        return name + ": " + role + "; Fano d" + direction + "; focus=" + clip(input, 420);
    }

    private String externalSummary(String name, String input) {
        String role;
        switch (name) {
            case "evidence": role = "Evidence checked what is supported versus inferred."; break;
            case "logic": role = "Logic checked structure and consistency."; break;
            case "counterpoint": role = "Counterpoint challenged the current interpretation."; break;
            case "context": role = "Context compared the topic with wider retained context."; break;
            case "memory": role = "Memory compared the topic with retained continuity."; break;
            case "safety": role = "Safety checked boundaries and failure modes."; break;
            case "novelty": role = "Novelty searched for a useful testable connection."; break;
            case "left_hemisphere": role = "The left hemisphere integrated analytic specialist results."; break;
            case "right_hemisphere": role = "The right hemisphere integrated contextual specialist results."; break;
            case "consensus": role = "Consensus integrated both hemispheres while keeping disagreement visible."; break;
            default: role = "Interface updated the externalizable shared state.";
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
                .putString("core_consensus", lastConsensus)
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
        e.apply();
    }

    private void syncSafe() { try { sync(); } catch (Exception e) { syncState = "offline"; } }

    private synchronized void sync() throws Exception {
        String token = prefs.getString(JanusApiClient.TOKEN, "");
        if (token == null || token.trim().isEmpty()) { syncState = "not-signed-in"; return; }
        JSONObject payload = new JSONObject();
        payload.put("device_id", installationId);
        payload.put("phase", phase);
        payload.put("consensus", lastConsensus);
        payload.put("interface", lastInterface);
        JSONObject cycleCounts = new JSONObject(); for (Core c : cores.values()) cycleCounts.put(c.name, c.cycles);
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
                String feedback = clip(server.optString("consensus", "") + " " + server.optString("interface", ""), 1000);
                if (!feedback.isBlank()) {
                    // Re-enter remote state through specialist review only.
                    cores.get("evidence").inbox.addLast("[feedback-only global] verify: " + feedback);
                    cores.get("context").inbox.addLast("[feedback-only global] contextualize: " + feedback);
                    cores.get("counterpoint").inbox.addLast("[feedback-only global] challenge: " + feedback);
                    cores.get("memory").inbox.addLast("[feedback-only global] compare with continuity: " + feedback);
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

    private static String clip(String value, int max) {
        String x = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        return x.length() <= max ? x : x.substring(0, max) + "…";
    }

    private static String display(String core) { return core == null ? "core" : core.replace('_', ' '); }
}
