import SwiftUI
import AVFoundation

struct QRScanView: View {
    let user: User
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = QRScanViewModel()

    var body: some View {
        ZStack {
            Color(hex: "#1A252F").ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                VStack(spacing: 4) {
                    Text("QR Kod Tara")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                    Text("Kilide ait QR kodu kameranıza gösterin")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.7))
                }
                .padding(.top, 20)
                .padding(.bottom, 16)

                // Camera / State area
                ZStack {
                    switch viewModel.state {
                    case .scanning, .processing:
                        CameraPreviewView(session: viewModel.captureSession)
                            .ignoresSafeArea(edges: .horizontal)
                            .overlay(
                                ScannerOverlay()
                            )

                    case .success:
                        Color.black
                        VStack(spacing: 16) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.system(size: 64))
                                .foregroundColor(.green)
                            Text("QR Kod Okundu!")
                                .font(.title2)
                                .fontWeight(.semibold)
                                .foregroundColor(.white)
                            ProgressView()
                                .tint(.white)
                                .padding(.top, 8)
                        }

                    case .error(let msg):
                        Color.black
                        VStack(spacing: 16) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 64))
                                .foregroundColor(.red)
                            Text(msg)
                                .multilineTextAlignment(.center)
                                .foregroundColor(.white)
                                .padding(.horizontal, 32)
                            Button("Tekrar Dene") {
                                viewModel.startScanning()
                            }
                            .buttonStyle(PardusButtonStyle(color: Color(hex: "#1A4D7A")))
                        }

                    case .permissionDenied:
                        Color.black
                        VStack(spacing: 16) {
                            Image(systemName: "camera.fill")
                                .font(.system(size: 64))
                                .foregroundColor(.white.opacity(0.5))
                            Text("Kamera erişimi reddedildi.\nAyarlar > Gizlilik > Kamera bölümünden izin verin.")
                                .multilineTextAlignment(.center)
                                .foregroundColor(.white.opacity(0.8))
                                .padding(.horizontal, 32)
                            Button("Ayarları Aç") {
                                if let url = URL(string: UIApplication.openSettingsURLString) {
                                    UIApplication.shared.open(url)
                                }
                            }
                            .buttonStyle(PardusButtonStyle(color: Color(hex: "#1A4D7A")))
                        }
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .cornerRadius(16)
                .padding(.horizontal, 16)

                // Footer
                VStack(spacing: 4) {
                    Text("Giriş yapan: \(user.fullName)")
                        .font(.footnote)
                        .foregroundColor(.white.opacity(0.6))
                }
                .padding(.vertical, 16)
            }
        }
        .onChange(of: viewModel.state) { newState in
            if case .success(let token) = newState {
                // Brief delay so the success UI is visible
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    appState.screen = .controller(user, token)
                }
            }
        }
        .onDisappear {
            viewModel.stopScanning()
        }
    }
}

// MARK: - Scanner Overlay

struct ScannerOverlay: View {
    var body: some View {
        GeometryReader { geo in
            let side = min(geo.size.width, geo.size.height) * 0.65
            ZStack {
                Color.black.opacity(0.5)
                    .mask(
                        Rectangle()
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .frame(width: side, height: side)
                                    .blendMode(.destinationOut)
                            )
                    )

                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white, lineWidth: 2)
                    .frame(width: side, height: side)
            }
        }
    }
}

// MARK: - Reusable Button Style

struct PardusButtonStyle: ButtonStyle {
    let color: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.horizontal, 24)
            .padding(.vertical, 12)
            .background(color.opacity(configuration.isPressed ? 0.7 : 1))
            .foregroundColor(.white)
            .cornerRadius(10)
            .fontWeight(.semibold)
    }
}
