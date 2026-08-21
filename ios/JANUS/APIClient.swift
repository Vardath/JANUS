import Foundation

@MainActor
final class APIClient: ObservableObject {
    let baseURL = URL(string: "https://janus-global-core.onrender.com")!
    @Published var status: String = "Dormant"
    @Published var accessToken: String = UserDefaults.standard.string(forKey: "janusAccessToken") ?? ""

    private let decoder = JSONDecoder()

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
            path: "/auth/login",
            method: "POST",
            body: ["identifier": identifier, "password": password],
            authenticated: false
        )
        if let token = response.access_token {
            setToken(token)
        }
        return response
    }

    func register(username: String, email: String, password: String) async throws -> AuthResponse {
        let response: AuthResponse = try await request(
            path: "/auth/register",
            method: "POST",
            body: ["username": username, "email": email, "password": password],
            authenticated: false
        )
        if let token = response.access_token {
            setToken(token)
        }
        return response
    }

    func me() async throws -> Account {
        let response: MeResponse = try await request(path: "/auth/me", method: "GET", body: Optional<[String: String]>.none)
        return response.account
    }

    func logout() async {
        if !accessToken.isEmpty {
            _ = try? await request(path: "/auth/logout", method: "POST", body: [String: String]()) as Data
        }
        setToken("")
    }

    func chat(profile: String, message: String) async throws -> String {
        let body = ["profile_id": profile, "message": message]
        let response: ChatResponse = try await request(path: "/desktop/chat", method: "POST", body: body)
        return response.reply ?? response.response ?? "JANUS replied, but the response was empty."
    }

    func home(profile: String) async throws -> HomeResponse {
        try await request(path: "/desktop/home?username=\(profile.urlEncoded)", method: "GET", body: Optional<[String: String]>.none)
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
        if token.isEmpty {
            UserDefaults.standard.removeObject(forKey: "janusAccessToken")
        } else {
            UserDefaults.standard.set(token, forKey: "janusAccessToken")
        }
    }

    private func request<T: Decodable, B: Encodable>(
        path: String,
        method: String,
        body: B?,
        authenticated: Bool = true
    ) async throws -> T {
        status = "Syncing"
        var request = URLRequest(url: baseURL.appendingPath(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if authenticated, !accessToken.isEmpty {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }
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
        } else {
            components.path = path
        }
        return components.url ?? self.appendingPathComponent(path)
    }
}

private extension String {
    var urlEncoded: String {
        addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? self
    }
}
