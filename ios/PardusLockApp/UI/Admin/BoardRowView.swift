import SwiftUI

struct BoardRowView: View {
    let board: Board
    let onPermissions: () -> Void
    let onDelete: () -> Void

    @State private var showDeleteConfirm = false

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(board.isOnline ? Color.green : Color.red)
                .frame(width: 10, height: 10)

            VStack(alignment: .leading, spacing: 2) {
                Text(board.boardId)
                    .font(.headline)
                    .foregroundColor(.white)
                Text(board.name)
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
                if let loc = board.location, !loc.isEmpty {
                    Text(loc)
                        .font(.caption2)
                        .foregroundColor(.white.opacity(0.4))
                }
            }

            Spacer()

            Text(board.isOnline ? "Çevrimiçi" : "Çevrimdışı")
                .font(.caption2)
                .foregroundColor(board.isOnline ? .green : .red)

            Menu {
                Button("Yetkiler") { onPermissions() }
                Button("Tahtayı Sil", role: .destructive) { showDeleteConfirm = true }
            } label: {
                Image(systemName: "ellipsis")
                    .foregroundColor(.white.opacity(0.7))
                    .padding(8)
            }
        }
        .padding(.vertical, 4)
        .listRowBackground(Color(hex: "#1A252F"))
        .confirmationDialog(
            "\"\(board.boardId)\" tahtasını silmek istediğinize emin misiniz?",
            isPresented: $showDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Sil", role: .destructive) { onDelete() }
            Button("İptal", role: .cancel) {}
        }
    }
}
