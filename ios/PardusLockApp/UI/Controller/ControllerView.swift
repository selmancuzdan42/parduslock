import SwiftUI

struct ControllerView: View {
    let user: User
    let boardId: String

    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel: ControllerViewModel
    @State private var showAdmin = false
    @State private var showLogoutAlert = false
    @State private var feedbackMessage: String? = nil

    init(user: User, boardId: String) {
        self.user = user
        self.boardId = boardId
        _viewModel = StateObject(wrappedValue: ControllerViewModel(boardId: boardId))
    }

    var body: some View {
        ZStack {
            Color(hex: "#1A252F").ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                headerView

                Divider()
                    .background(Color.white.opacity(0.15))

                // Feedback banner
                if let msg = feedbackMessage {
                    Text(msg)
                        .font(.footnote)
                        .foregroundColor(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .frame(maxWidth: .infinity)
                        .background(feedbackBannerColor)
                        .transition(.move(edge: .top).combined(with: .opacity))
                }

                // Command Grid
                commandGrid
                    .padding()

                // Admin button
                if user.isAdmin || user.isSuperAdmin {
                    Button("Yönetici Paneli") {
                        showAdmin = true
                    }
                    .buttonStyle(PardusButtonStyle(color: Color(hex: "#1A4D7A")))
                    .padding(.bottom, 8)
                }

                Spacer()
            }
        }
        .onChange(of: viewModel.commandState) { newState in
            handleCommandState(newState)
        }
        .sheet(isPresented: $showAdmin) {
            AdminView(currentUser: user)
        }
        .alert("Çıkış Yap", isPresented: $showLogoutAlert) {
            Button("Çıkış Yap", role: .destructive) {
                Task {
                    await viewModel.logout()
                    appState.screen = .login
                }
            }
            Button("İptal", role: .cancel) {}
        } message: {
            Text("Oturumu kapatmak istediğinize emin misiniz?")
        }
    }

    // MARK: - Subviews

    private var headerView: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(user.fullName)
                    .font(.headline)
                    .foregroundColor(.white)
                Text("Tahta: \(boardId)")
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.5))
                Text(roleBadgeText)
                    .font(.caption)
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(roleBadgeColor)
                    .cornerRadius(6)
            }

            Spacer()

            Button {
                showLogoutAlert = true
            } label: {
                Image(systemName: "rectangle.portrait.and.arrow.right")
                    .font(.title3)
                    .foregroundColor(.white.opacity(0.8))
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
    }

    private var commandGrid: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                CommandButton(
                    title: "Kilit Aç",
                    icon: "lock.open.fill",
                    color: .green,
                    command: "unlock",
                    isLoading: loadingCommand == "unlock"
                ) {
                    Task { await viewModel.sendCommand("unlock") }
                }

                CommandButton(
                    title: "Kilitle",
                    icon: "lock.fill",
                    color: .red,
                    command: "lock",
                    isLoading: loadingCommand == "lock"
                ) {
                    Task { await viewModel.sendCommand("lock") }
                }
            }

            HStack(spacing: 12) {
                CommandButton(
                    title: "Önceki",
                    icon: "chevron.left.circle.fill",
                    color: .blue,
                    command: "prev",
                    isLoading: loadingCommand == "prev"
                ) {
                    Task { await viewModel.sendCommand("prev") }
                }

                CommandButton(
                    title: "Sonraki",
                    icon: "chevron.right.circle.fill",
                    color: Color(hex: "#FF8C00"),
                    command: "next",
                    isLoading: loadingCommand == "next"
                ) {
                    Task { await viewModel.sendCommand("next") }
                }
            }
        }
    }

    // MARK: - Helpers

    private var loadingCommand: String? {
        if case .loading(let cmd) = viewModel.commandState { return cmd }
        return nil
    }

    private var feedbackBannerColor: Color {
        switch viewModel.commandState {
        case .success: return Color.green.opacity(0.75)
        case .error: return Color.red.opacity(0.75)
        default: return Color.clear
        }
    }

    private var roleBadgeText: String {
        user.roleBadge
    }

    private var roleBadgeColor: Color {
        switch user.role {
        case "superadmin": return Color(hex: "#6C3483")
        case "admin":      return Color(hex: "#1A4D7A")
        default:           return Color.gray.opacity(0.5)
        }
    }

    private func handleCommandState(_ state: CommandState) {
        switch state {
        case .success(let msg):
            withAnimation { feedbackMessage = msg }
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                withAnimation { feedbackMessage = nil }
            }
        case .error(let msg):
            withAnimation { feedbackMessage = msg }
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                withAnimation { feedbackMessage = nil }
            }
        default:
            break
        }
    }
}

// MARK: - CommandButton

struct CommandButton: View {
    let title: String
    let icon: String
    let color: Color
    let command: String
    let isLoading: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                if isLoading {
                    ProgressView()
                        .tint(.white)
                } else {
                    VStack(spacing: 10) {
                        Image(systemName: icon)
                            .font(.system(size: 36))
                        Text(title)
                            .font(.headline)
                    }
                    .foregroundColor(.white)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 120)
            .background(color.opacity(0.85))
            .cornerRadius(16)
        }
        .disabled(isLoading)
    }
}
