import Foundation

enum CommandState {
    case idle
    case loading(String)    // command name
    case success(String)    // message
    case error(String)
}

@MainActor
final class ControllerViewModel: ObservableObject {
    @Published var commandState: CommandState = .idle

    private let boardId: String

    init(boardId: String) {
        self.boardId = boardId
    }

    var isLoading: Bool {
        if case .loading = commandState { return true }
        return false
    }

    func sendCommand(_ command: String) async {
        guard !isLoading else { return }
        commandState = .loading(command)
        do {
            let response = try await APIClient.shared.sendCommand(boardId: boardId, command: command)
            if response.status == "ok" {
                commandState = .success(response.message ?? "Komut başarıyla gönderildi.")
            } else {
                commandState = .error(response.message ?? "Komut gönderilemedi.")
            }
        } catch {
            commandState = .error(error.localizedDescription)
        }
    }

    func logout() async {
        _ = try? await APIClient.shared.logout()
        APIClient.shared.clearCookies()
    }
}
