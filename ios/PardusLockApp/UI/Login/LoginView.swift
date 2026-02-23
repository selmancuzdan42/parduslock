import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LoginViewModel()
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var showDemoExpiredToast = false

    var body: some View {
        ZStack {
            Color(hex: "#1A252F")
                .ignoresSafeArea()

            VStack(spacing: 32) {
                // Logo / Title
                VStack(spacing: 8) {
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 72))
                        .foregroundColor(Color(hex: "#1A4D7A"))

                    Text("Pardus Kilit Sistemi")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                }
                .padding(.top, 40)

                // Form
                VStack(spacing: 16) {
                    TextField("Kullanıcı Adı", text: $viewModel.username)
                        .textFieldStyle(PardusTextFieldStyle())
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .submitLabel(.next)

                    SecureField("Şifre", text: $viewModel.password)
                        .textFieldStyle(PardusTextFieldStyle())
                        .submitLabel(.done)
                        .onSubmit {
                            Task { await performLogin() }
                        }
                }
                .padding(.horizontal, 32)

                // Login Button
                Button {
                    Task { await performLogin() }
                } label: {
                    ZStack {
                        if viewModel.isLoading {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Giriş Yap")
                                .fontWeight(.semibold)
                                .foregroundColor(.white)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(Color(hex: "#1A4D7A"))
                    .cornerRadius(12)
                }
                .disabled(viewModel.isLoading)
                .padding(.horizontal, 32)

                Spacer()
            }

            // Demo süresi doldu toast banner
            if showDemoExpiredToast {
                VStack {
                    Spacer()
                    DemoExpiredToastView()
                        .padding(.horizontal, 16)
                        .padding(.bottom, 40)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
        }
        .animation(.easeInOut(duration: 0.4), value: showDemoExpiredToast)
        .onChange(of: viewModel.state) { newState in
            handleState(newState)
        }
        .alert("Hata", isPresented: $showError) {
            Button("Tamam", role: .cancel) {}
        } message: {
            Text(errorMessage)
        }
        .task {
            await viewModel.checkDemoOnAppear()
        }
    }

    private func performLogin() async {
        await viewModel.login()
    }

    private func handleState(_ state: LoginState) {
        switch state {
        case .success(let user):
            appState.screen = .qrScan(user)
        case .error(let msg):
            errorMessage = msg
            showError = true
        case .demoExpired:
            showDemoExpiredToast = true
        default:
            break
        }
    }
}

// MARK: - Demo Expired Toast

struct DemoExpiredToastView: View {
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.yellow)
                .font(.title3)
            Text(Constants.demoExpiredMessage)
                .font(.footnote)
                .foregroundColor(.white)
                .multilineTextAlignment(.leading)
        }
        .padding(16)
        .background(Color(hex: "#1A252F").opacity(0.95))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.yellow.opacity(0.6), lineWidth: 1.5)
        )
        .cornerRadius(14)
        .shadow(color: .black.opacity(0.4), radius: 8, x: 0, y: 4)
    }
}

// MARK: - Custom TextField Style

struct PardusTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(14)
            .background(Color.white.opacity(0.08))
            .cornerRadius(10)
            .foregroundColor(.white)
            .tint(.white)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.white.opacity(0.2), lineWidth: 1)
            )
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
