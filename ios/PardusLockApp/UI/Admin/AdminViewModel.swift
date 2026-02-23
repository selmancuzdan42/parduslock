import Foundation

enum AdminState {
    case idle
    case loading
    case error(String)
}

@MainActor
final class AdminViewModel: ObservableObject {
    @Published var users: [User] = []
    @Published var state: AdminState = .idle
    @Published var actionError: String? = nil

    let currentUser: User

    init(currentUser: User) {
        self.currentUser = currentUser
    }

    var isLoading: Bool {
        if case .loading = state { return true }
        return false
    }

    // MARK: - Load

    func loadUsers() async {
        state = .loading
        do {
            let response = try await APIClient.shared.getUsers()
            if response.status == "ok" {
                users = response.users ?? []
                state = .idle
            } else {
                state = .error(response.message ?? "Kullanıcılar yüklenemedi.")
            }
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    // MARK: - Add User

    func addUser(username: String, fullName: String, password: String, role: String) async -> Bool {
        do {
            let response = try await APIClient.shared.addUser(
                username: username,
                fullName: fullName,
                password: password,
                role: role
            )
            if response.status == "ok" {
                await loadUsers()
                return true
            } else {
                actionError = response.message ?? "Kullanıcı eklenemedi."
                return false
            }
        } catch {
            actionError = error.localizedDescription
            return false
        }
    }

    // MARK: - Delete User

    func deleteUser(id: Int) async {
        guard id != currentUser.id else {
            actionError = "Kendi hesabınızı silemezsiniz."
            return
        }
        do {
            let response = try await APIClient.shared.deleteUser(id: id)
            if response.status == "ok" {
                users.removeAll { $0.id == id }
            } else {
                actionError = response.message ?? "Kullanıcı silinemedi."
            }
        } catch {
            actionError = error.localizedDescription
        }
    }

    // MARK: - Change Password

    func changePassword(userId: Int, newPassword: String) async -> Bool {
        let trimmed = newPassword.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else {
            actionError = "Şifre boş olamaz."
            return false
        }
        do {
            let response = try await APIClient.shared.changePassword(userId: userId, newPassword: trimmed)
            if response.status == "ok" {
                return true
            } else {
                actionError = response.message ?? "Şifre değiştirilemedi."
                return false
            }
        } catch {
            actionError = error.localizedDescription
            return false
        }
    }
}
