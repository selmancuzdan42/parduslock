import Foundation
import AVFoundation

enum QRScanState: Equatable {
    case scanning
    case processing
    case success(String)   // token
    case error(String)
    case permissionDenied
}

@MainActor
final class QRScanViewModel: NSObject, ObservableObject {
    @Published var state: QRScanState = .scanning

    let captureSession = AVCaptureSession()
    private var scanned = false

    override init() {
        super.init()
        Task { await setupCamera() }
    }

    func setupCamera() async {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        switch status {
        case .authorized:
            configureSession()
        case .notDetermined:
            let granted = await AVCaptureDevice.requestAccess(for: .video)
            if granted {
                configureSession()
            } else {
                state = .permissionDenied
            }
        default:
            state = .permissionDenied
        }
    }

    private func configureSession() {
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device) else {
            state = .error("Kamera başlatılamadı.")
            return
        }

        captureSession.beginConfiguration()
        if captureSession.canAddInput(input) {
            captureSession.addInput(input)
        }

        let output = AVCaptureMetadataOutput()
        if captureSession.canAddOutput(output) {
            captureSession.addOutput(output)
            output.setMetadataObjectsDelegate(self, queue: .main)
            output.metadataObjectTypes = [.qr]
        }
        captureSession.commitConfiguration()

        let session = captureSession
        Task.detached {
            session.startRunning()
        }
    }

    func startScanning() {
        scanned = false
        state = .scanning
        let session = captureSession
        if !session.isRunning {
            Task.detached {
                session.startRunning()
            }
        }
    }

    func stopScanning() {
        let session = captureSession
        if session.isRunning {
            Task.detached {
                session.stopRunning()
            }
        }
    }

    private func parseToken(from qrString: String) -> String? {
        // Desteklenen formatlar:
        // 1. Düz metin: "ETAP1"
        // 2. URL parametresi: "http://sunucu/?board_id=ETAP1"
        let trimmed = qrString.trimmingCharacters(in: .whitespacesAndNewlines)
        if let components = URLComponents(string: trimmed),
           let item = components.queryItems?.first(where: { $0.name == "board_id" }),
           let value = item.value, !value.isEmpty {
            return value
        }
        return trimmed.isEmpty ? nil : trimmed
    }
}

// MARK: - AVCaptureMetadataOutputObjectsDelegate

extension QRScanViewModel: AVCaptureMetadataOutputObjectsDelegate {
    nonisolated func metadataOutput(
        _ output: AVCaptureMetadataOutput,
        didOutput metadataObjects: [AVMetadataObject],
        from connection: AVCaptureConnection
    ) {
        Task { @MainActor in
            guard !self.scanned else { return }
            guard let object = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
                  object.type == .qr,
                  let stringValue = object.stringValue else { return }

            self.scanned = true
            self.stopScanning()

            guard let token = self.parseToken(from: stringValue) else {
                self.state = .error("QR koddan token okunamadı.")
                return
            }
            self.state = .success(token)
        }
    }
}
