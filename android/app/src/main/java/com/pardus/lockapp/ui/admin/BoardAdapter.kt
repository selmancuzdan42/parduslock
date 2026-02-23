package com.pardus.lockapp.ui.admin

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.data.model.Board
import com.pardus.lockapp.databinding.ItemBoardBinding

class BoardAdapter(
    private val onPermissions: (Board) -> Unit,
    private val onDelete: (Board) -> Unit
) : ListAdapter<Board, BoardAdapter.ViewHolder>(DIFF) {

    inner class ViewHolder(private val b: ItemBoardBinding) :
        RecyclerView.ViewHolder(b.root) {

        fun bind(board: Board) {
            b.tvBoardId.text       = board.boardId
            b.tvBoardName.text     = board.name
            b.tvBoardLocation.text = board.location?.takeIf { it.isNotBlank() } ?: ""
            b.tvOnlineDot.setTextColor(
                if (board.isOnline) Color.parseColor("#4CAF50")
                else Color.parseColor("#F44336")
            )
            b.btnMore.setOnClickListener { view ->
                val menu = PopupMenu(view.context, view)
                menu.menu.add(0, 1, 0, "Yetkiler")
                menu.menu.add(0, 2, 1, "Tahtayı Sil")
                menu.setOnMenuItemClickListener { item ->
                    when (item.itemId) {
                        1 -> onPermissions(board)
                        2 -> onDelete(board)
                    }
                    true
                }
                menu.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        ViewHolder(ItemBoardBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: ViewHolder, position: Int) =
        holder.bind(getItem(position))

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<Board>() {
            override fun areItemsTheSame(a: Board, b: Board) = a.boardId == b.boardId
            override fun areContentsTheSame(a: Board, b: Board) = a == b
        }
    }
}
