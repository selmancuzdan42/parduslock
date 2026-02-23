import SwiftUI

struct DashboardView: View {

    @StateObject private var viewModel = DashboardViewModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color(hex: "#1A252F").ignoresSafeArea()

                if viewModel.isLoading && viewModel.data == nil {
                    ProgressView("Yükleniyor…")
                        .tint(.white)
                        .foregroundColor(.white)

                } else if let msg = viewModel.errorMessage, viewModel.data == nil {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        Text(msg)
                            .multilineTextAlignment(.center)
                            .foregroundColor(.white)
                            .padding(.horizontal, 32)
                        Button("Yenile") {
                            Task { await viewModel.load() }
                        }
                        .buttonStyle(PardusButtonStyle(color: Color(hex: "#1A4D7A")))
                    }

                } else if let d = viewModel.data {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 20) {

                            // ── İstatistik kartları ──
                            HStack(spacing: 10) {
                                StatCard(
                                    value: "\(d.boards.online)",
                                    label: "Çevrimiçi",
                                    sub: "\(d.boards.total) tahta toplam",
                                    color: Color(hex: "#4CAF50")
                                )
                                StatCard(
                                    value: "\(d.users.teachers)",
                                    label: "Öğretmen",
                                    sub: "\(d.users.admins) yönetici",
                                    color: Color(hex: "#4CA1AF")
                                )
                                StatCard(
                                    value: "\(d.commands.last24h)",
                                    label: "Komut (24s)",
                                    sub: "\(d.commands.done24h) başarılı",
                                    color: Color(hex: "#FFA726")
                                )
                            }

                            // ── Tahtalar ──
                            SectionHeader(title: "TAHTALAR")

                            VStack(spacing: 0) {
                                ForEach(d.boardList) { board in
                                    DashboardBoardRow(board: board)
                                    if board.id != d.boardList.last?.id {
                                        Divider().background(Color.white.opacity(0.07))
                                    }
                                }
                            }
                            .background(Color(hex: "#1E2D3D"))
                            .cornerRadius(12)

                            // ── Son Komutlar ──
                            SectionHeader(title: "SON KOMUTLAR")

                            VStack(spacing: 0) {
                                ForEach(d.recentCommands) { cmd in
                                    DashboardCommandRow(cmd: cmd)
                                    if cmd.id != d.recentCommands.last?.id {
                                        Divider().background(Color.white.opacity(0.07))
                                    }
                                }
                            }
                            .background(Color(hex: "#1E2D3D"))
                            .cornerRadius(12)
                        }
                        .padding(12)
                    }
                    .refreshable {
                        await viewModel.load()
                    }
                }
            }
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Kapat") { dismiss() }
                        .foregroundColor(.white)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    if viewModel.isLoading {
                        ProgressView().tint(.white).scaleEffect(0.8)
                    } else {
                        Button {
                            Task { await viewModel.load() }
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .foregroundColor(.white)
                        }
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
        .onAppear  { viewModel.startAutoRefresh() }
        .onDisappear { viewModel.stopAutoRefresh() }
    }
}

// MARK: - Alt bileşenler

private struct StatCard: View {
    let value: String
    let label: String
    let sub: String
    let color: Color

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 28, weight: .bold))
                .foregroundColor(color)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(Color(hex: "#7A8FA0"))
            Text(sub)
                .font(.system(size: 10))
                .foregroundColor(Color(hex: "#AABBCC"))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .background(Color(hex: "#1E2D3D"))
        .cornerRadius(12)
    }
}

private struct SectionHeader: View {
    let title: String
    var body: some View {
        Text(title)
            .font(.system(size: 11, weight: .bold))
            .foregroundColor(Color(hex: "#637D96"))
            .tracking(1.5)
    }
}

private struct DashboardBoardRow: View {
    let board: DashboardBoardItem

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(board.isOnline ? Color(hex: "#4CAF50") : Color(hex: "#F44336"))
                .frame(width: 8, height: 8)

            VStack(alignment: .leading, spacing: 2) {
                Text(board.name)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                Text([board.boardId, board.location].compactMap { $0 }.joined(separator: " · "))
                    .font(.system(size: 11))
                    .foregroundColor(Color(hex: "#7A8FA0"))
            }

            Spacer()

            Text(board.isOnline ? "Çevrimiçi" : "Çevrimdışı")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(board.isOnline ? Color(hex: "#4CAF50") : Color(hex: "#F44336"))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }
}

private struct DashboardCommandRow: View {
    let cmd: DashboardRecentCommand

    var commandInfo: (label: String, color: Color) {
        switch cmd.command {
        case "unlock": return ("🔓 Kilit Aç", Color(hex: "#4CAF50"))
        case "lock":   return ("🔒 Kilitle",  Color(hex: "#F44336"))
        case "next":   return ("▶ Sonraki",   Color(hex: "#FFA726"))
        case "prev":   return ("◀ Önceki",    Color(hex: "#42A5F5"))
        default:       return (cmd.command,    Color(hex: "#AABBCC"))
        }
    }

    var statusInfo: (label: String, color: Color) {
        switch cmd.status {
        case "done":       return ("✓ Tamam",         Color(hex: "#4CAF50"))
        case "failed":     return ("✗ Başarısız",     Color(hex: "#F44336"))
        case "expired":    return ("⏱ Süresi Doldu",  Color(hex: "#FFA726"))
        case "pending":    return ("⏳ Bekliyor",      Color(hex: "#AABBCC"))
        case "processing": return ("⚙ İşleniyor",     Color(hex: "#42A5F5"))
        default:           return (cmd.status,         Color(hex: "#AABBCC"))
        }
    }

    var timeLabel: String {
        cmd.issuedAt.count >= 16 ? String(cmd.issuedAt.dropFirst(11).prefix(5)) : cmd.issuedAt
    }

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(commandInfo.label)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(commandInfo.color)
                HStack(spacing: 4) {
                    Text(cmd.boardId)
                    Text("·")
                    Text(cmd.issuedBy ?? "—")
                }
                .font(.system(size: 11))
                .foregroundColor(Color(hex: "#7A8FA0"))
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(statusInfo.label)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(statusInfo.color)
                Text(timeLabel)
                    .font(.system(size: 10))
                    .foregroundColor(Color(hex: "#637D96"))
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }
}
