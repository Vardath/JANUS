package com.vardath.janus;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Immutable Chat response presentation model for JANUS Android v0.92. */
public final class JanusChatPresentation {
    public static final class Source {
        public final String title;
        public final String url;
        public final String domain;

        Source(String title, String url) {
            this.title = title == null || title.isBlank() ? "Source" : title.trim();
            this.url = url == null ? "" : url.trim();
            this.domain = domainOf(this.url);
        }
    }

    public final String reply;
    public final List<Source> sources;
    public final JSONObject generatedImage;

    private JanusChatPresentation(String reply, List<Source> sources, JSONObject generatedImage) {
        this.reply = reply == null ? "" : reply;
        this.sources = Collections.unmodifiableList(sources);
        this.generatedImage = generatedImage;
    }

    public static JanusChatPresentation fromResponse(JSONObject response, String fallback) {
        String reply = response.optString("reply", response.optString("response", fallback == null ? "" : fallback));
        JSONArray raw = response.optJSONArray("sources");
        List<Source> sources = new ArrayList<>();
        if (raw != null) {
            for (int i = 0; i < Math.min(8, raw.length()); i++) {
                Object item = raw.opt(i);
                if (item instanceof JSONObject) {
                    JSONObject s = (JSONObject) item;
                    String url = s.optString("url", "");
                    sources.add(new Source(s.optString("title", url.isBlank() ? "Source" : url), url));
                } else if (item != null) {
                    sources.add(new Source(String.valueOf(item), ""));
                }
            }
        }
        return new JanusChatPresentation(reply, sources, response.optJSONObject("generated_image"));
    }

    private static String domainOf(String url) {
        if (url == null || url.isBlank()) return "";
        try {
            java.net.URI uri = java.net.URI.create(url);
            String host = uri.getHost();
            if (host == null) return "";
            return host.startsWith("www.") ? host.substring(4) : host;
        } catch (Exception ignored) { return ""; }
    }
}
