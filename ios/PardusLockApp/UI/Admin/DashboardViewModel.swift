import Foundation

@MainActor
class DashboardViewModel: ObservableObject {

    @Published var data: DashboardResponse? = nil
    @Published var isLoading = false
    @Published var errorMessage: String? = nil

    private var refreshTask: Task<Void, Never>? = nil

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            data = try await APIClient.shared.getDashboard()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func startAutoRefresh() {
        refreshTask = Task {
            while !Task.isCancelled {
                await load()
                try? await Task.sleep(nanoseconds: 10_000_000_000) // 10 sn
            }
        }
    }

    func stopAutoRefresh() {
        refreshTask?.cancel()
        refreshTask = nil
    }
}
