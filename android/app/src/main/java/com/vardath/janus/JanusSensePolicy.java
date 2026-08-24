package com.vardath.janus;

import org.json.JSONException;
import org.json.JSONObject;

/**
 * Lightweight deterministic sensory/appraisal primitives for the local JANUS society.
 * These are computational control signals, not claims of biological sensation or
 * phenomenal feeling. They are deliberately zero-API and bounded.
 */
final class JanusSensePolicy {
    private JanusSensePolicy() {}

    static final String[] MODALITIES = new String[]{
            "text", "image", "audio", "file", "web", "memory", "runtime", "peer", "action_result"
    };

    static final class Appraisal {
        double confidence = 0.5;
        double valence = 0.0;
        double salience = 0.5;
        double uncertainty = 0.5;
        double novelty = 0.5;
        double urgency = 0.0;
        double familiarity = 0.5;
        double risk = 0.0;
        double opportunity = 0.0;
        double conflict = 0.0;

        Appraisal bounded() {
            confidence = unit(confidence);
            valence = signed(valence);
            salience = unit(salience);
            uncertainty = unit(uncertainty);
            novelty = unit(novelty);
            urgency = unit(urgency);
            familiarity = unit(familiarity);
            risk = unit(risk);
            opportunity = unit(opportunity);
            conflict = unit(conflict);
            return this;
        }

        String actionPosture() {
            bounded();
            if (risk >= 0.8 && urgency >= 0.6) return "interrupt_or_warn";
            if (conflict >= 0.7 || uncertainty >= 0.75) return "clarify_or_preserve_uncertainty";
            if (opportunity >= 0.7 && risk <= 0.4) return "explore_or_act";
            if (salience <= 0.25) return "defer_or_observe";
            return "respond_normally";
        }

        JSONObject toJson() {
            bounded();
            JSONObject out = new JSONObject();
            try {
                out.put("confidence", confidence);
                out.put("valence", valence);
                out.put("salience", salience);
                out.put("uncertainty", uncertainty);
                out.put("novelty", novelty);
                out.put("urgency", urgency);
                out.put("familiarity", familiarity);
                out.put("risk", risk);
                out.put("opportunity", opportunity);
                out.put("conflict", conflict);
                out.put("action_posture", actionPosture());
            } catch (JSONException ignored) {
                // Primitive bounded values are JSON-safe; retain a partial object if a
                // platform implementation nevertheless rejects a field.
            }
            return out;
        }
    }

    static Appraisal merge(Appraisal a, Appraisal b) {
        Appraisal out = new Appraisal();
        out.confidence = (a.confidence + b.confidence) / 2.0;
        out.valence = (a.valence + b.valence) / 2.0;
        out.salience = Math.max(a.salience, b.salience);
        out.uncertainty = Math.max(a.uncertainty, b.uncertainty);
        out.novelty = Math.max(a.novelty, b.novelty);
        out.urgency = Math.max(a.urgency, b.urgency);
        out.familiarity = (a.familiarity + b.familiarity) / 2.0;
        out.risk = Math.max(a.risk, b.risk);
        out.opportunity = Math.max(a.opportunity, b.opportunity);
        out.conflict = Math.max(a.conflict, b.conflict);
        return out.bounded();
    }

    private static double unit(double x) { return Math.max(0.0, Math.min(1.0, x)); }
    private static double signed(double x) { return Math.max(-1.0, Math.min(1.0, x)); }
}
