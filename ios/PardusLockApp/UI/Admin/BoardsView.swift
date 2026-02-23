import SwiftUI

struct BoardsView: View {
    @StateObject private var viewModel = BoardsViewModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color(hex: "#1A252F").ignoresSafeArea()

                if viewModel.isLoading && viewModel.boards.isEmpty {
                    ProgressView("Yükleniyor…")
                        .tint(.white).foregroundColor(.white)
                } else if viewModel.boards.isEmpty {
                    VStack(spacing: 12) {
                        Image(systemName: "display")
                            .font(.system(size: 48))
                            .foregroundColor(.white.opacity(0.3))
                        Text("Henüz kayıtlı tahta yok.\nTahtalar lock_system.py çalıştırınca otomatik kaydolur.")
                            .multilineTextAlignment(.center)
                            .foregroundColor(.white.opacity(0.5))
                            .padding(.horizontal, 32)
                    }
                } else {
                    List(viewModel.boards) { board in
                        BoardRowView(
                            board: board,
                            onPermissions: {
                                Task { await viewModel.loadPermissionsForBoard(board) }
                            },
                            onDelete: {
                                Task { await viewModel.deleteBoard(board) }
                            }
                        )
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .refreshable { await viewModel.loadBoards() }
                }
            }
            .navigationTitle("Tahta Yönetimi")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Kapat") { dismiss() }.foregroundColor(.white)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    if viewModel.isLoading { ProgressView().tint(.white) }
                }
            }
        }
        .task { await viewModel.loadBoards() }
        .sheet(isPresented: $viewModel.showPermissionsSheet) {
            PermissionsSheetView(viewModel: viewModel)
        }
        .alert("Hata", isPresented: Binding(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )) {
            Button("Tamam", role: .cancel) { viewModel.errorMessage = nil }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
        .alert("Başarılı", isPresented: Binding(
            get: { viewModel.actionMessage != nil },
            set: { if !$0 { viewModel.actionMessage = nil } }
        )) {
            Button("Tamam", role: .cancel) { viewModel.actionMessage = nil }
        } message: {
            Text(viewModel.actionMessage ?? "")
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - Permissions Sheet

struct PermissionsSheetView: View {
    @ObservedObject var viewModel: BoardsViewModel
    @State private var selected: Set<Int> = []

    var body: some View {
        NavigationStack {
            ZStack {
                Color(hex: "#1A252F").ignoresSafeArea()

                if viewModel.allTeachers.isEmpty {
                    Text("Sistemde öğretmen hesabı bulunmuyor.")
                        .foregroundColor(.white.opacity(0.6))
                        .multilineTextAlignment(.center)
                        .padding()
                } else {
                    List(viewModel.allTeachers) { teacher in
                        HStack {
                            Image(systemName: selected.contains(teacher.id)
                                  ? "checkmark.circle.fill" : "circle")
                                .foregroundColor(selected.contains(teacher.id)
                                                 ? Color(hex: "#1A4D7A") : .gray)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(teacher.fullName)
                                    .foregroundColor(.white)
                                Text("@\(teacher.username)")
                                    .font(.caption)
                                    .foregroundColor(.white.opacity(0.5))
                            }
                            Spacer()
                        }
                        .contentShape(Rectangle())
                        .onTapGesture {
                            if selected.contains(teacher.id) {
                                selected.remove(teacher.id)
                            } else {
                                selected.insert(teacher.id)
                            }
                        }
                        .listRowBackground(Color(hex: "#1A252F"))
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
            .navigationTitle("Yetkiler: \(viewModel.permissionBoard?.boardId ?? "")")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("İptal") {
                        viewModel.showPermissionsSheet = false
                    }.foregroundColor(.white)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Kaydet") {
                        Task { await viewModel.savePermissions(selectedIds: selected) }
                    }
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                }
            }
        }
        .onAppear {
            selected = viewModel.assignedIds
        }
        .preferredColorScheme(.dark)
    }
}
