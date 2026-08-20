package com.vardath.janus;

import android.content.Context;
import android.content.SharedPreferences;

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

/** Lightweight zero-API-cost 11-core runtime for the Android client process. */
public final class JanusLocalCoreRuntime {
    private static final String SERVER = "https://janus-global-core.onrender.com";
    private static final String[] NAMES = {"evidence","logic","counterpoint","context","memory","safety","novelty","left_hemisphere","right_hemisphere","consensus","interface"};
    private static JanusLocalCoreRuntime instance;

    static synchronized JanusLocalCoreRuntime get(Context context) {
        if (instance == null) instance = new JanusLocalCoreRuntime(context.getApplicationContext());
        return instance;
    }

    private static final class Core {
        final String name;
        long cycles;
        final ArrayDeque<String> inbox = new ArrayDeque<>();
        String last = "";
        Core(String name) { this.name = name; }
    }

    private final Context context;
    private final SharedPreferences prefs;
    private final Map<String,Core> cores = new LinkedHashMap<>();
    private final ScheduledExecutorService executor = Executors.newScheduledThreadPool(2);
    private volatile boolean started;
    private volatile String phase = "sleep";
    private volatile long phaseStarted = System.currentTimeMillis();
    private volatile String lastConsensus = "";
    private volatile String lastInterface = "";
    private final String installationId;

    private JanusLocalCoreRuntime(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences("janus", Context.MODE_PRIVATE);
        for (String name : NAMES) {
            Core c = new Core(name);
            c.cycles = prefs.getLong("core_cycles_" + name, 0);
            c.last = prefs.getString("core_last_" + name, "");
            cores.put(name, c);
        }
        String id = prefs.getString("core_installation_id", "");
        if (id == null || id.isEmpty()) {
            id = UUID.randomUUID().toString();
            prefs.edit().putString("core_installation_id", id).apply();
        }
        installationId = id;
        lastConsensus = prefs.getString("core_consensus", "");
        lastInterface = prefs.getString("core_interface", "");
    }

    synchronized void start() {
        if (started) return;
        started = true;
        executor.scheduleAtFixedRate(this::tickSafe, 0, 5, TimeUnit.SECONDS);
        executor.scheduleAtFixedRate(this::syncSafe, 20, 60, TimeUnit.SECONDS);
    }

    private void tickSafe() { try { tick(); } catch (Exception ignored) {} }
    private synchronized void tick() {
        long now = System.currentTimeMillis();
        long elapsed = now - phaseStarted;
        if ("wake".equals(phase) && elapsed >= 5 * 60_000L) { phase="sleep"; phaseStarted=now; persist(); return; }
        if ("sleep".equals(phase) && elapsed >= 10 * 60_000L) { phase="wake"; phaseStarted=now; }
        if (!"wake".equals(phase)) return;

        for (String name : NAMES) {
            Core c = cores.get(name);
            String thought = think(c);
            c.last = thought;
            c.cycles++;
            route(name, thought);
        }
        persist();
    }

    private String think(Core c) {
        if (c.inbox.isEmpty()) return c.name + ": idle self-check complete";
        StringBuilder b = new StringBuilder(); int n=0;
        while (!c.inbox.isEmpty() && n < 4) { if (n++>0) b.append(" | "); b.append(c.inbox.pollLast()); }
        c.inbox.clear();
        if ("left_hemisphere".equals(c.name)) return "left_hemisphere: analytic synthesis; " + b;
        if ("right_hemisphere".equals(c.name)) return "right_hemisphere: contextual/associative synthesis; " + b;
        if ("consensus".equals(c.name)) return "consensus: integrated reading; " + b;
        if ("interface".equals(c.name)) return "interface: user-facing interpretation; " + b;
        return c.name + ": reviewed peer inputs; " + b;
    }

    private void send(String from, String to, String text) {
        Core target = cores.get(to); if (target != null && !from.equals(to)) target.inbox.addLast(from + ": " + text);
    }
    private void route(String from, String text) {
        if (Arrays.asList("evidence","logic","counterpoint").contains(from)) send(from,"left_hemisphere",text);
        else if (Arrays.asList("context","memory","novelty").contains(from)) send(from,"right_hemisphere",text);
        else if ("safety".equals(from)) { send(from,"left_hemisphere",text); send(from,"right_hemisphere",text); send(from,"consensus",text); }
        else if ("left_hemisphere".equals(from)) { send(from,"right_hemisphere",text); send(from,"consensus",text); }
        else if ("right_hemisphere".equals(from)) { send(from,"left_hemisphere",text); send(from,"consensus",text); }
        else if ("consensus".equals(from)) { lastConsensus=text; send(from,"interface",text); send(from,"left_hemisphere",text); send(from,"right_hemisphere",text); }
        else if ("interface".equals(from)) { lastInterface=text; send(from,"consensus",text); }
    }

    private void persist() {
        SharedPreferences.Editor e = prefs.edit().putString("core_phase",phase).putString("core_consensus",lastConsensus).putString("core_interface",lastInterface);
        for (Core c : cores.values()) e.putLong("core_cycles_"+c.name,c.cycles).putString("core_last_"+c.name,c.last);
        e.apply();
    }

    private JSONObject summary() throws Exception {
        JSONObject cycles = new JSONObject(); for (Core c : cores.values()) cycles.put(c.name,c.cycles);
        return new JSONObject().put("device_id",installationId).put("phase",phase).put("consensus",lastConsensus).put("interface",lastInterface).put("cycles",cycles);
    }

    private void syncSafe() { try { sync(); } catch (Exception ignored) {} }
    private void sync() throws Exception {
        String token = prefs.getString("access_token", "");
        if (token == null || token.trim().isEmpty()) return;
        HttpURLConnection c = (HttpURLConnection)new URL(SERVER + "/core-sync/exchange").openConnection();
        c.setRequestMethod("POST"); c.setDoOutput(true); c.setConnectTimeout(15000); c.setReadTimeout(30000);
        c.setRequestProperty("Content-Type","application/json"); c.setRequestProperty("Authorization","Bearer "+token.trim());
        byte[] body = summary().toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream os = c.getOutputStream()) { os.write(body); }
        int code=c.getResponseCode();
        BufferedReader r=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),StandardCharsets.UTF_8));
        StringBuilder b=new StringBuilder(); String line; while((line=r.readLine())!=null)b.append(line); r.close();
        if (code<400) {
            JSONObject server = new JSONObject(b.toString()).optJSONObject("server");
            if (server != null) {
                String remoteConsensus=server.optString("consensus","");
                String remoteInterface=server.optString("interface","");
                if (!remoteConsensus.isEmpty()) send("interface","consensus","global: "+remoteConsensus);
                if (!remoteInterface.isEmpty()) send("consensus","interface","global: "+remoteInterface);
            }
        }
    }
}
