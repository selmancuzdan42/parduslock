package com.pardus.lockapp.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.R
import com.pardus.lockapp.data.model.User
import com.pardus.lockapp.databinding.ItemUserBinding

class UserAdapter(
    private val currentUserId: Int,
    private val onDelete: (User) -> Unit,
    private val onChangePassword: (User) -> Unit
) : ListAdapter<User, UserAdapter.UserViewHolder>(UserDiff) {

    inner class UserViewHolder(private val binding: ItemUserBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(user: User) {
            // Avatar: ismin baş harfi
            val initials = user.fullName.trim().split(" ")
                .mapNotNull { it.firstOrNull()?.toString() }
                .take(2)
                .joinToString("")
                .uppercase()
            binding.tvAvatar.text   = initials.ifEmpty { "?" }

            binding.tvFullName.text = user.fullName
            binding.tvUsername.text = "@${user.username}"
            binding.tvRole.text     = if (user.role == "admin") "YÖNETİCİ" else "ÖĞRETMEN"

            binding.btnMore.setOnClickListener { anchor ->
                val popup = PopupMenu(anchor.context, anchor)
                popup.menu.add(0, 1, 0, "Şifre Değiştir")
                if (user.id != currentUserId) {
                    popup.menu.add(0, 2, 1, "Kullanıcıyı Sil")
                }
                popup.setOnMenuItemClickListener { item ->
                    when (item.itemId) {
                        1 -> { onChangePassword(user); true }
                        2 -> { onDelete(user); true }
                        else -> false
                    }
                }
                popup.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): UserViewHolder {
        val binding = ItemUserBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return UserViewHolder(binding)
    }

    override fun onBindViewHolder(holder: UserViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    private object UserDiff : DiffUtil.ItemCallback<User>() {
        override fun areItemsTheSame(a: User, b: User) = a.id == b.id
        override fun areContentsTheSame(a: User, b: User) = a == b
    }
}
