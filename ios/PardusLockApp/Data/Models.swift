import Foundation

// MARK: - Domain Models

struct User: Codable, Identifiable, Equatable {
    let id: Int
    let username: String
    let fullName: String
    let role: String
    let schoolCode: String

    enum CodingKeys: String, CodingKey {
        case id
        case username
        case fullName   = "full_name"
        case role
        case schoolCode = "school_code"
    }

    var isAdmin: Bool      { role == "admin" }
    var isSuperAdmin: Bool { role == "superadmin" }
    var roleBadge: String  {
        switch role {
        case "superadmin": return "SÜPER ADMİN"
        case "admin":      return "YÖNETİCİ"
        default:           return "ÖĞRETMEN"
        }
    }
}

// MARK: - Demo Config

struct DemoConfig: Decodable {
    let active: Bool
    let demoEnd: String

    enum CodingKeys: String, CodingKey {
        case active
        case demoEnd = "demo_end"
    }

    var expiryDate: Date? {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = TimeZone(identifier: "Europe/Istanbul")
        return f.date(from: demoEnd)
    }

    var isExpired: Bool {
        guard active else { return true }          // active=false → direkt bitti
        guard let end = expiryDate else { return false }
        // Gün bazlı karşılaştır — saat farkı sorun çıkarmasın
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let endDay = calendar.startOfDay(for: end)
        return today >= endDay
    }
}

// MARK: - Request Models

struct LoginRequest: Codable {
    let username: String
    let password: String
}

struct SendCommandRequest: Codable {
    let boardId: String
    let command: String

    enum CodingKeys: String, CodingKey {
        case boardId = "board_id"
        case command
    }
}

struct AddPermissionRequest: Codable {
    let userId: Int
    enum CodingKeys: String, CodingKey { case userId = "user_id" }
}

struct AddUserRequest: Codable {
    let username: String
    let fullName: String
    let password: String
    let role: String

    enum CodingKeys: String, CodingKey {
        case username
        case fullName = "full_name"
        case password
        case role
    }
}

struct ChangePasswordRequest: Codable {
    let userId: Int
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case newPassword = "new_password"
    }
}

// MARK: - Response Models

struct LoginResponse: Codable {
    let status: String
    let user: User?
    let message: String?
}

struct StatusResponse: Codable {
    let status: String
    let message: String?
}

struct UsersResponse: Codable {
    let status: String
    let users: [User]?
    let message: String?
}

struct Board: Codable, Identifiable {
    var id: String { boardId }
    let boardId: String
    let name: String
    let location: String?
    let isOnline: Bool
    let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case boardId   = "board_id"
        case name, location
        case isOnline  = "is_online"
        case isActive  = "is_active"
    }
}

struct BoardsResponse: Codable {
    let status: String
    let boards: [Board]?
}

struct BoardPermissionsResponse: Codable {
    let status: String
    let boardId: String?
    let users: [User]?
    enum CodingKeys: String, CodingKey {
        case status
        case boardId = "board_id"
        case users
    }
}

// MARK: - Dashboard Models

struct DashboardBoardStats: Codable {
    let total: Int
    let online: Int
    let offline: Int
}

struct DashboardUserStats: Codable {
    let total: Int
    let admins: Int
    let teachers: Int
}

struct DashboardCommandStats: Codable {
    let last24h: Int
    let done24h: Int
    let failed24h: Int
    let expired24h: Int

    enum CodingKeys: String, CodingKey {
        case last24h   = "last_24h"
        case done24h   = "done_24h"
        case failed24h = "failed_24h"
        case expired24h = "expired_24h"
    }
}

struct DashboardBoardItem: Codable, Identifiable {
    var id: String { boardId }
    let boardId: String
    let name: String
    let location: String?
    let isOnline: Bool
    let lastSeen: String?

    enum CodingKeys: String, CodingKey {
        case boardId  = "board_id"
        case name, location
        case isOnline = "is_online"
        case lastSeen = "last_seen"
    }
}

struct DashboardRecentCommand: Codable, Identifiable {
    let id: Int
    let boardId: String
    let command: String
    let status: String
    let issuedAt: String
    let issuedBy: String?

    enum CodingKeys: String, CodingKey {
        case id
        case boardId  = "board_id"
        case command, status
        case issuedAt = "issued_at"
        case issuedBy = "issued_by"
    }
}

struct DashboardResponse: Codable {
    let status: String
    let boards: DashboardBoardStats
    let users: DashboardUserStats
    let commands: DashboardCommandStats
    let boardList: [DashboardBoardItem]
    let recentCommands: [DashboardRecentCommand]

    enum CodingKeys: String, CodingKey {
        case status, boards, users, commands
        case boardList      = "board_list"
        case recentCommands = "recent_commands"
    }
}
