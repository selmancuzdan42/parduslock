package com.pardus.lockapp.ui.superadmin

import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.data.model.SchoolAdmin
import com.pardus.lockapp.databinding.ItemSchoolAdminBinding

class SchoolAdminAdapter(
    private val onDelete: (SchoolAdmin) -> Unit
) : ListAdapter<SchoolAdmin, SchoolAdminAdapter.VH>(DIFF) {

    inner class VH(private val b: ItemSchoolAdminBinding) : RecyclerView.ViewHolder(b.root) {
        fun bind(admin: SchoolAdmin) {
            b.tvFullName.text   = admin.fullName
            b.tvUsername.text   = "@${admin.username}"
            b.tvSchoolCode.text = admin.schoolCode
            b.btnMore.setOnClickListener { anchor ->
                val menu = PopupMenu(anchor.context, anchor)
                menu.menu.add(0, 1, 0, "Sil")
                menu.setOnMenuItemClickListener {
                    if (it.itemId == 1) onDelete(admin)
                    true
                }
                menu.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemSchoolAdminBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(getItem(position))

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<SchoolAdmin>() {
            override fun areItemsTheSame(a: SchoolAdmin, b: SchoolAdmin) = a.id == b.id
            override fun areContentsTheSame(a: SchoolAdmin, b: SchoolAdmin) = a == b
        }
    }
}
