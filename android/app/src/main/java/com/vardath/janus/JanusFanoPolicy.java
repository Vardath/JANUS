package com.vardath.janus;

/**
 * Canonical JANUS Fano semantics shared by the seven original subconscious roles.
 *
 * Primitive coordinates:
 * E = epistemic/truth, V = valence/welfare, P = pattern/relationship.
 * Directions are processing lenses and home positions, never truth oracles.
 */
final class JanusFanoPolicy {
    private JanusFanoPolicy() {}

    static int homeDirection(String core) {
        if ("evidence".equals(core)) return 1;       // E
        if ("safety".equals(core)) return 2;         // V
        if ("counterpoint".equals(core)) return 3;   // E+V
        if ("context".equals(core)) return 4;        // P
        if ("logic".equals(core)) return 5;          // E+P
        if ("novelty".equals(core)) return 6;        // V+P
        if ("memory".equals(core)) return 7;         // E+V+P
        return 0;
    }

    static String orientation(int direction) {
        switch (direction) {
            case 1: return "evidence / truth / grounding";
            case 2: return "safety / valence / welfare / boundary";
            case 3: return "counterpoint / significance / consequence";
            case 4: return "context / pattern / relationship";
            case 5: return "logic / understanding / causal model";
            case 6: return "novelty / possibility / imagination / direction";
            case 7: return "memory / continuity / learned appraisal";
            default: return "neutral / uncommitted reference";
        }
    }

    static String directive(int direction) {
        switch (direction) {
            case 1: return "prioritize observations, evidence quality, confidence, uncertainty, and what would verify the claim";
            case 2: return "prioritize benefit/harm, wanted/unwanted, user goals, boundaries, reversibility, privacy, and safety";
            case 3: return "prioritize consequential contradictions, objections, salience, failure modes, and why the issue matters";
            case 4: return "prioritize relationships, environment, framing, analogy, gestalt, and how the topic changes under reframing";
            case 5: return "prioritize internal consistency, causal structure, mechanisms, constraints, predictions, and falsifiable models";
            case 6: return "prioritize useful alternatives, creative hypotheses, opportunities, future paths, and testable adjacent possibilities";
            case 7: return "prioritize retained history, learned significance, unfinished threads, identity continuity, and comparison with prior outcomes";
            default: return "observe without privileging a projection until enough information is available";
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
