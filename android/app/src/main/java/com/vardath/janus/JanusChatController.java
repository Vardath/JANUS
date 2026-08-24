package com.vardath.janus;

import org.json.JSONObject;

/**
 * Chat transport/controller boundary.
 * Owns retry timing, structured response parsing, presentation capture and failure classification.
 */
public final class JanusChatController {
    private static final long[] RETRY_DELAYS_MS = new long[]{0L, 1800L, 5000L};
    private JanusChatController() {}

    public static Result send(JanusApiClient api, String preparedBody) {
        JanusApiClient.Response response = null;
        for (long wait : RETRY_DELAYS_MS) {
            if (wait > 0) {
                try { Thread.sleep(wait); }
                catch (InterruptedException e) { Thread.currentThread().interrupt(); break; }
            }
            response = api.postRaw("/desktop/chat", preparedBody, true);
            if (response.ok() || !response.retryable()) break;
        }
        if (response == null) response = new JanusApiClient.Response(0, "", "No response");
        if (!response.ok()) return Result.failure(response);
        try {
            JanusChatPresentation presentation = JanusChatPresentation.fromResponse(new JSONObject(response.body), response.body);
            JanusChatResponseRegistry.capture(response.body);
            return Result.success(response, presentation);
        } catch (Exception e) {
            JanusChatPresentation fallback = JanusChatPresentation.fromResponse(new JSONObject(), response.body);
            return Result.success(response, fallback);
        }
    }

    public static final class Result {
        public final JanusApiClient.Response response;
        public final JanusChatPresentation presentation;
        public final boolean retryable;
        public final boolean authExpired;
        private Result(JanusApiClient.Response response, JanusChatPresentation presentation) {
            this.response = response;
            this.presentation = presentation;
            this.retryable = response != null && response.retryable();
            this.authExpired = response != null && (response.code == 401 || response.code == 403);
        }
        static Result success(JanusApiClient.Response r, JanusChatPresentation p) { return new Result(r, p); }
        static Result failure(JanusApiClient.Response r) { return new Result(r, null); }
        public boolean ok() { return response != null && response.ok(); }
    }
}
