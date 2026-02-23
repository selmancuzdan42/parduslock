package com.pardus.lockapp.ui.superadmin

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.data.model.SaBoard
import com.pardus.lockapp.databinding.ItemSaBoardBinding

class SaBoardAdapter(
    private val onAssign: (SaBoard) -> Unit,
    private val onDelete: (SaBoard) -> Unit
) : ListAdapter<SaBoard, SaBoardAdapter.VH>(DIFF) {

    inner class VH(private val b: ItemSaBoardBinding) : RecyclerView.ViewHolder(b.root) {
        fun bind(board: SaBoard) {
            b.tvBoardId.text    = board.boardId
            b.tvBoardName.text  = board.name
            b.tvSchoolCode.text = if (board.schoolCode.isNotBlank()) board.schoolCode else "Atanmamış"
            b.tvSchoolCode.setTextColor(
                if (board.schoolCode.isNotBlank()) Color.parseColor("#4CAF50")
                else Color.parseColor("#F44336")
            )
            b.btnMore.setOnClickListener { anchor ->
                val menu = PopupMenu(anchor.context, anchor)
                menu.menu.add(0, 1, 0, "Okula Ata")
                menu.menu.add(0, 2, 1, "Sil")
                menu.setOnMenuItemClickListener { item ->
                    when (item.itemId) {
                        1 -> onAssign(board)
                        2 -> onDelete(board)
                    }
                    true
                }
                menu.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemSaBoardBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(getItem(position))

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<SaBoard>() {
            override fun areItemsTheSame(a: SaBoard, b: SaBoard) = a.boardId == b.boardId
            override fun areContentsTheSame(a: SaBoard, b: SaBoard) = a == b
        }
    }
}
