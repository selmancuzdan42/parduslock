import SwiftUI

struct UserRowView: View {
    let user: User
    let isCurrentUser: Bool
    let onChangePassword: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Avatar circle
            Circle()
                .fill(Color(hex: "#1A4D7A"))
                .frame(width: 44, height: 44)
                .overlay(
                    Text(String(user.fullName.prefix(1)).uppercased())
                        .font(.headline)
                        .foregroundColor(.white)
                )

            // Info
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(user.fullName)
                        .font(.body)
                        .foregroundColor(.white)
                    if isCurrentUser {
                        Text("(siz)")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.5))
                    }
                }
                Text("@\(user.username)")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.6))
            }

            Spacer()

            // Role badge
            Text(user.role == "admin" ? "Admin" : "User")
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(user.role == "admin" ? Color(hex: "#1A4D7A") : Color.gray.opacity(0.4))
                .cornerRadius(6)

            // Action menu
            Menu {
                Button {
                    onChangePassword()
                } label: {
                    Label("Şifre Değiştir", systemImage: "key.fill")
                }

                if !isCurrentUser {
                    Button(role: .destructive) {
                        onDelete()
                    } label: {
                        Label("Sil", systemImage: "trash")
                    }
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .font(.title3)
                    .foregroundColor(.white.opacity(0.7))
            }
        }
        .padding(.vertical, 4)
        .listRowBackground(Color(hex: "#1A252F"))
    }
}
