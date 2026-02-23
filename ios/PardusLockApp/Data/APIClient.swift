import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case networkError(Error)
    case serverError(Int)
    case decodingError(Error)
    case unauthorized
    case unknown(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Geçersiz sunucu URL'si."
        case .networkError(let e):
            return "Ağ hatası: \(e.localizedDescription)"
        case .serverError(let code):
            return "Sunucu hatası: HTTP \(code)"
        case .decodingError(let e):
            return "Veri çözümleme hatası: \(e.localizedDescription)"
        case .unauthorized:
            return "Oturum süresi doldu. Lütfen tekrar giriş yapın."
        case .unknown(let msg):
            return msg
        }
    }
}

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private var baseURL: String

    private init() {
        baseURL = Constants.defaultServerURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        config.timeoutIntervalForResource = 15
        config.httpCookieStorage = HTTPCookieStorage.shared
        config.httpShouldSetCookies = true
        config.httpCookieAcceptPolicy = .always
        session = URLSession(configuration: config)
    }

    func fetchDemoConfig() async throws -> DemoConfig {
        let urlReq = try jsonRequest(try url("/api/demo-config"), method: "GET")
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlReq)
        } catch {
            throw APIError.networkError(error)
        }
        _ = response
        return try JSONDecoder().decode(DemoConfig.self, from: data)
    }

    func clearCookies() {
        guard let cookies = HTTPCookieStorage.shared.cookies else { return }
        for cookie in cookies {
            HTTPCookieStorage.shared.deleteCookie(cookie)
        }
    }

    // MARK: - Private helpers

    private func url(_ path: String) throws -> URL {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }
        return url
    }

    private func jsonRequest(_ url: URL, method: String, body: Encodable? = nil) throws -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        if let http = response as? HTTPURLResponse {
            guard (200...299).contains(http.statusCode) else {
                // Body'den mesaj okumayı her zaman dene
                if let decoded = try? JSONDecoder().decode(StatusResponse.self, from: data),
                   let msg = decoded.message, !msg.isEmpty {
                    // 401 ve body'de mesaj varsa → yanlış şifre vb., generic "oturum doldu" gösterme
                    if http.statusCode == 401 {
                        throw APIError.unknown(msg)
                    }
                    throw APIError.unknown(msg)
                }
                // Body boşsa ve 401 → gerçekten oturum süresi dolmuş
                if http.statusCode == 401 {
                    throw APIError.unauthorized
                }
                throw APIError.serverError(http.statusCode)
            }
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: - Auth

    func login(username: String, password: String) async throws -> LoginResponse {
        let req = LoginRequest(username: username, password: password)
        let urlReq = try jsonRequest(try url("/api/login"), method: "POST", body: req)
        return try await perform(urlReq)
    }

    func logout() async throws -> StatusResponse {
        let urlReq = try jsonRequest(try url("/api/logout"), method: "POST")
        return try await perform(urlReq)
    }

    func me() async throws -> LoginResponse {
        let urlReq = try jsonRequest(try url("/api/me"), method: "GET")
        return try await perform(urlReq)
    }

    // MARK: - Commands

    func sendCommand(boardId: String, command: String) async throws -> StatusResponse {
        let req = SendCommandRequest(boardId: boardId, command: command)
        let urlReq = try jsonRequest(try url("/api/send_command"), method: "POST", body: req)
        return try await perform(urlReq)
    }

    // MARK: - Admin

    func getUsers() async throws -> UsersResponse {
        let urlReq = try jsonRequest(try url("/api/admin/users"), method: "GET")
        return try await perform(urlReq)
    }

    func addUser(username: String, fullName: String, password: String, role: String) async throws -> StatusResponse {
        let req = AddUserRequest(username: username, fullName: fullName, password: password, role: role)
        let urlReq = try jsonRequest(try url("/api/admin/users"), method: "POST", body: req)
        return try await perform(urlReq)
    }

    func deleteUser(id: Int) async throws -> StatusResponse {
        let urlReq = try jsonRequest(try url("/api/admin/users/\(id)"), method: "DELETE")
        return try await perform(urlReq)
    }

    // MARK: - Boards

    func getBoards() async throws -> BoardsResponse {
        let urlReq = try jsonRequest(try url("/api/admin/boards"), method: "GET")
        return try await perform(urlReq)
    }

    func deleteBoard(boardId: String) async throws -> StatusResponse {
        let urlReq = try jsonRequest(try url("/api/admin/boards/\(boardId)"), method: "DELETE")
        return try await perform(urlReq)
    }

    func getBoardPermissions(boardId: String) async throws -> BoardPermissionsResponse {
        let urlReq = try jsonRequest(try url("/api/admin/boards/\(boardId)/permissions"), method: "GET")
        return try await perform(urlReq)
    }

    func addBoardPermission(boardId: String, userId: Int) async throws -> StatusResponse {
        let req = AddPermissionRequest(userId: userId)
        let urlReq = try jsonRequest(try url("/api/admin/boards/\(boardId)/permissions"), method: "POST", body: req)
        return try await perform(urlReq)
    }

    func removeBoardPermission(boardId: String, userId: Int) async throws -> StatusResponse {
        let urlReq = try jsonRequest(try url("/api/admin/boards/\(boardId)/permissions/\(userId)"), method: "DELETE")
        return try await perform(urlReq)
    }

    func changePassword(userId: Int, newPassword: String) async throws -> StatusResponse {
        let req = ChangePasswordRequest(userId: userId, newPassword: newPassword)
        let urlReq = try jsonRequest(try url("/api/admin/change_password"), method: "POST", body: req)
        return try await perform(urlReq)
    }

    func getDashboard() async throws -> DashboardResponse {
        let urlReq = try jsonRequest(try url("/api/admin/dashboard"), method: "GET")
        return try await perform(urlReq)
    }
}
