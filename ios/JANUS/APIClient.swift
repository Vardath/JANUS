import Foundation
import Combine
import UniformTypeIdentifiers

@MainActor
final class APIClient: ObservableObject {
    let baseURL = URL(string: "https://janus-global-core.onrender.com")!
    @Published var status: String = "Dormant"
    @Published var accessToken: String = KeychainStore.readToken()

    private let decoder = JSONDecoder()
    private let maxFileBytes = 8 * 1024 * 1024
    private var deviceID: String {
        let key = "janusDeviceID"
        if let existing = UserDefaults.standard.string(forKey: key), !existing.isEmpty { return existing }
        let value = "ios-" + UUID().uuidString.lowercased()
        UserDefaults.standard.set(value, forKey: key)
        return value
    }

    func health() async {
        do {
            _ = try await request(path: "/health", method: "GET", body: Optional<[String: String]>.none, authenticated: false) as Data
            status = "Active"
        } catch {
            status = "Dormant"
        }
    }

    func login(identifier: String, password: String) async throws -> AuthResponse {
        let response: AuthResponse = try await request(
            path: "/auth/login", method: "POST",
            body: ["identifier": identifier, "password": password], authenticated: false
        )
        if let token = response.access_token { setToken(token); await presenceHeartbeat() }
        return response
    }

    func register(username: String, email: String, password: String) async throws -> AuthResponse {
        let response: AuthResponse = try await request(
            path: "/auth/register", method: "POST",
            body: ["username": username, "email": email, "password": password], authenticated: false
        )
        if let token = response.access_token { setToken(token); await presenceHeartbeat() }
        return response
    }

    func me() async throws -> Account {
        let response: MeResponse = try await request(path: "/auth/me", method: "GET", body: Optional<[String: String]>.none)
        await presenceHeartbeat()
        return response.account
    }

    func logout() async {
        if !accessToken.isEmpty {
            _ = try? await request(path: "/auth/logout", method: "POST", body: [String: String]()) as Data
        }
        setToken("")
    }

    func presenceHeartbeat() async {
        guard !accessToken.isEmpty else { return }
        struct PresenceBody: Encodable {
            let device_id: String
            let platform: String
            let client_version: String
            let phase: String
            let cycles: [String: Int]
            let observe_events: [[String: String]]
            let memories: [String]
            let conclusions: [String]
        }
        let body = PresenceBody(device_id: deviceID, platform: "ios", client_version: "0.4", phase: "interface", cycles: [:], observe_events: [], memories: [], conclusions: [])
        do {
            let data: Data = try await request(path: "/core-sync/exchange", method: "POST", body: body)
            if let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let presence = root["presence"] as? [String: Any],
               let server = root["server"] as? [String: Any] {
                let online = presence["online"] as? Int ?? 0
                let registered = presence["registered"] as? Int ?? 0
                let phase = server["phase"] as? String ?? "unknown"
                status = "Global \(phase) · \(online)/\(registered) clients"
            }
        } catch {
            status = "Global offline"
        }
    }

    func chat(profile: String, message: String, attachmentIDs: [String] = []) async throws -> ChatResponse {
        await presenceHeartbeat()
        let body = ChatRequest(profile_id: profile, message: message, attachment_ids: attachmentIDs)
        return try await request(path: "/desktop/chat", method: "POST", body: body)
    }

    func uploadFile(url: URL) async throws -> UploadedFile {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        let values = try url.resourceValues(forKeys: [.fileSizeKey])
        if let size = values.fileSize, size > maxFileBytes {
            throw NSError(domain: "JANUS", code: 413, userInfo: [NSLocalizedDescriptionKey: "JANUS currently accepts files up to 8 MiB."])
        }
        let data = try Data(contentsOf: url, options: [.mappedIfSafe])
        guard !data.isEmpty else { throw NSError(domain: "JANUS", code: 400, userInfo: [NSLocalizedDescriptionKey: "Empty files are not supported."]) }
        guard data.count <= maxFileBytes else { throw NSError(domain: "JANUS", code: 413, userInfo: [NSLocalizedDescriptionKey: "JANUS currently accepts files up to 8 MiB."]) }
        let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        struct FileBody: Encodable { let filename: String; let mime_type: String; let data_base64: String }
        let body = FileBody(filename: url.lastPathComponent, mime_type: mime, data_base64: data.base64EncodedString())
        let response: UploadResponse = try await request(path: "/files/upload", method: "POST", body: body)
        return response.file
    }

    func generatedImageData(path: String) async throws -> Data {
        try await request(path: path, method: "GET", body: Optional<[String: String]>.none)
    }

    func home(profile: String) async throws -> HomeResponse {
        await presenceHeartbeat()
        return try await request(path: "/desktop/home?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
    }

    func messages(profile: String) async throws -> MessageListResponse {
        try await request(path: "/desktop/messages?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
    }

    func setMessageState(id: Int, profile: String, state: String) async throws {
        let body = ["profile_id": profile, "state": state]
        _ = try await request(path: "/desktop/messages/\(id)/state", method: "POST", body: body) as Data
    }

    func observe(profile: String) async throws -> [ActivityItem] {
        let response: ActivityListResponse = try await request(path: "/desktop/observe?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
        return response.notes ?? response.items ?? []
    }

    func activity(profile: String) async throws -> [ActivityItem] {
        let response: ActivityListResponse = try await request(path: "/desktop/activity?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
        return response.items ?? []
    }

    func memory(profile: String) async throws -> [MemoryItem] {
        let response: MemoryListResponse = try await request(path: "/desktop/memory?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
        return response.items ?? []
    }

    private func setToken(_ token: String) {
        accessToken = token
        KeychainStore.writeToken(token)
    }

    private func request<T: Decodable, B: Encodable>(path: String, method: String, body: B?, authenticated: Bool = true) async throws -> T {
        status = "Syncing"
        var request = URLRequest(url: baseURL.appendingPath(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if authenticated, !accessToken.isEmpty { request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization") }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(body)
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            let text = String(data: data, encoding: .utf8) ?? "Unknown server error"
            status = "Dormant"
            throw NSError(domain: "JANUS", code: 1, userInfo: [NSLocalizedDescriptionKey: text])
        }
        status = "Active"
        if T.self == Data.self { return data as! T }
        return try decoder.decode(T.self, from: data)
    }
}

private extension URL {
    func appendingPath(_ path: String) -> URL {
        guard var components = URLComponents(url: self, resolvingAgainstBaseURL: false) else { return self }
        if let queryStart = path.firstIndex(of: "?") {
            components.path = String(path[..<queryStart])
            components.percentEncodedQuery = String(path[path.index(after: queryStart)...])
        } else { components.path = path }
        return components.url ?? self.appendingPathComponent(path)
    }
}

private extension String {
    var urlEncoded: String { addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self }
}
