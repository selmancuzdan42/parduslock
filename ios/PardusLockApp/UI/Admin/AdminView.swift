import SwiftUI

struct AdminView: View {
    let currentUser: User

    @StateObject private var viewModel: AdminViewModel
    @Environment(\.dismiss) private var dismiss

    // Add user sheet state
    @State private var showAddUser = false
    @State private var newUsername = ""
    @State private var newFullName = ""
    @State private var newPassword = ""
    @State private var newRole = "user"

    // Change password state
    @State private var showChangePassword = false
    @State private var selectedUser: User? = nil
    @State private var newPasswordInput = ""

    // Delete confirmation
    @State private var showDeleteAlert = false
    @State private var userToDelete: User? = nil

    // Boards sheet
    @State private var showBoards = false

    // Dashboard sheet
    @State private var showDashboard = false

    init(currentUser: User) {
        self.currentUser = currentUser
        _viewModel = StateObject(wrappedValue: AdminViewModel(currentUser: currentUser))
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color(hex: "#1A252F").ignoresSafeArea()
                userListContent
            }
            .navigationTitle("Yönetici Paneli")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Kapat") { dismiss() }
                        .foregroundColor(.white)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    trailingToolbarItems
                }
            }
        }
        .task { await viewModel.loadUsers() }
        .sheet(isPresented: $showDashboard) { DashboardView() }
        .sheet(isPresented: $showBoards) { BoardsView() }
        .sheet(isPresented: $showAddUser) { addUserSheet }
        .alert("Şifre Değiştir", isPresented: $showChangePassword, presenting: selectedUser) { user in
            TextField("Yeni şifre", text: $newPasswordInput)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            Button("Değiştir") {
                Task { _ = await viewModel.changePassword(userId: user.id, newPassword: newPasswordInput) }
            }
            Button("İptal", role: .cancel) {}
        } message: { user in
            Text("\(user.fullName) kullanıcısı için yeni şifre girin.")
        }
        .alert("Kullanıcıyı Sil", isPresented: $showDeleteAlert, presenting: userToDelete) { user in
            Button("Sil", role: .destructive) {
                Task { await viewModel.deleteUser(id: user.id) }
            }
            Button("İptal", role: .cancel) {}
        } message: { user in
            Text("\(user.fullName) kullanıcısını silmek istediğinize emin misiniz?")
        }
        .alert("Hata", isPresented: Binding(
            get: { viewModel.actionError != nil },
            set: { if !$0 { viewModel.actionError = nil } }
        )) {
            Button("Tamam", role: .cancel) { viewModel.actionError = nil }
        } message: {
            Text(viewModel.actionError ?? "")
        }
    }

    @ViewBuilder
    private var userListContent: some View {
        if viewModel.isLoading && viewModel.users.isEmpty {
            ProgressView("Yükleniyor…")
                .tint(.white)
                .foregroundColor(.white)
        } else if case .error(let msg) = viewModel.state {
            VStack(spacing: 16) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.orange)
                Text(msg)
                    .multilineTextAlignment(.center)
                    .foregroundColor(.white)
                    .padding(.horizontal, 32)
                Button("Yenile") {
                    Task { await viewModel.loadUsers() }
                }
                .buttonStyle(PardusButtonStyle(color: Color(hex: "#1A4D7A")))
            }
        } else {
            List(viewModel.users) { user in
                UserRowView(
                    user: user,
                    isCurrentUser: user.id == currentUser.id,
                    onChangePassword: {
                        selectedUser = user
                        newPasswordInput = ""
                        showChangePassword = true
                    },
                    onDelete: {
                        userToDelete = user
                        showDeleteAlert = true
                    }
                )
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .refreshable { await viewModel.loadUsers() }
        }
    }

    private var trailingToolbarItems: some View {
        HStack(spacing: 4) {
            Button { showDashboard = true } label: {
                Image(systemName: "chart.bar.xaxis").foregroundColor(.white)
            }
            Button { showBoards = true } label: {
                Image(systemName: "display").foregroundColor(.white)
            }
            Button {
                showAddUser = true
                resetAddUserForm()
            } label: {
                Image(systemName: "person.badge.plus").foregroundColor(.white)
            }
        }
    }

    private var addUserSheet: some View {
        AddUserSheet(
            username: $newUsername,
            fullName: $newFullName,
            password: $newPassword,
            role: $newRole
        ) {
            Task {
                let success = await viewModel.addUser(
                    username: newUsername,
                    fullName: newFullName,
                    password: newPassword,
                    role: newRole
                )
                if success { showAddUser = false }
            }
        }
    }

    private func resetAddUserForm() {
        newUsername = ""
        newFullName = ""
        newPassword = ""
        newRole = "user"
    }
}

// MARK: - Add User Sheet

struct AddUserSheet: View {
    @Binding var username: String
    @Binding var fullName: String
    @Binding var password: String
    @Binding var role: String
    let onSave: () -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color(hex: "#1A252F").ignoresSafeArea()

                Form {
                    Section("Kullanıcı Bilgileri") {
                        TextField("Ad Soyad", text: $fullName)
                            .autocorrectionDisabled()
                        TextField("Kullanıcı Adı", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        SecureField("Şifre", text: $password)
                    }
                    .listRowBackground(Color.white.opacity(0.08))

                    Section("Rol") {
                        Picker("Rol", selection: $role) {
                            Text("Kullanıcı").tag("user")
                            Text("Yönetici").tag("admin")
                        }
                        .pickerStyle(.segmented)
                    }
                    .listRowBackground(Color.white.opacity(0.08))
                }
                .scrollContentBackground(.hidden)
                .foregroundColor(.white)
            }
            .navigationTitle("Kullanıcı Ekle")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("İptal") { dismiss() }
                        .foregroundColor(.white)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Kaydet") { onSave() }
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .disabled(username.isEmpty || fullName.isEmpty || password.isEmpty)
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
