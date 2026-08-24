package com.vardath.janus;

import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Central policy for authenticated Android API paths.
 *
 * server_v2 derives account ownership from the bearer token. Legacy username/profile_id
 * query parameters therefore add noise and can create misleading security assumptions.
 * This helper strips only those identity-like query parameters from authenticated,
 * account-owned GET paths while preserving operational filters such as limit and mode.
 */
public final class JanusRoutePolicy {
    private JanusRoutePolicy() {}

    public static String sanitizeAuthenticatedPath(String path) {
        if (path == null || path.isBlank() || path.indexOf('?') < 0) return path;
        int q = path.indexOf('?');
        String base = path.substring(0, q);
        String query = path.substring(q + 1);
        if (!isAccountOwnedPath(base)) return path;

        List<String> keep = new ArrayList<>();
        for (String pair : query.split("&")) {
            if (pair == null || pair.isBlank()) continue;
            int eq = pair.indexOf('=');
            String rawKey = eq >= 0 ? pair.substring(0, eq) : pair;
            String key;
            try { key = URLDecoder.decode(rawKey, StandardCharsets.UTF_8).trim().toLowerCase(); }
            catch (Exception e) { key = rawKey.trim().toLowerCase(); }
            if ("username".equals(key) || "profile_id".equals(key) || "user".equals(key)) continue;
            keep.add(pair);
        }
        return keep.isEmpty() ? base : base + "?" + String.join("&", keep);
    }

    public static boolean isAccountOwnedPath(String base) {
        if (base == null) return false;
        return base.startsWith("/desktop/messages")
                || base.startsWith("/desktop/core-observe")
                || base.startsWith("/desktop/runtime-cores")
                || base.startsWith("/desktop/memory")
                || base.startsWith("/desktop/activity")
                || base.startsWith("/research/")
                || base.startsWith("/artifacts")
                || base.startsWith("/maintenance/");
    }
}
