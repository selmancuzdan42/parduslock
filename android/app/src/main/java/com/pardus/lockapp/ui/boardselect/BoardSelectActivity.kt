package com.pardus.lockapp.ui.boardselect

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.R
import com.pardus.lockapp.data.Constants
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.Board
import com.pardus.lockapp.databinding.ActivityBoardSelectBinding
import com.pardus.lockapp.ui.admin.AdminActivity
import com.pardus.lockapp.ui.controller.ControllerActivity
import com.pardus.lockapp.ui.login.LoginActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class BoardSelectActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_FULL_NAME = "full_name"
        const val EXTRA_ROLE      = "role"
        const val EXTRA_USER_ID   = "user_id"
    }

    private lateinit var binding: ActivityBoardSelectBinding
    private val viewModel: BoardSelectViewModel by viewModels()

    private lateinit var fullName: String
    private lateinit var role: String
    private var userId: Int = -1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBoardSelectBinding.inflate(layoutInflater)
        setContentView(binding.root)

        fullName = intent.getStringExtra(EXTRA_FULL_NAME) ?: ""
        role     = intent.getStringExtra(EXTRA_ROLE)      ?: "admin"
        userId   = intent.getIntExtra(EXTRA_USER_ID, -1)

        binding.recyclerView.layoutManager = LinearLayoutManager(this)

        binding.btnLogout.setOnClickListener {
            CoroutineScope(Dispatchers.IO).launch {
                try { ApiClient.getService(Constants.DEFAULT_SERVER_URL).logout() } catch (_: Exception) {}
                ApiClient.clearCookies()
            }
            startActivity(Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
        }

        viewModel.state.observe(this) { state ->
            when (state) {
                is BoardSelectState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.tvError.visibility = View.GONE
                }
                is BoardSelectState.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.tvError.visibility = View.GONE
                    binding.recyclerView.adapter = BoardSelectAdapter(state.boards) { board ->
                        openController(board)
                    }
                }
                is BoardSelectState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.tvError.visibility = View.VISIBLE
                    binding.tvError.text = state.message
                }
            }
        }

        viewModel.loadBoards(Constants.DEFAULT_SERVER_URL)
    }

    private fun openController(board: Board) {
        val intent = Intent(this, ControllerActivity::class.java).apply {
            putExtra(ControllerActivity.EXTRA_SERVER_URL, Constants.DEFAULT_SERVER_URL)
            putExtra(ControllerActivity.EXTRA_BOARD_ID,   board.boardId)
            putExtra(ControllerActivity.EXTRA_FULL_NAME,  fullName)
            putExtra(ControllerActivity.EXTRA_ROLE,       role)
            putExtra(AdminActivity.EXTRA_CURRENT_USER_ID, userId)
        }
        startActivity(intent)
    }
}

class BoardSelectAdapter(
    private val boards: List<Board>,
    private val onClick: (Board) -> Unit
) : RecyclerView.Adapter<BoardSelectAdapter.VH>() {

    inner class VH(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvOnlineDot: TextView  = itemView.findViewById(R.id.tvOnlineDot)
        val tvBoardName: TextView  = itemView.findViewById(R.id.tvBoardName)
        val tvBoardLocation: TextView = itemView.findViewById(R.id.tvBoardLocation)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_board_select, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val board = boards[position]
        holder.tvOnlineDot.setTextColor(
            if (board.isOnline) Color.parseColor("#4CAF50") else Color.parseColor("#607D8B")
        )
        holder.tvBoardName.text     = board.name
        holder.tvBoardLocation.text = board.location ?: ""
        holder.itemView.setOnClickListener { onClick(board) }
    }

    override fun getItemCount() = boards.size
}
