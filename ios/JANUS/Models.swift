import Foundation

struct Account: Decodable {
    var id: Int
    var username: String
    var email: String
    var email_verified: Bool?
    var google_linked: Bool?
    var created_at: Int?
}

struct AuthResponse: Decodable {
    var ok: Bool?
    var access_token: String?
    var account: Account
    var verification_required: Bool?
    var email_delivery: Bool?
}

struct MeResponse: Decodable {
    var ok: Bool?
    var account: Account
}

struct GeneratedImage: Decodable {
    var id: String?
    var file_id: String
    var mime_type: String?
    var size_bytes: Int?
    var quality: String?
    var size: String?
    var origin: String?
    var model: String?
    var download_path: String
}

struct ChatResponse: Decodable {
    var reply: String?
    var response: String?
    var generated_image: GeneratedImage?
}

struct MessageListResponse: Decodable {
    var items: [JanusMessage]?
    var unread: Int?
}

struct JanusMessage: Identifiable, Decodable {
    var id: Int
    var message_type: String?
    var detail: String?
    var state: String?
    var created_at: String?
}

struct HomeResponse: Decodable {
    var status: String?
    var background_interval_minutes: Int?
    var unread_messages: Int?
    var latest_activity: ActivityItem?
}

struct ActivityListResponse: Decodable {
    var items: [ActivityItem]?
    var notes: [ActivityItem]?
}

struct ActivityItem: Identifiable, Decodable {
    var id: Int?
    var event_type: String?
    var detail: String?
    var created_at: String?
}

struct MemoryListResponse: Decodable {
    var items: [MemoryItem]?
}

struct MemoryItem: Identifiable, Decodable {
    var id: Int?
    var level: String?
    var role: String?
    var content: String?
    var created_at: String?
}
