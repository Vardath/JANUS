package com.vardath.janus;

/**
 * Turns the persistent seven-direction Fano state into an actual processing policy.
 * The directions are computational attention lenses; they are not claims that the
 * mathematical Fano plane itself proves anything about a topic.
 */
final class JanusFanoPolicy {
    private JanusFanoPolicy() {}

    static String orientation(int direction) {
        switch (direction) {
            case 1: return "grounding/support";
            case 2: return "structure/causality";
            case 3: return "counterexample/falsification";
            case 4: return "context/relationships";
            case 5: return "continuity/memory";
            case 6: return "boundary/risk";
            case 7: return "novelty/adjacent possibility";
            default: return "neutral integration";
        }
    }

    static String directive(int direction) {
        switch (direction) {
            case 1: return "prioritize observations, evidence quality, and what would verify the claim";
            case 2: return "prioritize internal consistency, dependencies, causal structure, and hidden assumptions";
            case 3: return "prioritize alternatives, counterexamples, failure modes, and what would falsify the current view";
            case 4: return "prioritize wider context, relationships, environment, and how the topic changes under reframing";
            case 5: return "prioritize retained history, unfinished threads, continuity, and changes from earlier states";
            case 6: return "prioritize limits, uncertainty, privacy, safety, reversibility, and boundary conditions";
            case 7: return "prioritize unusual but testable adjacent connections and unexplored possibilities";
            default: return "integrate the available material without a directional preference";
        }
    }

    static long salience(long[] weights, int direction) {
        if (weights == null || direction < 1 || direction >= weights.length) return 1L;
        long total = 0L;
        for (int i = 1; i < weights.length; i++) total += Math.max(1L, weights[i]);
        if (total <= 0L) return 1L;
        return Math.max(1L, Math.min(100L, Math.round((100.0 * Math.max(1L, weights[direction])) / total)));
    }

    static String projection(long[] weights) {
        if (weights == null || weights.length < 8) return "1|3|4 unavailable";
        long line = weights[1] + weights[2] + weights[3];
        long off = weights[4] + weights[5] + weights[6] + weights[7];
        return "1|3|4 origin=" + weights[0] + ", line=" + line + ", off-line=" + off;
    }
}
