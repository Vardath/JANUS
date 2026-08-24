import Foundation

struct LocalAppraisal: Codable {
    var confidence: Double = 0.5
    var valence: Double = 0.0
    var salience: Double = 0.5
    var uncertainty: Double = 0.5
    var novelty: Double = 0.5
    var urgency: Double = 0.0
    var familiarity: Double = 0.5
    var risk: Double = 0.0
    var opportunity: Double = 0.0
    var conflict: Double = 0.0

    mutating func bound() {
        confidence = unit(confidence)
        valence = max(-1.0, min(1.0, valence))
        salience = unit(salience)
        uncertainty = unit(uncertainty)
        novelty = unit(novelty)
        urgency = unit(urgency)
        familiarity = unit(familiarity)
        risk = unit(risk)
        opportunity = unit(opportunity)
        conflict = unit(conflict)
    }

    var actionPosture: String {
        var x = self; x.bound()
        if x.risk >= 0.8 && x.urgency >= 0.6 { return "interrupt_or_warn" }
        if x.conflict >= 0.7 || x.uncertainty >= 0.75 { return "clarify_or_preserve_uncertainty" }
        if x.opportunity >= 0.7 && x.risk <= 0.4 { return "explore_or_act" }
        if x.salience <= 0.25 { return "defer_or_observe" }
        return "respond_normally"
    }

    enum CodingKeys: String, CodingKey {
        case confidence, valence, salience, uncertainty, novelty, urgency, familiarity, risk, opportunity, conflict
    }
}

struct LocalCoreState: Codable {
    var cycles: Int = 0
    var last: String = ""
    var appraisal: LocalAppraisal = LocalAppraisal()
}

struct LocalSenseRecord: Codable {
    let modality: String
    let source: String
    let content: String
    let salience: Double
    let uncertainty: Double
    let novelty: Double
    let createdAt: Int
}

struct LocalSocietySnapshot {
    let phase: String
    let cycles: [String: Int]
    let coreSummaries: [String: String]
    let front: String
    let frontAppraisal: LocalAppraisal
    let interface: String
    let interfaceAppraisal: LocalAppraisal
    let lastSenseAt: Int

    var coreCount: Int { cycles.count }
}

@MainActor
final class LocalJanusSociety: ObservableObject {
    static let shared = LocalJanusSociety()

    static let specialists = ["evidence", "safety", "counterpoint", "context", "logic", "novelty", "memory"]
    static let hemispheres = ["left_hemisphere", "right_hemisphere"]
    static let coreNames = specialists + hemispheres + ["front", "interface"]
    static let homeDirections: [String: Int] = [
        "evidence": 1, "safety": 2, "counterpoint": 3, "context": 4,
        "logic": 5, "novelty": 6, "memory": 7,
    ]
    static let supportedModalities = ["text", "image", "audio", "file", "web", "memory", "runtime", "peer", "action_result"]

    @Published private(set) var phase: String = "wake"
    @Published private(set) var cores: [String: LocalCoreState] = [:]
    @Published private(set) var lastSenseAt: Int = 0
    private var recentSenses: [LocalSenseRecord] = []
    private let storageKey = "janusLocalSocietyV1"

    private struct StoredState: Codable {
        let phase: String
        let cores: [String: LocalCoreState]
        let lastSenseAt: Int
        let recentSenses: [LocalSenseRecord]
    }

