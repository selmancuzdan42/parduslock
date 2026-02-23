import Foundation

@MainActor
final class BoardsViewModel: ObservableObject {
    @Published var boards: [Board] = []
    @Published var isLoading = false
    @Published var errorMessage: String? = nil

    // Yetki dialogu için
    @Published var permissionBoard: Board? = nil
    @Published var allTeachers: [User] = []
    @Published var assignedIds: Set<Int> = []
    @Published var showPermissionsSheet = false
    @Published var actionMessage: String? = nil

    func loadBoards() async {
        isLoading = true
        do {
            let resp = try await APIClient.shared.getBoards()
            boards = resp.boards ?? []
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func loadPermissionsForBoard(_ board: Board) async {
        isLoading = true
        async let permsTask  = APIClient.shared.getBoardPermissions(boardId: board.boardId)
        async let usersTask  = APIClient.shared.getUsers()

        do {
            let (perms, users) = try await (permsTask, usersTask)
            assignedIds   = Set((perms.users ?? []).map { $0.id })
            allTeachers   = (users.users ?? []).filter { $0.role == "teacher" }
            permissionBoard = board
            showPermissionsSheet = true
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func deleteBoard(_ board: Board) async {
        isLoading = true
        do {
            _ = try await APIClient.shared.deleteBoard(boardId: board.boardId)
            actionMessage = "Tahta silindi"
            await loadBoards()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func savePermissions(selectedIds: Set<Int>) async {
        guard let board = permissionBoard else { return }
        isLoading = true
        let toAdd    = selectedIds.subtracting(assignedIds)
        let toRemove = assignedIds.subtracting(selectedIds)

        do {
            for uid in toAdd {
                _ = try await APIClient.shared.addBoardPermission(boardId: board.boardId, userId: uid)
            }
            for uid in toRemove {
                _ = try await APIClient.shared.removeBoardPermission(boardId: board.boardId, userId: uid)
            }
            actionMessage = "Yetkiler güncellendi"
            showPermissionsSheet = false
            await loadBoards()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
