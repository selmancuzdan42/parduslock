package com.pardus.lockapp.ui.superadmin

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.data.model.License
import com.pardus.lockapp.databinding.ItemLicenseBinding

class LicenseAdapter(
    private val onToggle: (License) -> Unit,
    private val onDelete: (License) -> Unit
) : ListAdapter<License, LicenseAdapter.VH>(DIFF) {

    inner class VH(private val b: ItemLicenseBinding) : RecyclerView.ViewHolder(b.root) {
        fun bind(lic: License) {
            b.tvSchoolCode.text = lic.schoolCode
            b.tvSchoolName.text = lic.schoolName
            b.tvDates.text      = "${lic.startDate} → ${lic.endDate} (${lic.durationMonths} ay)"
            b.tvStatus.text     = if (lic.isActive) "AKTİF" else "PASİF"
            b.tvStatus.setTextColor(
                if (lic.isActive) Color.parseColor("#4CAF50") else Color.parseColor("#F44336")
            )
            b.btnMore.setOnClickListener { anchor ->
                val menu = PopupMenu(anchor.context, anchor)
                menu.menu.add(0, 1, 0, if (lic.isActive) "Pasif Yap" else "Aktif Yap")
                menu.menu.add(0, 2, 1, "Sil")
                menu.setOnMenuItemClickListener { item ->
                    when (item.itemId) {
                        1 -> onToggle(lic)
                        2 -> onDelete(lic)
                    }
                    true
                }
                menu.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemLicenseBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(getItem(position))

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<License>() {
            override fun areItemsTheSame(a: License, b: License) = a.id == b.id
            override fun areContentsTheSame(a: License, b: License) = a == b
        }
    }
}