    private init() {
        for name in Self.coreNames { cores[name] = LocalCoreState() }
        load()
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: storageKey),
              let stored = try? JSONDecoder().decode(StoredState.self, from: data) else { return }
        phase = stored.phase
        lastSenseAt = stored.lastSenseAt
        for name in Self.coreNames { cores[name] = stored.cores[name] ?? LocalCoreState() }
        recentSenses = Array(stored.recentSenses.suffix(24))
    }

    private func persist() {
        let stored = StoredState(phase: phase, cores: cores, lastSenseAt: lastSenseAt, recentSenses: Array(recentSenses.suffix(24)))
        if let data = try? JSONEncoder().encode(stored) { UserDefaults.standard.set(data, forKey: storageKey) }
    }

    private func signals(_ content: String) -> (risk: Double, opportunity: Double, conflict: Double, urgency: Double, valence: Double) {
        let t = content.lowercased()
        let riskWords = ["danger", "unsafe", "risk", "harm", "leak", "breach", "crash", "error", "fail", "broken"]
        let opportunityWords = ["improve", "possible", "idea", "create", "build", "could", "opportunity", "explore", "new"]
        let conflictWords = ["but", "however", "conflict", "disagree", "contradict", "versus", "instead"]
        let urgencyWords = ["urgent", "now", "immediately", "critical", "asap"]
        let positiveWords = ["good", "like", "better", "success", "useful", "want", "help"]
        let negativeWords = ["bad", "dislike", "worse", "failure", "harm", "problem", "wrong"]
        let count: ([String]) -> Int = { words in words.reduce(0) { $0 + (t.contains($1) ? 1 : 0) } }
        return (
            min(1, Double(count(riskWords)) / 3.0),
            min(1, Double(count(opportunityWords)) / 3.0),
            min(1, Double(count(conflictWords)) / 2.0),
            min(1, Double(count(urgencyWords)) / 2.0),
            max(-1, min(1, Double(count(positiveWords) - count(negativeWords)) / 4.0))
        )
    }

    private func project(name: String, frame: LocalSenseRecord) -> (String, LocalAppraisal) {
        let sig = signals(frame.content)
        var appraisal = LocalAppraisal(
            confidence: 1.0 - frame.uncertainty,
            valence: sig.valence,
            salience: frame.salience,
            uncertainty: frame.uncertainty,
            novelty: frame.novelty,
            urgency: sig.urgency,
            familiarity: 1.0 - frame.novelty,
            risk: sig.risk,
            opportunity: sig.opportunity,
            conflict: sig.conflict
        )
        let text = clip(frame.content, 650)
        let summary: String
        switch name {
        case "evidence":
            summary = "Evidence sensed support/confidence needs in \(frame.modality): \(text)"
            appraisal.confidence = max(appraisal.confidence, text.isEmpty ? 0.2 : 0.55)
        case "safety":
            summary = "Safety sensed valence, welfare and boundaries: \(text)"
            if frame.source == "global-janus" { appraisal.risk = max(appraisal.risk, 0.2) }
        case "counterpoint":
            summary = "Counterpoint sensed consequence, conflict and failure possibilities: \(text)"
            appraisal.conflict = max(appraisal.conflict, frame.uncertainty * 0.55)
        case "context":
            summary = "Context sensed pattern, relationship and environment: \(text)"
            appraisal.familiarity = max(appraisal.familiarity, 0.45)
        case "logic":
            summary = "Logic sensed constraints, model and causal structure: \(text)"
            appraisal.confidence = (appraisal.confidence + (1 - appraisal.conflict)) / 2
        case "novelty":
            summary = "Novelty sensed alternatives, imagination and direction: \(text)"
            appraisal.opportunity = max(appraisal.opportunity, frame.novelty * 0.75)
        default:
            summary = "Memory compared the sense with retained continuity: \(text)"
            appraisal.familiarity = max(appraisal.familiarity, recentSenses.isEmpty ? 0.35 : 0.6)
        }
        appraisal.bound()
        return (clip(summary, 900), appraisal)
    }

    private func merge(_ items: [LocalAppraisal]) -> LocalAppraisal {
        guard !items.isEmpty else { return LocalAppraisal() }
        let n = Double(items.count)
        var out = LocalAppraisal(
            confidence: items.reduce(0) { $0 + $1.confidence } / n,
            valence: items.reduce(0) { $0 + $1.valence } / n,
            salience: items.map(\.salience).max() ?? 0.5,
            uncertainty: items.map(\.uncertainty).max() ?? 0.5,
            novelty: items.map(\.novelty).max() ?? 0.5,
            urgency: items.map(\.urgency).max() ?? 0,
            familiarity: items.reduce(0) { $0 + $1.familiarity } / n,
            risk: items.map(\.risk).max() ?? 0,
            opportunity: items.map(\.opportunity).max() ?? 0,
            conflict: items.map(\.conflict).max() ?? 0
        )
        out.bound(); return out
    }

    @discardableResult
    func sense(modality: String, source: String, content: String, salience: Double = 0.5, uncertainty: Double = 0.5, novelty: Double = 0.5) -> LocalSocietySnapshot {
        let actualModality = Self.supportedModalities.contains(modality) ? modality : "runtime"
        let frame = LocalSenseRecord(
            modality: actualModality, source: clip(source, 80), content: clip(content, 1600),
            salience: unit(salience), uncertainty: unit(uncertainty), novelty: unit(novelty),
            createdAt: Int(Date().timeIntervalSince1970)
        )
        lastSenseAt = frame.createdAt
        recentSenses.append(frame); recentSenses = Array(recentSenses.suffix(24))

        var projected: [String: LocalAppraisal] = [:]
        for name in Self.specialists {
            let (summary, appraisal) = project(name: name, frame: frame)
            var state = cores[name] ?? LocalCoreState()
            state.cycles += 1; state.last = summary; state.appraisal = appraisal
            cores[name] = state; projected[name] = appraisal
        }

        let allApps = Self.specialists.compactMap { projected[$0] }
        var leftApp = merge(allApps)
        leftApp.confidence = unit((leftApp.confidence + (1 - leftApp.conflict)) / 2); leftApp.bound()
        var left = cores["left_hemisphere"] ?? LocalCoreState()
        left.cycles += 1; left.last = "Left constrained the complete seven-core field for explicit consistency and causal structure."; left.appraisal = leftApp
        cores["left_hemisphere"] = left

        var rightApp = merge(allApps)
        rightApp.novelty = max(rightApp.novelty, rightApp.opportunity); rightApp.bound()
        var right = cores["right_hemisphere"] ?? LocalCoreState()
        right.cycles += 1; right.last = "Right expanded the complete seven-core field through association, context, alternatives and imagination."; right.appraisal = rightApp
        cores["right_hemisphere"] = right

        let frontApp = merge([leftApp, rightApp])
        var front = cores["front"] ?? LocalCoreState()
        front.cycles += 1; front.last = "Front appraised both hemispheres; posture=\(frontApp.actionPosture); source=\(frame.source); modality=\(actualModality)."; front.appraisal = frontApp
        cores["front"] = front

        let interfaceApp = merge([frontApp])
        var interface = cores["interface"] ?? LocalCoreState()
        interface.cycles += 1; interface.last = "Interface prepared bounded expression/action; posture=\(interfaceApp.actionPosture)."; interface.appraisal = interfaceApp
        cores["interface"] = interface
        persist()
        return snapshot()
    }

    func pulse() -> LocalSocietySnapshot {
        sense(modality: "runtime", source: "ios-local", content: "bounded deterministic local maintenance pulse", salience: 0.2, uncertainty: 0.1, novelty: 0.1)
    }

    func ingestPeer(_ server: [String: Any]) {
        let front = (server["front"] as? String) ?? (server["consensus"] as? String) ?? ""
        let interface = server["interface"] as? String ?? ""
        let content = [front, interface].filter { !$0.isEmpty }.joined(separator: " ")
        let appraisal = server["front_appraisal"] as? [String: Any] ?? [:]
        let salience = appraisal["salience"] as? Double ?? 0.55
        let uncertainty = appraisal["uncertainty"] as? Double ?? 0.4
        let novelty = appraisal["novelty"] as? Double ?? 0.4
        let fallback = "global phase=\(server["phase"] ?? "unknown") topology=\(server["conceptual_topology"] ?? "1|3|7")"
        sense(modality: "peer", source: "global-janus", content: content.isEmpty ? fallback : content, salience: salience, uncertainty: uncertainty, novelty: novelty)
    }

    func snapshot() -> LocalSocietySnapshot {
        LocalSocietySnapshot(
            phase: phase,
            cycles: Dictionary(uniqueKeysWithValues: Self.coreNames.map { ($0, cores[$0]?.cycles ?? 0) }),
            coreSummaries: Dictionary(uniqueKeysWithValues: Self.coreNames.map { ($0, cores[$0]?.last ?? "") }),
            front: cores["front"]?.last ?? "",
            frontAppraisal: cores["front"]?.appraisal ?? LocalAppraisal(),
            interface: cores["interface"]?.last ?? "",
            interfaceAppraisal: cores["interface"]?.appraisal ?? LocalAppraisal(),
            lastSenseAt: lastSenseAt
        )
    }
}

private func unit(_ value: Double) -> Double { max(0.0, min(1.0, value)) }
private func clip(_ value: String, _ maxLength: Int) -> String {
    let compact = value.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
    guard compact.count > maxLength else { return compact }
    return String(compact.prefix(maxLength)) + "…"
}
