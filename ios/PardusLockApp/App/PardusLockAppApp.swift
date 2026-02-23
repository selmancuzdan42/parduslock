import SwiftUI

@main
struct PardusLockAppApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

/// Manages top-level navigation state across the app.
struct RootView: View {
    @StateObject private var appState = AppState()

    var body: some View {
        Group {
            switch appState.screen {
            case .login:
                LoginView()
                    .environmentObject(appState)
            case .qrScan(let user):
                QRScanView(user: user)
                    .environmentObject(appState)
            case .controller(let user, let boardId):
                ControllerView(user: user, boardId: boardId)
                    .environmentObject(appState)
            }
        }
        .preferredColorScheme(.dark)
    }
}

enum AppScreen {
    case login
    case qrScan(User)
    case controller(User, String)   // String = boardId
}

final class AppState: ObservableObject {
    @Published var screen: AppScreen = .login
}
