import Foundation

enum LoginState: Equatable {
    case idle
    case loading
    case success(User)
    case error(String)
    case demoExpired
}

@MainActor
final class LoginViewModel: ObservableObject {
    @Published var username: String = ""
    @Published var password: String = ""
    @Published var state: LoginState = .idle

    var isLoading: Bool {
        if case .loading = state { return true }
        return false
    }

    func login() async {
        let trimmedUsername = username.trimmingCharacters(in: .whitespaces)
        let trimmedPassword = password.trimmingCharacters(in: .whitespaces)

        guard !trimmedUsername.isEmpty, !trimmedPassword.isEmpty else {
            state = .error("Kullanıcı adı ve şifre boş bırakılamaz.")
            return
        }

        state = .loading
        do {
            let response = try await APIClient.shared.login(username: trimmedUsername, password: trimmedPassword)
            if response.status == "ok", let user = response.user {
                state = .success(user)
            } else {
                state = .error(response.message ?? "Giriş başarısız.")
            }
        } catch {
            // Login ağ hatasında da demo kontrolü yap
            if case APIError.networkError = error {
                await checkDemoOnAppear()
                if case .demoExpired = state { return }
            }
            state = .error(error.localizedDescription)
        }
    }

    /// Uygulama açılışında sunucudan demo config'i çeker.
    /// Sunucu erişilemezse hardcoded fallback tarihe bakar.
    func checkDemoOnAppear() async {
        do {
            let config = try await APIClient.shared.fetchDemoConfig()
            if config.isExpired {
                state = .demoExpired
            }
        } catch APIError.networkError {
            // Sunucu erişilemez — fallback tarihe bak
            if Date() >= Constants.demoExpiryFallback {
                state = .demoExpired
            }
        } catch {
            // Sunucu erişilebilir ama başka hata — demo geçerli
        }
    }
}
