import Foundation

struct ChatResponse: Decodable {
    var reply: String?
    var response: String?
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
